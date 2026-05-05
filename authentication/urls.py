from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [

    # ─── CLASSIC AUTH (phone + password) ─────────────────────────────────────
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # ─── PRIVY SEEDLESS AUTH ──────────────────────────────────────────────────
    # Single endpoint — handles both new registration AND returning login.
    # Frontend just always calls this after Privy login. Backend figures it out.
    path('privy/', views.privy_auth, name='privy_auth'),

    # ─── WEB3 NONCE LOGIN (MetaMask / external wallets) ──────────────────────
    path('request-nonce/', views.request_nonce, name='request_nonce'),
    path('verify-signature/', views.verify_signature, name='verify_signature'),

    # ─── TRANSACTION PIN ──────────────────────────────────────────────────────
    # set-pin:    Called once after first login to create M-Pesa-style PIN
    # verify-pin: Called before every outgoing payment to confirm identity
    path('set-pin/', views.set_transaction_pin, name='set_transaction_pin'),
    path('verify-pin/', views.verify_transaction_pin, name='verify_transaction_pin'),

    # ─── PROFILE ──────────────────────────────────────────────────────────────
    path('profile/', views.get_profile, name='get_profile'),
    path('profile/update/', views.update_profile, name='update_profile'),

]