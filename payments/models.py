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

    # 1. User Info
    phone_number = models.CharField(max_length=15)
    wallet_address = models.CharField(max_length=42)

    # 2. Money Info
    amount_kes = models.DecimalField(max_digits=10, decimal_places=2)
    amount_eth = models.DecimalField(max_digits=18, decimal_places=8) # This is the NIT amount
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=2, default=1.00)

    # 3. M-Pesa Technicals
    checkout_request_id = models.CharField(max_length=100, unique=True)
    mpesa_receipt = models.CharField(max_length=50, blank=True, null=True)

    # 4. Blockchain Technicals
    tx_hash = models.CharField(max_length=66, blank=True, null=True)
    
    # 5. Metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.phone_number} - {self.amount_kes} KES"