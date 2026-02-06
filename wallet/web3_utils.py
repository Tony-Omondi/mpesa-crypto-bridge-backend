# wallet/web3_utils.py
import json
import os
from web3 import Web3
from django.conf import settings
from decouple import config

# 1. Connection Setup
RPC_URL = config('WEB3_PROVIDER_URL')
w3 = Web3(Web3.HTTPProvider(RPC_URL))

# 2. Owner Setup (Admin Wallet)
OWNER_PRIVATE_KEY = config('OWNER_PRIVATE_KEY', default=None)
SENDER_ADDRESS = None
if OWNER_PRIVATE_KEY:
    try:
        SENDER_ADDRESS = w3.eth.account.from_key(OWNER_PRIVATE_KEY).address
    except Exception as e:
        print(f"❌ Owner Key Error: {e}")

# 3. Contract Setup
NITOKEN_ADDRESS = config('NITOKEN_ADDRESS', default=None)
ABI_PATH = os.path.join(settings.BASE_DIR, 'wallet', 'abi.json')

NITOKEN_ABI = []
if os.path.exists(ABI_PATH):
    try:
        with open(ABI_PATH, 'r') as f:
            data = json.load(f)
            NITOKEN_ABI = data if isinstance(data, list) else data.get('abi', [])
    except Exception as e:
        print(f"❌ ABI Error: {e}")

# Global Contract Instance
contract = None
if NITOKEN_ADDRESS and NITOKEN_ABI and w3.is_connected():
    try:
        checksum_address = Web3.to_checksum_address(NITOKEN_ADDRESS)
        contract = w3.eth.contract(address=checksum_address, abi=NITOKEN_ABI)
    except Exception as e:
        print(f"❌ Contract Init Error: {e}")

# --- FUNCTIONS ---

def get_wallet_balance(wallet_address):
    """Fetches real-time $NIT and ETH balances."""
    if not w3.is_connected() or not contract:
        return None, None
    try:
        checksum_addr = Web3.to_checksum_address(wallet_address)
        
        # Get $NIT
        nit_raw = contract.functions.balanceOf(checksum_addr).call()
        nit_bal = w3.from_wei(nit_raw, 'ether')

        # Get ETH (Gas)
        eth_raw = w3.eth.get_balance(checksum_addr)
        eth_bal = w3.from_wei(eth_raw, 'ether')

        return float(nit_bal), float(eth_bal)
    except Exception as e:
        print(f"❌ Balance Fetch Error: {e}")
        return 0.0, 0.0

def mint_token_to_user(user_address, amount_kes):
    """Mints new tokens to a user (Called by Payments App)."""
    if not w3.is_connected() or not contract or not SENDER_ADDRESS:
        return None
    try:
        user_checksum = Web3.to_checksum_address(user_address)
        # Fix decimals
        amount_wei = w3.to_wei(amount_kes, 'ether')

        mint_func = getattr(contract.functions, 'mintFromKES', contract.functions.mint)
        
        tx = mint_func(user_checksum, amount_wei).build_transaction({
            'from': SENDER_ADDRESS,
            'nonce': w3.eth.get_transaction_count(SENDER_ADDRESS),
            'gas': 150000,
            'maxFeePerGas': w3.eth.gas_price * 2,
            'maxPriorityFeePerGas': w3.to_wei('1', 'gwei'),
            'chainId': w3.eth.chain_id,
            'type': '0x2'
        })

        signed_tx = w3.eth.account.sign_transaction(tx, OWNER_PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        return tx_hash.hex()
    except Exception as e:
        print(f"❌ Minting Error: {e}")
        return None

def transfer_token(sender_private_key, to_address, amount_nit):
    """Transfers $NIT from User A to User B."""
    if not w3.is_connected() or not contract:
        return {"error": "Blockchain disconnected"}

    try:
        sender_account = w3.eth.account.from_key(sender_private_key)
        sender_address = sender_account.address
        
        to_checksum = Web3.to_checksum_address(to_address)
        amount_wei = w3.to_wei(amount_nit, 'ether')

        # Balance Checks
        balance = contract.functions.balanceOf(sender_address).call()
        if balance < amount_wei:
            return {"error": "Insufficient $NIT Balance"}

        eth_balance = w3.eth.get_balance(sender_address)
        if eth_balance < w3.to_wei(0.0001, 'ether'):
            return {"error": "Insufficient ETH for Gas"}

        tx = contract.functions.transfer(to_checksum, amount_wei).build_transaction({
            'from': sender_address,
            'nonce': w3.eth.get_transaction_count(sender_address),
            'gas': 100000,
            'maxFeePerGas': w3.eth.gas_price * 2,
            'maxPriorityFeePerGas': w3.to_wei('1', 'gwei'),
            'chainId': w3.eth.chain_id,
            'type': '0x2'
        })

        signed_tx = w3.eth.account.sign_transaction(tx, sender_private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        print(f"✅ Transfer Success! Hash: {tx_hash.hex()}")
        return {"tx_hash": tx_hash.hex()}

    except Exception as e:
        print(f"❌ Transfer Error: {e}")
        return {"error": str(e)}

def return_token_to_admin(user_private_key, amount_nit):
    """
    Transfers $NIT from User back to Admin (For Withdrawals).
    """
    if not SENDER_ADDRESS:
        return {"error": "Admin address not configured"}
        
    # We simply transfer to the SENDER_ADDRESS (Admin)
    return transfer_token(user_private_key, SENDER_ADDRESS, amount_nit)