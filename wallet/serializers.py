# wallet/serializers.py
from rest_framework import serializers
from web3 import Web3


class TransferSerializer(serializers.Serializer):
    to_address = serializers.CharField(max_length=42)
    amount = serializers.DecimalField(max_digits=30, decimal_places=18)
    tx_hash = serializers.CharField(max_length=100)  # ✅ Replaces privateKey

    def validate_to_address(self, value):
        if not Web3.is_address(value):
            raise serializers.ValidationError("Invalid Wallet Address")
        return value

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero")
        return value

    def validate_tx_hash(self, value):
        if not value.startswith('0x'):
            raise serializers.ValidationError("Invalid transaction hash format")
        return value


class WithdrawalSerializer(serializers.Serializer):
    """Validates Withdrawal requests — blockchain burn already done on device"""
    amount = serializers.DecimalField(max_digits=30, decimal_places=2)
    phone_number = serializers.CharField(max_length=15)
    tx_hash = serializers.CharField(max_length=100)  # ✅ Replaces privateKey

    def validate_amount(self, value):
        if value < 10:
            raise serializers.ValidationError("Minimum withdrawal is 10 KES")
        return value

    def validate_tx_hash(self, value):
        if not value.startswith('0x'):
            raise serializers.ValidationError("Invalid transaction hash format")
        return value