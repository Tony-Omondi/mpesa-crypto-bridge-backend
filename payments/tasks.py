
from celery import shared_task
from celery.utils.log import get_task_logger
import logging

logger = get_task_logger(__name__)
admin_logger = logging.getLogger('django')

FEE_RATE = 0.005  # 0.5%


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    name='payments.tasks.process_mint'
)
def process_mint(self, order_id):
    """
    Mints NIT tokens after M-Pesa payment confirmed.
    For REQUEST type orders: mints (amount - 0.5% fee) to requester, fee to admin.
    For DEPOSIT type orders: mints full amount to wallet_address.
    """
    from .models import CryptoOrder
    from wallet.web3_utils import mint_token_to_user, SENDER_ADDRESS

    try:
        order = CryptoOrder.objects.get(id=order_id)

        if order.status != 'PAID':
            logger.warning(f"Order {order_id} not in PAID state — skipping. Status: {order.status}")
            return

        logger.info(f"[MINT] Order {order_id} | Type: {order.request_type} | {order.amount_kes} KES")

        if order.request_type == 'REQUEST' and order.requester_wallet:
            # ── Payment Request — split fee ───────────────────────
            total_kes = float(order.amount_kes)
            fee_kes = round(total_kes * FEE_RATE, 2)
            requester_kes = round(total_kes - fee_kes, 2)

            logger.info(f"[MINT] REQUEST split: {requester_kes} NIT to requester, {fee_kes} NIT fee to admin")

            # 1. Mint to requester
            tx_hash = mint_token_to_user(order.requester_wallet, requester_kes)

            if tx_hash:
                order.tx_hash = tx_hash
                logger.info(f"[MINT] ✅ Requester mint success: {tx_hash}")

                # 2. Mint fee to admin wallet
                if fee_kes > 0 and SENDER_ADDRESS:
                    fee_tx = mint_token_to_user(SENDER_ADDRESS, fee_kes)
                    if fee_tx:
                        order.fee_tx_hash = fee_tx
                        logger.info(f"[MINT] ✅ Fee mint success: {fee_tx}")
                    else:
                        logger.warning(f"[MINT] ⚠️ Fee mint failed for order {order_id} — continuing anyway")

                order.status = 'COMPLETED'
                order.save()
            else:
                order.status = 'PAID_BUT_FAILED'
                order.error_message = "Blockchain returned no tx_hash for requester mint"
                order.save()
                admin_logger.error(
                    f"🚨 REQUEST MINT FAILED — Order #{order_id} | "
                    f"Requester: {order.requester_wallet} | "
                    f"Amount: {requester_kes} NIT | "
                    f"Action: POST /api/payments/retry/{order_id}/"
                )

        else:
            # ── Standard Deposit — full amount to wallet ──────────
            tx_hash = mint_token_to_user(order.wallet_address, float(order.amount_kes))

            if tx_hash:
                order.status = 'COMPLETED'
                order.tx_hash = tx_hash
                order.save()
                logger.info(f"[MINT] ✅ Deposit mint success: {tx_hash}")
            else:
                order.status = 'PAID_BUT_FAILED'
                order.error_message = "Blockchain returned no tx_hash"
                order.save()
                admin_logger.error(
                    f"🚨 MINT FAILED — Order #{order_id} | "
                    f"Wallet: {order.wallet_address} | "
                    f"Amount: {order.amount_kes} KES | "
                    f"Action: POST /api/payments/retry/{order_id}/"
                )

    except CryptoOrder.DoesNotExist:
        logger.error(f"[MINT] Order {order_id} not found.")

    except Exception as exc:
        logger.error(f"[MINT] ❌ Error for order {order_id}: {exc}")
        retry_count = self.request.retries

        if retry_count < self.max_retries:
            logger.warning(f"[MINT] Retrying order {order_id} — attempt {retry_count + 1}/{self.max_retries}")
        else:
            try:
                order = CryptoOrder.objects.get(id=order_id)
                order.status = 'PAID_BUT_FAILED'
                order.error_message = f"All {self.max_retries} retries failed: {str(exc)}"
                order.save()
                admin_logger.error(
                    f"🚨 MINT PERMANENTLY FAILED — Order #{order_id} | "
                    f"Error: {str(exc)} | "
                    f"Action: POST /api/payments/retry/{order_id}/"
                )
            except Exception:
                pass

        raise self.retry(exc=exc)
