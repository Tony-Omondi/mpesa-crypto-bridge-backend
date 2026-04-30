from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.utils import timezone
from eth_account import Account
from eth_account.messages import encode_defunct
import secrets

from .serializers import UserRegistrationSerializer
from .models import User


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            "status": "Account Created",
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user_id": user.pk,
            "wallet": user.wallet_address
        })
    return Response(serializer.errors, status=400)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    phone = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(username=phone, password=password)
    if not user:
        return Response({"error": "Invalid Credentials"}, status=400)
    refresh = RefreshToken.for_user(user)
    return Response({
        "refresh": str(refresh),
        "access": str(refresh.access_token),
        "user_id": user.pk,
        "wallet_address": user.wallet_address
    })


# ─── WEB3 LOGIN ──────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def request_nonce(request):
    """
    Endpoint: GET /api/auth/request-nonce/?address=0x...
    Finds user by wallet address, generates a random nonce, saves it, returns it.
    Frontend will sign this nonce with the private key to prove wallet ownership.
    """
    address = request.query_params.get('address', '').strip().lower()

    if not address:
        return Response({"error": "Wallet address is required"}, status=400)

    try:
        # Find user by wallet address (case insensitive)
        user = User.objects.get(wallet_address__iexact=address)
    except User.DoesNotExist:
        return Response({"error": "No account found for this wallet address."}, status=404)

    # Generate a fresh random nonce
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
    Verifies the signature was made by the private key of the given address.
    If valid, issues JWT tokens.
    """
    address = request.data.get('address', '').strip()
    signature = request.data.get('signature', '').strip()

    if not address or not signature:
        return Response({"error": "Address and signature are required"}, status=400)

    try:
        user = User.objects.get(wallet_address__iexact=address)
    except User.DoesNotExist:
        return Response({"error": "No account found for this wallet address."}, status=404)

    # Check nonce hasn't expired (5 minutes)
    if not user.is_nonce_valid():
        return Response({"error": "Nonce expired. Please request a new one."}, status=400)

    # Reconstruct the exact message that was signed on the frontend
    message = f"Sign this message to authenticate with NitoWallet.\nNonce: {user.auth_nonce}"

    try:
        # Recover the address that signed this message
        encoded_message = encode_defunct(text=message)
        recovered_address = Account.recover_message(encoded_message, signature=signature)

        if recovered_address.lower() != address.lower():
            return Response({"error": "Signature verification failed."}, status=401)

    except Exception as e:
        return Response({"error": f"Invalid signature: {str(e)}"}, status=400)

    # ✅ Signature is valid! Clear the nonce so it can't be reused
    user.auth_nonce = None
    user.nonce_created_at = None
    user.save(update_fields=['auth_nonce', 'nonce_created_at'])

    # Issue JWT tokens
    refresh = RefreshToken.for_user(user)

    return Response({
        "status": "Authenticated",
        "refresh": str(refresh),
        "access": str(refresh.access_token),
        "user_id": user.pk,
        "wallet_address": user.wallet_address
    })


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    user = request.user
    new_phone = request.data.get('phone_number')
    if not new_phone:
        return Response({"error": "Phone number is required"}, status=400)
    user.phone_number = new_phone
    user.username = new_phone
    user.save()
    return Response({"status": "Profile Updated", "phone_number": user.phone_number})