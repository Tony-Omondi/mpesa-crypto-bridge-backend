from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView # NEW: Import the refresh view
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    
    # NEW: Endpoint to get a new access token using the refresh token
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'), 
    
    path('profile/update/', views.update_profile, name='update_profile'),
]