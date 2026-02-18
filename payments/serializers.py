# payments/serializers.py
from rest_framework import serializers
from .models import CryptoOrder, Transfer
from web3 import Web3

class InitiateTradeSerializer(serializers.ModelSerializer):
    """
    Validates data from the App before creating an Order.
    """
    class Meta:
        model = CryptoOrder
        fields = ['amount_kes', 'phone_number', 'wallet_address']

    def validate_amount_kes(self, value):
        if value < 1: # Minimum 1 KES for easier testing
            raise serializers.ValidationError("Minimum amount is 1 KES.")
        return value

    def validate_wallet_address(self, value):
        if not Web3.is_address(value):
            raise serializers.ValidationError("Invalid Ethereum Address.")
        return value

class CryptoOrderSerializer(serializers.ModelSerializer):
    """
    Returns the full order status to the App.
    """
    class Meta:
        model = CryptoOrder
        fields = '__all__'
        read_only_fields = ['status', 'tx_hash', 'amount_nit', 'checkout_request_id', 'mpesa_receipt']

class UnifiedTransactionSerializer(serializers.Serializer):
    """
    Merges CryptoOrder (Deposits) and Transfers (P2P) into a single feed.
    """
    id = serializers.IntegerField()
    type = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
    tx_hash = serializers.CharField(required=False, allow_null=True)
    from_address = serializers.CharField(required=False, allow_null=True)
    to_address = serializers.CharField(required=False, allow_null=True)

    def get_type(self, obj):
        if isinstance(obj, CryptoOrder):
            return "DEPOSIT"
        return "TRANSFER"

    def get_amount(self, obj):
        # M-Pesa deposits use 'amount_kes', P2P uses 'amount'
        return getattr(obj, 'amount_kes', getattr(obj, 'amount', 0))