# wallet/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from eth_account import Account
from web3 import Web3
from decimal import Decimal  # <-- Added this for database saving

from .serializers import TransferSerializer, WithdrawalSerializer

# Import Logic
from .web3_utils import get_wallet_balance, transfer_token, return_token_to_admin, w3
# Import B2C Logic from your Payments App
from payments.mpesa import initiate_b2c_payment
# Import the Transfer model so we can save to History <-- Added this
from payments.models import Transfer 

Account.enable_unaudited_hdwallet_features()

@api_view(['GET'])
@permission_classes([AllowAny])
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
@permission_classes([AllowAny])
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
@permission_classes([AllowAny])
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
@permission_classes([AllowAny])
def transfer_funds(request):
    serializer = TransferSerializer(data=request.data)
    if serializer.is_valid():
        to_addr = serializer.validated_data['to_address']
        amount = serializer.validated_data['amount']
        p_key = serializer.validated_data['privateKey']

        # Derive the sender's address from the private key
        sender_account = Account.from_key(p_key)
        sender_address = sender_account.address

        result = transfer_token(p_key, to_addr, float(amount))
        
        if "error" in result:
             return Response({"result": False, "error": result["error"]}, status=400)
        
        # 🛑 NEW: SAVE TO DATABASE SO HISTORY TAB CAN SEE IT
        Transfer.objects.create(
            from_address=sender_address,
            to_address=to_addr,
            amount=Decimal(str(amount)),
            tx_hash=result["tx_hash"],
            status='COMPLETED'
        )
        
        return Response({"result": True, "tx_hash": result["tx_hash"], "message": "Transfer Successful"})
    
    return Response(serializer.errors, status=400)

@api_view(['POST'])
@permission_classes([AllowAny])
def withdraw_to_mpesa(request):
    """
    Endpoint: /api/wallet/withdraw/
    1. Burns Tokens (User -> Admin)
    2. Sends M-Pesa (Admin -> User)
    """
    serializer = WithdrawalSerializer(data=request.data)
    if serializer.is_valid():
        p_key = serializer.validated_data['privateKey']
        amount = serializer.validated_data['amount']
        phone = serializer.validated_data['phone_number']

        # Derive the sender's address from the private key
        sender_account = Account.from_key(p_key)
        sender_address = sender_account.address

        # 1. Blockchain Transfer (Burn)
        crypto_result = return_token_to_admin(p_key, float(amount))
        if "error" in crypto_result:
            return Response({"result": False, "error": crypto_result["error"]}, status=400)

        # 2. M-Pesa B2C Payout
        try:
            mpesa_resp = initiate_b2c_payment(phone, int(amount))
            if mpesa_resp.get("ResponseCode") == "0":
                
                # 🛑 NEW: SAVE TO DATABASE SO HISTORY TAB CAN SEE IT
                Transfer.objects.create(
                    from_address=sender_address,
                    to_address="MPESA_WITHDRAWAL", 
                    amount=Decimal(str(amount)),
                    tx_hash=crypto_result['tx_hash'],
                    status='COMPLETED'
                )

                return Response({
                    "result": True, 
                    "message": "Withdrawal Successful", 
                    "tx_hash": crypto_result['tx_hash']
                })
            else:
                return Response({
                    "result": False, 
                    "error": f"M-Pesa Error: {mpesa_resp.get('ResponseDescription')}"
                }, status=500)
        except Exception as e:
            return Response({"result": False, "error": f"B2C Exception: {str(e)}"}, status=500)

    return Response(serializer.errors, status=400)

@api_view(['POST'])
@permission_classes([AllowAny])
def estimate_gas(request):
    return Response({"message": "Use frontend library (e.g., ethers.js) for real-time gas estimation."})