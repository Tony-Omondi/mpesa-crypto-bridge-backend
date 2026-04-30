from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('profile/update/', views.update_profile, name='update_profile'),

    # ✅ Web3 Login endpoints
    path('request-nonce/', views.request_nonce, name='request_nonce'),
    path('verify-signature/', views.verify_signature, name='verify_signature'),
]