
from django.db import models


class CryptoOrder(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Waiting for M-Pesa PIN'),
        ('PAID', 'M-Pesa Payment Received'),
        ('PROCESSING', 'Sending Crypto to Wallet'),
        ('COMPLETED', 'Crypto Sent Successfully'),
        ('FAILED', 'Transaction Failed'),
        ('PAID_BUT_FAILED', 'Paid but Crypto Fail'),
    ]

    REQUEST_TYPE_CHOICES = [
        ('DEPOSIT', 'Self Deposit'),
        ('REQUEST', 'Payment Request from Peer'),
    ]

    # User Info
    phone_number = models.CharField(max_length=15)
    wallet_address = models.CharField(max_length=42, db_index=True)

    # Money Info
    amount_kes = models.DecimalField(max_digits=10, decimal_places=2)
    amount_eth = models.DecimalField(max_digits=18, decimal_places=8)
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=2, default=1.00)

    # ✅ Fee fields
    fee_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    requester_wallet = models.CharField(max_length=42, blank=True, null=True)  # who requested the payment
    request_type = models.CharField(max_length=10, choices=REQUEST_TYPE_CHOICES, default='DEPOSIT')

    # M-Pesa Technicals
    checkout_request_id = models.CharField(max_length=100, unique=True, db_index=True)
    mpesa_receipt = models.CharField(max_length=50, blank=True, null=True)

    # Blockchain Technicals
    tx_hash = models.CharField(max_length=66, blank=True, null=True)
    fee_tx_hash = models.CharField(max_length=66, blank=True, null=True)  # ✅ fee mint tx

    # Metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', db_index=True)
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['wallet_address', 'status']),
            models.Index(fields=['requester_wallet']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.phone_number} - {self.amount_kes} KES ({self.request_type})"


class Transfer(models.Model):
    """Tracks Peer-to-Peer token transfers."""
    from_address = models.CharField(max_length=255, db_index=True)
    to_address = models.CharField(max_length=255, db_index=True)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    tx_hash = models.CharField(max_length=255, unique=True, null=True, blank=True)
    status = models.CharField(max_length=20, default='COMPLETED', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['from_address', 'created_at']),
            models.Index(fields=['to_address', 'created_at']),
        ]

    def __str__(self):
        return f"{self.from_address} -> {self.to_address} ({self.amount} NIT)"
