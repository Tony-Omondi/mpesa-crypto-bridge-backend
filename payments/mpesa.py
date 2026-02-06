# payments/mpesa.py
import os
import base64
import requests
import re
import time 
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURATION ---
MPESA_CONSUMER_KEY = os.getenv('MPESA_CONSUMER_KEY')
MPESA_CONSUMER_SECRET = os.getenv('MPESA_CONSUMER_SECRET')
MPESA_PASSKEY = os.getenv('MPESA_PASSKEY')
MPESA_SHORTCODE = os.getenv('MPESA_SHORTCODE')
MPESA_CALLBACK_URL = os.getenv('MPESA_CALLBACK_URL')
MPESA_BASE_URL = os.getenv('MPESA_BASE_URL', 'https://sandbox.safaricom.co.ke').rstrip('/')

# B2C Config (For Withdrawals)
MPESA_INITIATOR_NAME = os.getenv('MPESA_INITIATOR_NAME')
MPESA_SECURITY_CREDENTIAL = os.getenv('MPESA_SECURITY_CREDENTIAL')

if not all([MPESA_CONSUMER_KEY, MPESA_CONSUMER_SECRET, MPESA_PASSKEY, MPESA_SHORTCODE, MPESA_CALLBACK_URL]):
    raise ValueError("Missing M-Pesa environment variables.")

# Token Caching
_cached_token = None
_token_expiry = 0

def format_phone_number(phone: str) -> str:
    """Ensures phone number is in 254 format"""
    phone = re.sub(r"[^\d]", "", phone.strip())
    if phone.startswith("254") and len(phone) == 12: return phone
    elif phone.startswith("0") and len(phone) == 10: return "254" + phone[1:]
    elif phone.startswith("7") and len(phone) == 9: return "254" + phone
    else: raise ValueError("Invalid phone number format")

def get_access_token() -> str:
    """Generates or retrieves cached OAuth token"""
    global _cached_token, _token_expiry
    current_time = time.time()
    
    if _cached_token and current_time < (_token_expiry - 60):
        return _cached_token

    auth_str = f"{MPESA_CONSUMER_KEY}:{MPESA_CONSUMER_SECRET}"
    encoded_auth = base64.b64encode(auth_str.encode()).decode()
    headers = {"Authorization": f"Basic {encoded_auth}"}
    url = f"{MPESA_BASE_URL}/oauth/v1/generate?grant_type=client_credentials"

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        _cached_token = data["access_token"]
        _token_expiry = current_time + int(data.get("expires_in", 3599))
        return _cached_token
    except Exception as e:
        raise Exception(f"Token Gen Error: {str(e)}")

def initiate_stk_push(phone_number: str, amount: int, order_id: str = None):
    """Triggers STK Push to User's Phone (Deposit)"""
    try:
        phone = format_phone_number(phone_number)
        token = get_access_token()
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        password = base64.b64encode(f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}".encode()).decode()
        account_ref = (str(order_id) if order_id else "ARIFARM")[:12]

        payload = {
            "BusinessShortCode": MPESA_SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(amount),
            "PartyA": phone,
            "PartyB": MPESA_SHORTCODE,
            "PhoneNumber": phone,
            "CallBackURL": MPESA_CALLBACK_URL,
            "AccountReference": account_ref,
            "TransactionDesc": "Deposit to NIT Wallet"
        }

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        url = f"{MPESA_BASE_URL}/mpesa/stkpush/v1/processrequest"
        
        response = requests.post(url, json=payload, headers=headers, timeout=20)
        return response.json()
    except Exception as e:
        print(f"STK Error: {e}")
        raise

def initiate_b2c_payment(phone_number: str, amount: int, remarks: str = "Withdrawal"):
    """Triggers Business Payment to User (Withdrawal)"""
    try:
        phone = format_phone_number(phone_number)
        token = get_access_token()
        
        payload = {
            "OriginatorConversationID": f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{phone}",
            "InitiatorName": MPESA_INITIATOR_NAME,
            "SecurityCredential": MPESA_SECURITY_CREDENTIAL,
            "CommandID": "BusinessPayment",
            "Amount": int(amount),
            "PartyA": MPESA_SHORTCODE,
            "PartyB": phone,
            "Remarks": remarks,
            "QueueTimeOutURL": f"{MPESA_BASE_URL}/b2c/timeout",
            "ResultURL": f"{MPESA_BASE_URL}/b2c/result",
            "Occassion": "Withdrawal"
        }

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        url = f"{MPESA_BASE_URL}/mpesa/b2c/v3/paymentrequest"
        
        print(f"[MPESA] Sending B2C: {amount} to {phone}")
        response = requests.post(url, json=payload, headers=headers, timeout=20)
        return response.json()
    except Exception as e:
        print(f"B2C Error: {e}")
        raise