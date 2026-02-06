# payments/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from decimal import Decimal
from django.shortcuts import get_object_or_404
import uuid

from .models import CryptoOrder
from .serializers import InitiateTradeSerializer, CryptoOrderSerializer
from .mpesa import initiate_stk_push
from wallet.web3_utils import mint_token_to_user 

@api_view(['POST'])
@permission_classes([AllowAny]) # AllowAny for testing, change to IsAuthenticated in production
def initiate_payment(request):
    """
    Endpoint: /api/payments/pay/
    Triggers M-Pesa STK Push and creates a PENDING order.
    """
    serializer = InitiateTradeSerializer(data=request.data)
    if serializer.is_valid():
        amount_kes = serializer.validated_data['amount_kes']
        exchange_rate = Decimal("1.00") 
        amount_nit = Decimal(amount_kes) / exchange_rate
        
        temp_id = f"TEMP_{uuid.uuid4()}"

        order = CryptoOrder.objects.create(
            phone_number=serializer.validated_data['phone_number'],
            wallet_address=serializer.validated_data['wallet_address'],
            amount_kes=amount_kes,
            amount_eth=amount_nit, 
            exchange_rate=exchange_rate,
            checkout_request_id=temp_id
        )

        try:
            mpesa_res = initiate_stk_push(
                phone_number=order.phone_number,
                amount=amount_kes,
                order_id=order.id
            )

            if mpesa_res.get('ResponseCode') == '0':
                order.checkout_request_id = mpesa_res.get('CheckoutRequestID')
                order.save()
                return Response({"status": "STK_SENT", "message": "Enter PIN", "order_id": order.id})
            else:
                order.delete()
                return Response({"error": "M-Pesa rejection", "details": mpesa_res}, status=400)
        except Exception as e:
            order.delete()
            return Response({"error": str(e)}, status=500)

    return Response(serializer.errors, status=400)

@api_view(['GET'])
@permission_classes([AllowAny])
def transaction_history(request):
    """
    Endpoint: /api/payments/history/
    """
    wallet_address = request.query_params.get('wallet_address')
    if not wallet_address:
        return Response({"error": "Wallet address required"}, status=400)

    orders = CryptoOrder.objects.filter(wallet_address=wallet_address).order_by('-created_at')
    serializer = CryptoOrderSerializer(orders, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([AllowAny])
def mpesa_callback(request):
    """
    Endpoint: /api/payments/callback/
    Safaricom calls this. If ResultCode is 0, we mint NIT tokens.
    """
    data = request.data
    try:
        stk_callback = data.get('Body', {}).get('stkCallback', {})
        checkout_id = stk_callback.get('CheckoutRequestID')
        result_code = stk_callback.get('ResultCode')

        if not checkout_id:
            return Response({"status": "No CheckoutID"}, status=200)

        order = get_object_or_404(CryptoOrder, checkout_request_id=checkout_id)

        if result_code == 0:
            meta = stk_callback['CallbackMetadata']['Item']
            receipt = next((i['Value'] for i in meta if i['Name'] == 'MpesaReceiptNumber'), "N/A")

            order.status = 'PAID'
            order.mpesa_receipt = receipt
            order.save()

            # --- MINTING LOGIC ---
            print(f"Minting {order.amount_kes} NIT to {order.wallet_address}")
            tx_hash = mint_token_to_user(order.wallet_address, order.amount_kes)

            if tx_hash:
                order.status = 'COMPLETED'
                order.tx_hash = tx_hash
                print(f"Mint Success: {tx_hash}")
            else:
                order.status = 'PAID_BUT_FAILED'
                order.error_message = "Blockchain Minting Error"
                print("Mint Failed")
            
            order.save()
        else:
            order.status = 'FAILED'
            order.error_message = stk_callback.get('ResultDesc', 'User Cancelled')
            order.save()

    except Exception as e:
        print(f"Callback Error: {e}")
        
    return Response({"status": "Received"})