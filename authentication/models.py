from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    # ─── CORE IDENTITY ───────────────────────────────────────────────────────
    phone_number = models.CharField(max_length=15, unique=True, blank=True)
    wallet_address = models.CharField(max_length=42, blank=True, null=True)

    # ─── PRIVY SEEDLESS AUTH ─────────────────────────────────────────────────
    # This is the unique ID Privy assigns every user (format: did:privy:xxxxxxxx)
    # When a user logs in via email/Google/Apple through Privy, this is their identity.
    # We verify their Privy token on the backend, then issue our own Django JWT.
    privy_user_id = models.CharField(max_length=100, unique=True, blank=True, null=True)

    # ─── WEB3 NONCE LOGIN (kept for MetaMask / power users) ──────────────────
    auth_nonce = models.CharField(max_length=64, blank=True, null=True)
    nonce_created_at = models.DateTimeField(blank=True, null=True)

    # ─── TRANSACTION PIN SECURITY ────────────────────────────────────────────
    # This is the M-Pesa-style PIN required before every outgoing payment.
    # Even if someone hijacks the JWT, they still can't send money without the PIN.
    transaction_pin_hash = models.CharField(max_length=128, blank=True, null=True)
    pin_attempts = models.IntegerField(default=0)
    pin_locked_until = models.DateTimeField(blank=True, null=True)

    # ─── DJANGO CONFIG ────────────────────────────────────────────────────────
    USERNAME_FIELD = 'phone_number'
    # Removed 'email' from REQUIRED_FIELDS — mama mboga may not have email
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.phone_number or self.privy_user_id or f"User #{self.pk}"

    # ─── NONCE HELPERS ───────────────────────────────────────────────────────
    def is_nonce_valid(self):
        """Nonce expires after 5 minutes"""
        if not self.nonce_created_at:
            return False
        return (timezone.now() - self.nonce_created_at).seconds < 300

    # ─── PIN HELPERS ─────────────────────────────────────────────────────────
    def is_pin_locked(self):
        """Returns True if user has exceeded PIN attempts and is locked out"""
        if not self.pin_locked_until:
            return False
        return timezone.now() < self.pin_locked_until

    def increment_pin_attempts(self):
        """
        Increments failed PIN attempts.
        Locks the account for 30 minutes after 3 failed attempts (same as M-Pesa).
        """
        self.pin_attempts += 1
        if self.pin_attempts >= 3:
            self.pin_locked_until = timezone.now() + timezone.timedelta(minutes=30)
        self.save(update_fields=['pin_attempts', 'pin_locked_until'])

    def reset_pin_attempts(self):
        """Call this on successful PIN entry"""
        self.pin_attempts = 0
        self.pin_locked_until = None
        self.save(update_fields=['pin_attempts', 'pin_locked_until'])

    # ─── CONVENIENCE PROPERTIES ──────────────────────────────────────────────
    @property
    def is_seedless(self):
        """True if this user signed up via Privy (no seed phrase ever shown)"""
        return self.privy_user_id is not None

    @property
    def has_transaction_pin(self):
        """True if user has set up their transaction PIN"""
        return bool(self.transaction_pin_hash)