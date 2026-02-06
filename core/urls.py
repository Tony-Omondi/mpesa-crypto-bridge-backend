from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Connects the Authentication App (Login/Register)
    path('api/auth/', include('authentication.urls')),
    
    # Connects the Payments App (M-Pesa)
    path('api/payments/', include('payments.urls')),
    path('api/wallet/', include('wallet.urls')), # <--- Add this
]