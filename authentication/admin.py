from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    model = User
    # 1. Columns to show in the list view
    list_display = ['username', 'phone_number', 'wallet_address', 'is_staff', 'date_joined']
    
    # 2. Add our custom fields to the "Edit User" page
    fieldsets = UserAdmin.fieldsets + (
        ('Crypto Details', {'fields': ('phone_number', 'wallet_address')}),
    )
    
    # 3. Add them to the "Add User" page too
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('phone_number', 'wallet_address')}),
    )

admin.site.register(User, CustomUserAdmin)