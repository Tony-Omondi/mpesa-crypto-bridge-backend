# wallet/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from eth_account import Account
from decimal import Decimal
from web3 import Web3

from .serializers import TransferSerializer, WithdrawalSerializer
from .web3_utils import get_wallet_balance, w3
from payments.models import Transfer
from payments.mpesa import initiate_b2c_payment

Account.enable_unaudited_hdwallet_features()


@api_view(['GET'])
@permission_classes([AllowAny])  # Public — needed during wallet creation before auth
def create_wallet(request):
    try:
        acct, mnemonic = Account.create_with_mnemonic()
        return Response({
            "address": acct.address,
            "privateKey": acct.key.hex(),
            "mnemonic": {"phrase": mnemonic}
        })
    except Exception as e:
        return Response({"error": "Failed to generate wallet"}, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])  # Public — needed during wallet restore before auth
def restore_wallet(request):
    mnemonic_phrase = request.data.get('mnemonic')
    if not mnemonic_phrase:
        return Response({"error": "Mnemonic is required"}, status=400)

    try:
        acct = Account.from_mnemonic(mnemonic_phrase)
        return Response({
            "address": acct.address,
            "privateKey": acct.key.hex(),
            "mnemonic": {"phrase": mnemonic_phrase}
        })
    except Exception as e:
        return Response({"error": "Invalid Mnemonic Phrase"}, status=400)


@api_view(['GET'])
@permission_classes([AllowAny])  # 🔒 Locked
def get_balance(request, address):
    if not w3.is_address(address):
        return Response({"error": "Invalid address"}, status=400)

    nit, eth = get_wallet_balance(address)
    if nit is None:
        return Response({
            "address": address, "balance_eth": 0.0, "balance_nit": 0.0,
            "status": "Offline", "message": "Blockchain unreachable"
        }, status=200)

    return Response({
        "address": address, "balance_eth": float(eth), "balance_nit": float(nit),
        "currency": "NIT", "status": "Success"
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])  # 🔒 Locked
def transfer_funds(request):
    """
    Endpoint: /api/wallet/transfer/
    Blockchain transfer already done on device.
    Django just records the tx in history.
    """
    serializer = TransferSerializer(data=request.data)
    if serializer.is_valid():
        to_addr = serializer.validated_data['to_address']
        amount = serializer.validated_data['amount']
        tx_hash = serializer.validated_data['tx_hash']

        # Derive sender address from the authenticated user's wallet
        sender_address = request.user.wallet_address

        # ✅ Record the completed transfer in history
        Transfer.objects.create(
            from_address=sender_address,
            to_address=to_addr,
            amount=Decimal(str(amount)),
            tx_hash=tx_hash,
            status='COMPLETED'
        )

        return Response({
            "result": True,
            "message": "Transfer recorded successfully.",
            "tx_hash": tx_hash,
            "from": sender_address,
            "to": to_addr,
            "amount": str(amount)
        })

    return Response(serializer.errors, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])  # 🔒 Locked
def withdraw_to_mpesa(request):
    """
    Endpoint: /api/wallet/withdraw/
    Blockchain burn already done on device.
    Django just triggers the M-Pesa B2C payout.
    """
    serializer = WithdrawalSerializer(data=request.data)
    if serializer.is_valid():
        amount = serializer.validated_data['amount']
        phone = serializer.validated_data['phone_number']
        tx_hash = serializer.validated_data['tx_hash']

        sender_address = request.user.wallet_address

        try:
            # ✅ Tokens already burned on device — just send M-Pesa payout
            mpesa_resp = initiate_b2c_payment(phone, int(amount))

            if mpesa_resp.get("ResponseCode") == "0":
                Transfer.objects.create(
                    from_address=sender_address,
                    to_address="MPESA_WITHDRAWAL",
                    amount=Decimal(str(amount)),
                    tx_hash=tx_hash,
                    status='COMPLETED'
                )

                return Response({
                    "result": True,
                    "message": "Withdrawal processing — M-Pesa payment will arrive shortly.",
                    "phone": phone,
                    "amount": str(amount),
                    "tx_hash": tx_hash
                })
            else:
                error_msg = mpesa_resp.get('ResponseDescription', 'Unknown M-Pesa error')
                Transfer.objects.create(
                    from_address=sender_address,
                    to_address="MPESA_WITHDRAWAL",
                    amount=Decimal(str(amount)),
                    tx_hash=tx_hash,
                    status='FAILED'
                )
                return Response({"result": False, "error": f"M-Pesa Error: {error_msg}"}, status=500)

        except Exception as e:
            return Response({"result": False, "error": f"B2C Exception: {str(e)}"}, status=500)

    return Response(serializer.errors, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def estimate_gas(request):
    return Response({"message": "Use frontend library (e.g., ethers.js) for real-time gas estimation."})