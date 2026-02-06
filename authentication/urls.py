from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    # NEW: The missing link that fixes the 404/Network Error
    path('profile/update/', views.update_profile, name='update_profile'),
]