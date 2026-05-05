# payments/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('pay/', views.initiate_payment, name='initiate_payment'),
    path('request/', views.request_payment, name='request_payment'),  # ✅ Added Request Payment endpoint
    path('callback/', views.mpesa_callback, name='mpesa_callback'),
    path('history/', views.transaction_history, name='transaction_history'),
    path('status/<int:order_id>/', views.payment_status, name='payment_status'),
    path('retry/<int:order_id>/', views.retry_mint, name='retry_mint'),  # ← Admin retry
]