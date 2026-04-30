from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,   # Wait 10 seconds before each retry
    name='payments.tasks.process_mint'
)
def process_mint(self, order_id):
    """
    Background task: Mint NIT tokens to the user after M-Pesa payment confirmed.
    Retries up to 3 times if the blockchain call fails.
    """
    from .models import CryptoOrder
    from wallet.web3_utils import mint_token_to_user

    try:
        order = CryptoOrder.objects.get(id=order_id)

        if order.status != 'PAID':
            logger.warning(f"Order {order_id} is not in PAID state — skipping mint. Status: {order.status}")
            return

        logger.info(f"[MINT] Starting mint for order {order_id} → {order.wallet_address} | {order.amount_kes} NIT")

        tx_hash = mint_token_to_user(order.wallet_address, order.amount_kes)

        if tx_hash:
            order.status = 'COMPLETED'
            order.tx_hash = tx_hash
            order.save()
            logger.info(f"[MINT] ✅ Success — tx_hash: {tx_hash}")
        else:
            order.status = 'PAID_BUT_FAILED'
            order.error_message = "Blockchain returned no tx_hash"
            order.save()
            logger.error(f"[MINT] ❌ Mint returned None for order {order_id}")

    except CryptoOrder.DoesNotExist:
        logger.error(f"[MINT] Order {order_id} not found — cannot mint.")

    except Exception as exc:
        logger.error(f"[MINT] ❌ Unexpected error for order {order_id}: {exc}")
        # Retry the task — Celery will wait 10s between each attempt
        raise self.retry(exc=exc)