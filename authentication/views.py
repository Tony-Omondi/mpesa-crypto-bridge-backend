import requests
import secrets

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from eth_account import Account
from eth_account.messages import encode_defunct

from .serializers import (
    UserRegistrationSerializer,
    PrivyAuthSerializer,
    TransactionPinSetSerializer,
    TransactionPinVerifySerializer,
    UserProfileSerializer,
)
from .models import User


# ─── HELPER ──────────────────────────────────────────────────────────────────

def issue_jwt(user):
    """Issues a Django JWT pair for a given user. Used by all auth endpoints."""
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
        "user_id": user.pk,
        "wallet_address": user.wallet_address,
        "is_seedless": user.is_seedless,
        "has_transaction_pin": user.has_transaction_pin,
    }


# ─── ORIGINAL AUTH (phone + password) ────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    Classic registration with phone + password.
    Kept for backward compatibility and fallback.
    """
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        return Response({
            "status": "Account Created",
            **issue_jwt(user)
        })
    return Response(serializer.errors, status=400)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """Classic login with phone + password."""
    phone = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(username=phone, password=password)
    if not user:
        return Response({"error": "Invalid Credentials"}, status=400)
    return Response(issue_jwt(user))


# ─── PRIVY SEEDLESS AUTH ──────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def privy_auth(request):
    """
    Endpoint: POST /api/auth/privy/

    The full seedless login flow:
      1. User logs in on the frontend with email/Google/Apple via Privy SDK
      2. Privy SDK returns a privy_token + embedded wallet address
      3. Frontend sends both here
      4. We verify the token against Privy's API
      5. We get_or_create the user in our database
      6. We issue our own Django JWT — rest of the app works exactly the same

    This endpoint handles BOTH first-time registration AND returning login.
    Frontend doesn't need to know which one it is.
    """
    serializer = PrivyAuthSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    privy_token = serializer.validated_data['privy_token']
    wallet_address = serializer.validated_data.get('wallet_address', '')
    phone_number = serializer.validated_data.get('phone_number', '')

    # ── Step 1: Verify Privy token against Privy's API ────────────────────────
    try:
        privy_response = requests.get(
            "https://auth.privy.io/api/v1/users/me",
            headers={
                "Authorization": f"Bearer {privy_token}",
                "privy-app-id": settings.PRIVY_APP_ID,
                "privy-app-secret": settings.PRIVY_APP_SECRET,
            },
            timeout=10,
        )

        if privy_response.status_code != 200:
            return Response(
                {"error": "Privy token verification failed. Please log in again."},
                status=401
            )

        privy_data = privy_response.json()
        privy_user_id = privy_data.get('id')

        if not privy_user_id:
            return Response({"error": "Could not extract Privy user ID."}, status=400)

        # Pull phone from Privy's profile if frontend didn't send it
        if not phone_number:
            linked_accounts = privy_data.get('linked_accounts', [])
            for account in linked_accounts:
                if account.get('type') == 'phone':
                    phone_number = account.get('number', '')
                    break

    except requests.Timeout:
        return Response({"error": "Privy verification timed out. Try again."}, status=503)
    except Exception as e:
        return Response({"error": f"Privy verification error: {str(e)}"}, status=400)

    # ── Step 2: Get or create user in our database ────────────────────────────
    user, created = User.objects.get_or_create(
        privy_user_id=privy_user_id,
        defaults={
            # Use privy_user_id as Django username — user never sees this
            'username': privy_user_id,
            'phone_number': phone_number,
            'wallet_address': wallet_address,
        }
    )

    # ── Step 3: Sync latest data if returning user ────────────────────────────
    if not created:
        updated_fields = []
        # Wallet may change if Privy rotates keys
        if wallet_address and user.wallet_address != wallet_address:
            user.wallet_address = wallet_address
            updated_fields.append('wallet_address')
        # Phone may have been added later
        if phone_number and not user.phone_number:
            user.phone_number = phone_number
            updated_fields.append('phone_number')
        if updated_fields:
            user.save(update_fields=updated_fields)

    # ── Step 4: Issue our own JWT ─────────────────────────────────────────────
    return Response({
        "status": "Account Created" if created else "Authenticated",
        "is_new_user": created,
        **issue_jwt(user)
    })


# ─── WEB3 NONCE LOGIN (MetaMask / external wallets) ──────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def request_nonce(request):
    """
    Endpoint: GET /api/auth/request-nonce/?address=0x...
    For MetaMask / external wallet login. Seedless users don't need this.
    """
    address = request.query_params.get('address', '').strip().lower()

    if not address:
        return Response({"error": "Wallet address is required"}, status=400)

    try:
        user = User.objects.get(wallet_address__iexact=address)
    except User.DoesNotExist:
        return Response({"error": "No account found for this wallet address."}, status=404)

    nonce = secrets.token_hex(32)
    user.auth_nonce = nonce
    user.nonce_created_at = timezone.now()
    user.save(update_fields=['auth_nonce', 'nonce_created_at'])

    return Response({
        "nonce": nonce,
        "message": f"Sign this message to authenticate with NitoWallet.\nNonce: {nonce}"
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_signature(request):
    """
    Endpoint: POST /api/auth/verify-signature/
    Body: { "address": "0x...", "signature": "0x..." }
    For MetaMask / external wallet login. Seedless users don't need this.
    """
    address = request.data.get('address', '').strip()
    signature = request.data.get('signature', '').strip()

    if not address or not signature:
        return Response({"error": "Address and signature are required"}, status=400)

    try:
        user = User.objects.get(wallet_address__iexact=address)
    except User.DoesNotExist:
        return Response({"error": "No account found for this wallet address."}, status=404)

    if not user.is_nonce_valid():
        return Response({"error": "Nonce expired. Please request a new one."}, status=400)

    message = f"Sign this message to authenticate with NitoWallet.\nNonce: {user.auth_nonce}"

    try:
        encoded_message = encode_defunct(text=message)
        recovered_address = Account.recover_message(encoded_message, signature=signature)

        if recovered_address.lower() != address.lower():
            return Response({"error": "Signature verification failed."}, status=401)

    except Exception as e:
        return Response({"error": f"Invalid signature: {str(e)}"}, status=400)

    # Clear nonce so it cannot be reused
    user.auth_nonce = None
    user.nonce_created_at = None
    user.save(update_fields=['auth_nonce', 'nonce_created_at'])

    return Response({
        "status": "Authenticated",
        **issue_jwt(user)
    })


# ─── TRANSACTION PIN ──────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_transaction_pin(request):
    """
    Endpoint: POST /api/auth/set-pin/
    Body: { "pin": "1234" }

    Called once after registration so the user sets their M-Pesa-style PIN.
    Also used when changing the PIN.
    A hacked email/JWT alone cannot send money — PIN is always required.
    """
    serializer = TransactionPinSetSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    pin = serializer.validated_data['pin']
    request.user.transaction_pin_hash = make_password(pin)
    request.user.pin_attempts = 0
    request.user.pin_locked_until = None
    request.user.save(update_fields=['transaction_pin_hash', 'pin_attempts', 'pin_locked_until'])

    return Response({"status": "Transaction PIN set successfully."})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_transaction_pin(request):
    """
    Endpoint: POST /api/auth/verify-pin/
    Body: { "pin": "1234" }

    Call this inside any payment/send endpoint BEFORE processing the transaction.
    3 wrong attempts = 30 minute lockout (same as M-Pesa).
    """
    user = request.user

    if not user.has_transaction_pin:
        return Response({"error": "No transaction PIN set. Please set a PIN first."}, status=400)

    if user.is_pin_locked():
        return Response({
            "error": "Too many wrong attempts. Account locked for 30 minutes.",
            "locked_until": user.pin_locked_until,
        }, status=403)

    serializer = TransactionPinVerifySerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    pin = serializer.validated_data['pin']

    if not check_password(pin, user.transaction_pin_hash):
        user.increment_pin_attempts()
        attempts_left = max(0, 3 - user.pin_attempts)
        return Response({
            "error": "Wrong PIN.",
            "attempts_remaining": attempts_left,
        }, status=401)

    # PIN correct — reset attempts
    user.reset_pin_attempts()
    return Response({"status": "PIN verified."})


# ─── PROFILE ──────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_profile(request):
    """Endpoint: GET /api/auth/profile/"""
    serializer = UserProfileSerializer(request.user)
    return Response(serializer.data)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """
    Endpoint: PATCH /api/auth/profile/update/
    Body: { "phone_number": "0712345678" }
    """
    user = request.user
    new_phone = request.data.get('phone_number')
    if not new_phone:
        return Response({"error": "Phone number is required"}, status=400)
    user.phone_number = new_phone
    user.username = new_phone
    user.save()
    return Response({"status": "Profile Updated", "phone_number": user.phone_number})