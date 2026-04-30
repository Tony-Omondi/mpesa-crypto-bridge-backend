from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    phone_number = models.CharField(max_length=15, unique=True)
    wallet_address = models.CharField(max_length=42, blank=True, null=True)

    # ✅ Web3 login fields
    auth_nonce = models.CharField(max_length=64, blank=True, null=True)
    nonce_created_at = models.DateTimeField(blank=True, null=True)

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['username', 'email']

    def __str__(self):
        return self.phone_number

    def is_nonce_valid(self):
        """Nonce expires after 5 minutes"""
        if not self.nonce_created_at:
            return False
        return (timezone.now() - self.nonce_created_at).seconds < 300