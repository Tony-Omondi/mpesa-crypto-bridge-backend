from rest_framework import serializers
from .models import User

class UserRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['phone_number', 'password', 'wallet_address']
        # Hide password from the response so it's not sent back to the phone
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        # We use create_user to ensure the password is hashed (encrypted)
        user = User.objects.create_user(
            username=validated_data['phone_number'], # Django requires a username
            phone_number=validated_data['phone_number'],
            password=validated_data['password']
        )
        
        # Save the wallet address if the phone sent it
        if 'wallet_address' in validated_data:
            user.wallet_address = validated_data['wallet_address']
            user.save()
            
        return user