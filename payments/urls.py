# payments/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Initiate Deposit
    path('pay/', views.initiate_payment, name='initiate_payment'),
    
    # Callback from Safaricom
    path('callback/', views.mpesa_callback, name='mpesa_callback'),
    
    # Transaction History
    path('history/', views.transaction_history, name='transaction_history'), 
]