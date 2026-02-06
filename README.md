# 🚀 M-Pesa to Crypto Bridge Backend (Django)

This repository hosts the server-side logic for the **NiToken ($NIT)** ecosystem, a stablecoin platform pegged to the Kenyan Shilling (KES). It serves as a secure bridge between traditional mobile money (**M-Pesa**) and decentralized finance (**Arbitrum Sepolia Blockchain**).

The system automates the conversion of fiat currency into crypto assets and vice versa, providing a seamless "Cash-in, Cash-out" experience for users.

---

## ⚡ Key Features

* **🟢 Automated Deposits (Fiat to Crypto)**
    Integrates with Safaricom's **STK Push**. When a user pays KES via M-Pesa, the system automatically validates the payment and **mints** an equivalent amount of `$NIT` tokens to their blockchain wallet.

* **🔴 Automated Withdrawals (Crypto to Fiat)**
    Handles **B2C (Business to Customer)** payouts. When a user requests a withdrawal, the system **burns** their `$NIT` tokens on-chain and instantly triggers an M-Pesa cash transfer to their phone number.

* **🔐 Non-Custodial Wallet Management**
    Generates standard Ethereum wallets (Private Keys & Mnemonics) using `eth_account`, allowing users full ownership of their assets.

* **💸 P2P Transfers**
    Enables users to send `$NIT` tokens to other wallets on the Arbitrum network with real-time balance updates.

* **⛓️ Web3 Integration**
    Uses `Web3.py` to interact directly with Smart Contracts on **Arbitrum Sepolia** (Layer 2) for fast and cheap transactions.

---

## 🛠️ Tech Stack

| Component | Technology |
| :--- | :--- |
| **Framework** | Django & Django REST Framework (DRF) |
| **Blockchain** | Arbitrum Sepolia (Ethereum Layer 2) |
| **Smart Contract** | ERC-20 (OpenZeppelin) |
| **Integration** | Web3.py |
| **Mobile Money** | Safaricom Daraja API (STK Push & B2C) |
| **Database** | SQLite (Dev) / PostgreSQL (Prod) |

---

## 🔄 How It Works

### 1. Deposit Flow
> **User requests 100 KES deposit** $\rightarrow$ App triggers M-Pesa STK Push $\rightarrow$ User enters PIN $\rightarrow$ Backend confirms payment $\rightarrow$ **Smart Contract Mints 100 $NIT**.

### 2. Transfer Flow
> **User sends 50 $NIT** $\rightarrow$ Backend signs transaction with user's private key $\rightarrow$ **Blockchain updates balances**.

### 3. Withdrawal Flow
> **User requests 50 KES withdrawal** $\rightarrow$ Backend burns 50 $NIT on-chain $\rightarrow$ **Triggers M-Pesa B2C payment to user**.