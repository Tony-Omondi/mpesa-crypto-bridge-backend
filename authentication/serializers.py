from rest_framework import serializers
from .models import User


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Original serializer — kept for backward compatibility.
    Used when a user registers with phone + password (non-Privy path).
    """
    class Meta:
        model = User
        fields = ['phone_number', 'password', 'wallet_address']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['phone_number'],
            phone_number=validated_data['phone_number'],
            password=validated_data['password']
        )
        if 'wallet_address' in validated_data:
            user.wallet_address = validated_data['wallet_address']
            user.save()
        return user


class PrivyAuthSerializer(serializers.Serializer):
    """
    Used for the Privy seedless auth flow.
    Frontend sends:
      - privy_token: the JWT Privy gives after email/Google/Apple login
      - wallet_address: the embedded wallet address Privy created for this user
      - phone_number: optional, pulled from Privy's user profile if available
    """
    privy_token = serializers.CharField(write_only=True)
    wallet_address = serializers.CharField(max_length=42, required=False, allow_blank=True)
    phone_number = serializers.CharField(max_length=15, required=False, allow_blank=True)


class TransactionPinSetSerializer(serializers.Serializer):
    """
    Used when a user sets or changes their transaction PIN.
    PIN must be 4–6 digits only (same rules as M-Pesa).
    """
    pin = serializers.CharField(min_length=4, max_length=6, write_only=True)

    def validate_pin(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("PIN must contain numbers only.")
        return value


class TransactionPinVerifySerializer(serializers.Serializer):
    """
    Used before processing any outgoing payment.
    Frontend always sends the PIN alongside the payment request.
    """
    pin = serializers.CharField(min_length=4, max_length=6, write_only=True)

    def validate_pin(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("PIN must contain numbers only.")
        return value


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for returning user info.
    Never exposes sensitive fields.
    """
    is_seedless = serializers.BooleanField(read_only=True)
    has_transaction_pin = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id',
            'phone_number',
            'wallet_address',
            'privy_user_id',
            'is_seedless',
            'has_transaction_pin',
            'date_joined',
        ]
        read_only_fields = fields