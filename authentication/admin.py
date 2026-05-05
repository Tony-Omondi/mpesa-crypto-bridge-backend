from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


class CustomUserAdmin(UserAdmin):
    model = User

    # ─── LIST VIEW ────────────────────────────────────────────────────────────
    list_display = (
        'id',
        'phone_number',
        'wallet_address',
        'privy_user_id',
        'is_seedless',
        'has_transaction_pin',
        'is_staff',
        'is_active',
        'date_joined',
    )

    list_filter = ('is_staff', 'is_active', 'date_joined')
    search_fields = ('phone_number', 'wallet_address', 'privy_user_id')
    ordering = ('-date_joined',)

    # ─── DETAIL / EDIT VIEW ───────────────────────────────────────────────────
    fieldsets = (
        (None, {
            'fields': ('phone_number', 'password')
        }),
        ('Personal Info', {
            'fields': ('username', 'email')
        }),
        ('Crypto / Wallet', {
            'fields': ('wallet_address',),
            'description': 'The on-chain wallet address for this user.'
        }),
        ('Privy Seedless Auth', {
            'fields': ('privy_user_id',),
            'description': (
                'Filled automatically when a user logs in via Privy (email/Google/Apple). '
                'Empty for users who registered with phone + password.'
            ),
        }),
        ('Web3 Nonce Auth', {
            'fields': ('auth_nonce', 'nonce_created_at'),
            'classes': ('collapse',),
            'description': 'Used for MetaMask-style signature login. Auto-managed.'
        }),
        ('Transaction PIN', {
            'fields': ('transaction_pin_hash', 'pin_attempts', 'pin_locked_until'),
            'classes': ('collapse',),
            'description': (
                'M-Pesa-style PIN required before every outgoing payment. '
                'Hash is stored — never the raw PIN. '
                'Locks for 30 mins after 3 failed attempts.'
            ),
        }),
        ('Permissions', {
            'fields': (
                'is_active',
                'is_staff',
                'is_superuser',
                'groups',
                'user_permissions',
            ),
            'classes': ('collapse',),
        }),
        ('Important Dates', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',),
        }),
    )

    # ─── CREATE USER VIEW ─────────────────────────────────────────────────────
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'phone_number',
                'username',
                'email',
                'password1',
                'password2',
                'wallet_address',
                'privy_user_id',
            ),
        }),
    )

    # ─── READ-ONLY FIELDS ─────────────────────────────────────────────────────
    # These are computed properties on the model — can't be edited directly
    readonly_fields = ('date_joined', 'last_login', 'nonce_created_at', 'pin_locked_until')

    # ─── CUSTOM DISPLAY METHODS ───────────────────────────────────────────────
    @admin.display(boolean=True, description='Seedless?')
    def is_seedless(self, obj):
        return obj.is_seedless

    @admin.display(boolean=True, description='PIN Set?')
    def has_transaction_pin(self, obj):
        return obj.has_transaction_pin


admin.site.register(User, CustomUserAdmin)