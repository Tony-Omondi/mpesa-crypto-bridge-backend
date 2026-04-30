from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


class CustomUserAdmin(UserAdmin):
    model = User

    # ✅ What shows in the user list
    list_display = (
        'id',
        'phone_number',
        'wallet_address',
        'is_staff',
        'is_active',
        'date_joined'
    )

    # ✅ Make phone searchable (since it's your login field)
    search_fields = ('phone_number', 'wallet_address')

    ordering = ('-date_joined',)

    # ✅ Fields when viewing/editing a user
    fieldsets = (
        (None, {'fields': ('phone_number', 'password')}),
        ('Personal Info', {'fields': ('username', 'email')}),
        ('Crypto Details', {'fields': ('wallet_address',)}),
        ('Web3 Auth', {'fields': ('auth_nonce', 'nonce_created_at')}),
        ('Permissions', {
            'fields': (
                'is_active',
                'is_staff',
                'is_superuser',
                'groups',
                'user_permissions'
            )
        }),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )

    # ✅ Fields when creating a user
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
            ),
        }),
    )


admin.site.register(User, CustomUserAdmin)