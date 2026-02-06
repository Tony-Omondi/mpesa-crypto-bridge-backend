# wallet/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create_wallet, name='create_wallet'),
    path('restore/', views.restore_wallet, name='restore_wallet'),
    path('balance/<str:address>/', views.get_balance, name='get_balance'),
    path('transfer/', views.transfer_funds, name='transfer_funds'),
    
    # NEW Withdrawal Endpoint
    path('withdraw/', views.withdraw_to_mpesa, name='withdraw_to_mpesa'),
    
    path('estimate_gas/', views.estimate_gas, name='estimate_gas'),
]