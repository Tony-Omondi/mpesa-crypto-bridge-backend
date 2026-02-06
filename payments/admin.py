from django.contrib import admin
from .models import CryptoOrder

@admin.register(CryptoOrder)
class CryptoOrderAdmin(admin.ModelAdmin):
    # These names MUST exist in your models.py
    list_display = (
        'phone_number', 
        'amount_kes', 
        'amount_eth',  # <--- If your model has amount_eth, keep this. 
        'status', 
        'created_at'
    )
    
    readonly_fields = (
        'status', 
        'tx_hash', 
        'amount_eth', 
        'checkout_request_id', 
        'mpesa_receipt', 
        'exchange_rate'
    )