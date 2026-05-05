
# payments/views.py
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from decimal import Decimal
from django.shortcuts import get_object_or_404
from django.db.models import Q
from itertools import chain
from operator import attrgetter
import uuid

from .models import CryptoOrder, Transfer
from .serializers import InitiateTradeSerializer, UnifiedTransactionSerializer
from .mpesa import initiate_stk_push
from .tasks import process_mint

FEE_RATE = Decimal('0.005')  # 0.5%


class StkPushThrottle(AnonRateThrottle):
    rate = '5/min'


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([StkPushThrottle])
def initiate_payment(request):
    """
    Endpoint: /api/payments/pay/
    Standard self-deposit. User pays M-Pesa, gets NIT minted to own wallet.
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
            checkout_request_id=temp_id,
            request_type='DEPOSIT',
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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([StkPushThrottle])
def request_payment(request):
    """
    Endpoint: /api/payments/request/
    Send STK push to ANY phone number to request payment.
    0.5% fee deducted — goes to admin wallet.
    NIT minted to the REQUESTER's wallet (not the payer's).

    Body: { phone_number, amount_kes }
    The authenticated user's wallet_address is automatically used as requester.
    """
    phone_number = request.data.get('phone_number')
    amount_kes = request.data.get('amount_kes')

    if not phone_number:
        return Response({"error": "phone_number is required"}, status=400)
    if not amount_kes:
        return Response({"error": "amount_kes is required"}, status=400)

    try:
        amount_kes = Decimal(str(amount_kes))
        if amount_kes < 5:
            return Response({"error": "Minimum amount is 5 KES"}, status=400)
    except Exception:
        return Response({"error": "Invalid amount"}, status=400)

    # Requester is the authenticated user
    requester_wallet = request.user.wallet_address
    if not requester_wallet:
        return Response({"error": "Your wallet address is not set. Please update your profile."}, status=400)

    # Calculate fee breakdown for display
    fee_kes = (amount_kes * FEE_RATE).quantize(Decimal('0.01'))
    requester_receives = (amount_kes - fee_kes).quantize(Decimal('0.01'))

    exchange_rate = Decimal("1.00")
    amount_nit = amount_kes / exchange_rate
    temp_id = f"TEMP_{uuid.uuid4()}"

    order = CryptoOrder.objects.create(
        phone_number=phone_number,
        wallet_address=requester_wallet,  # used as fallback
        requester_wallet=requester_wallet,
        amount_kes=amount_kes,
        amount_eth=amount_nit,
        exchange_rate=exchange_rate,
        fee_amount=fee_kes,
        checkout_request_id=temp_id,
        request_type='REQUEST',
    )

    try:
        mpesa_res = initiate_stk_push(
            phone_number=phone_number,
            amount=int(amount_kes),
            order_id=order.id
        )
        if mpesa_res.get('ResponseCode') == '0':
            order.checkout_request_id = mpesa_res.get('CheckoutRequestID')
            order.save()
            return Response({
                "status": "STK_SENT",
                "message": f"Payment request sent to {phone_number}",
                "order_id": order.id,
                "amount_kes": str(amount_kes),
                "fee_kes": str(fee_kes),
                "you_receive_nit": str(requester_receives),
            })
        else:
            order.delete()
            return Response({"error": "M-Pesa rejection", "details": mpesa_res}, status=400)
    except Exception as e:
        order.delete()
        return Response({"error": str(e)}, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def transaction_history(request):
    """Endpoint: /api/payments/history/"""
    wallet_address = request.query_params.get('wallet_address')
    if not wallet_address:
        return Response({"error": "Wallet address required"}, status=400)

    orders = CryptoOrder.objects.filter(
        Q(wallet_address__iexact=wallet_address) |
        Q(requester_wallet__iexact=wallet_address)
    )
    transfers = Transfer.objects.filter(
        Q(from_address__iexact=wallet_address) | Q(to_address__iexact=wallet_address)
    )

    combined_list = sorted(
        chain(orders, transfers),
        key=attrgetter('created_at'),
        reverse=True
    )[:50]

    serializer = UnifiedTransactionSerializer(combined_list, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_status(request, order_id):
    """Endpoint: /api/payments/status/<order_id>/"""
    try:
        order = CryptoOrder.objects.get(id=order_id)
        return Response({
            "order_id": order.id,
            "status": order.status,
            "amount_kes": str(order.amount_kes),
            "fee_amount": str(order.fee_amount),
            "request_type": order.request_type,
            "tx_hash": order.tx_hash,
            "mpesa_receipt": order.mpesa_receipt,
            "error_message": order.error_message,
        })
    except CryptoOrder.DoesNotExist:
        return Response({"error": "Order not found"}, status=404)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def retry_mint(request, order_id):
    """Admin endpoint to retry PAID_BUT_FAILED orders."""
    if not request.user.is_staff:
        return Response({"error": "Admin access required"}, status=403)
    try:
        order = CryptoOrder.objects.get(id=order_id)
        if order.status != 'PAID_BUT_FAILED':
            return Response({"error": f"Cannot retry — status is '{order.status}'"}, status=400)
        order.status = 'PAID'
        order.error_message = None
        order.save()
        process_mint.delay(order.id)
        return Response({"status": "Retry queued", "order_id": order.id})
    except CryptoOrder.DoesNotExist:
        return Response({"error": "Order not found"}, status=404)


@api_view(['POST'])
@permission_classes([AllowAny])
def mpesa_callback(request):
    """Endpoint: /api/payments/callback/"""
    data = request.data
    if 'Body' not in data or 'stkCallback' not in data.get('Body', {}):
        return Response({"status": "Invalid callback structure"}, status=200)

    try:
        stk_callback = data['Body']['stkCallback']
        checkout_id = stk_callback.get('CheckoutRequestID')
        result_code = stk_callback.get('ResultCode')

        if not checkout_id:
            return Response({"status": "No CheckoutID"}, status=200)

        order = get_object_or_404(CryptoOrder, checkout_request_id=checkout_id)

        if result_code == 0:
            meta = stk_callback.get('CallbackMetadata', {}).get('Item', [])
            receipt = next((i['Value'] for i in meta if i['Name'] == 'MpesaReceiptNumber'), "N/A")
            order.status = 'PAID'
            order.mpesa_receipt = receipt
            order.save()
            process_mint.delay(order.id)
        else:
            order.status = 'FAILED'
            order.error_message = stk_callback.get('ResultDesc', 'User Cancelled')
            order.save()

    except Exception as e:
        print(f"Callback Error: {e}")

    return Response({"status": "Received"})
