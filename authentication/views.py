from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token 
from django.contrib.auth import authenticate
from .serializers import UserRegistrationSerializer

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    Endpoint: /api/auth/register/
    Registers a new user and returns an auth token.
    """
    serializer = UserRegistrationSerializer(data=request.data)
    
    if serializer.is_valid():
        user = serializer.save()
        # Create a Token immediately so they are logged in
        token, _ = Token.objects.get_or_create(user=user)
        
        return Response({
            "status": "Account Created",
            "token": token.key, 
            "user_id": user.pk,
            "wallet": user.wallet_address
        })
        
    return Response(serializer.errors, status=400)

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    Endpoint: /api/auth/login/
    Authenticates user via phone number and password.
    """
    phone = request.data.get('username') 
    password = request.data.get('password')
    
    user = authenticate(username=phone, password=password)
    
    if not user:
        return Response({"error": "Invalid Credentials"}, status=400)
        
    token, _ = Token.objects.get_or_create(user=user)
    
    return Response({
        "token": token.key, 
        "user_id": user.pk,
        "wallet_address": user.wallet_address
    })

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """
    Endpoint: /api/auth/profile/update/
    Allows the authenticated user to update their phone number.
    """
    user = request.user
    new_phone = request.data.get('phone_number')

    if not new_phone:
        return Response({"error": "Phone number is required"}, status=400)

    # In this setup, username is the phone_number
    user.phone_number = new_phone
    user.username = new_phone
    user.save()

    return Response({
        "status": "Profile Updated",
        "phone_number": user.phone_number
    })