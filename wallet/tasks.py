from celery import shared_task
from celery.utils.log import get_task_logger
from decimal import Decimal

logger = get_task_logger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=15,
    name='wallet.tasks.process_transfer'
)
def process_transfer(self, sender_private_key, to_address, amount, sender_address):
    """
    Background task: Transfer NIT tokens from one wallet to another.
    Saves result to Transfer history on success.
    """
    from payments.models import Transfer
    from .web3_utils import transfer_token

    try:
        logger.info(f"[TRANSFER] Starting transfer → {to_address} | {amount} NIT")

        result = transfer_token(sender_private_key, to_address, float(amount))

        if "error" in result:
            logger.error(f"[TRANSFER] ❌ Failed: {result['error']}")
            # Save a FAILED record so the user can see it in history
            Transfer.objects.create(
                from_address=sender_address,
                to_address=to_address,
                amount=Decimal(str(amount)),
                tx_hash=None,
                status='FAILED'
            )
            return {"success": False, "error": result["error"]}

        Transfer.objects.create(
            from_address=sender_address,
            to_address=to_address,
            amount=Decimal(str(amount)),
            tx_hash=result["tx_hash"],
            status='COMPLETED'
        )

        logger.info(f"[TRANSFER] ✅ Success — tx_hash: {result['tx_hash']}")
        return {"success": True, "tx_hash": result["tx_hash"]}

    except Exception as exc:
        logger.error(f"[TRANSFER] ❌ Unexpected error: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=15,
    name='wallet.tasks.process_withdrawal'
)
def process_withdrawal(self, user_private_key, amount, phone_number, sender_address):
    """
    Background task: Burns NIT tokens then sends M-Pesa B2C payout.
    Both heavy operations run in background so the user gets instant response.
    """
    from payments.models import Transfer
    from payments.mpesa import initiate_b2c_payment
    from .web3_utils import return_token_to_admin

    try:
        logger.info(f"[WITHDRAWAL] Starting withdrawal for {phone_number} | {amount} KES")

        # Step 1: Burn tokens (blockchain)
        crypto_result = return_token_to_admin(user_private_key, float(amount))

        if "error" in crypto_result:
            logger.error(f"[WITHDRAWAL] ❌ Blockchain burn failed: {crypto_result['error']}")
            Transfer.objects.create(
                from_address=sender_address,
                to_address="MPESA_WITHDRAWAL",
                amount=Decimal(str(amount)),
                tx_hash=None,
                status='FAILED'
            )
            return {"success": False, "error": crypto_result["error"]}

        logger.info(f"[WITHDRAWAL] ✅ Tokens burned — tx_hash: {crypto_result['tx_hash']}")

        # Step 2: Send M-Pesa B2C payout
        mpesa_resp = initiate_b2c_payment(phone_number, int(amount))

        if mpesa_resp.get("ResponseCode") == "0":
            Transfer.objects.create(
                from_address=sender_address,
                to_address="MPESA_WITHDRAWAL",
                amount=Decimal(str(amount)),
                tx_hash=crypto_result['tx_hash'],
                status='COMPLETED'
            )
            logger.info(f"[WITHDRAWAL] ✅ M-Pesa B2C sent to {phone_number}")
            return {"success": True, "tx_hash": crypto_result["tx_hash"]}
        else:
            error_msg = mpesa_resp.get('ResponseDescription', 'Unknown M-Pesa error')
            logger.error(f"[WITHDRAWAL] ❌ M-Pesa failed: {error_msg}")
            Transfer.objects.create(
                from_address=sender_address,
                to_address="MPESA_WITHDRAWAL",
                amount=Decimal(str(amount)),
                tx_hash=crypto_result['tx_hash'],
                status='FAILED'
            )
            return {"success": False, "error": error_msg}

    except Exception as exc:
        logger.error(f"[WITHDRAWAL] ❌ Unexpected error: {exc}")
        raise self.retry(exc=exc)