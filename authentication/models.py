from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    # We use phone number as the unique identifier
    phone_number = models.CharField(max_length=15, unique=True)
    wallet_address = models.CharField(max_length=42, blank=True, null=True)
    
    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['username', 'email']

    def __str__(self):
        return self.phone_number