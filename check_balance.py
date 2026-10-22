"""
check_balance.py
================
Standalone script run by GitHub Actions every hour.
Checks USAT balance for all registered wallets and
sends a Telegram notification if tokens have arrived.

Usage:
    python check_balance.py

Environment variables required:
    TELEGRAM_BOT_TOKEN   — your bot token
    WALLET_ADDRESS       — Celo wallet address to monitor
    TELEGRAM_CHAT_ID     — your Telegram chat/user ID
"""

import os
import json
import requests
from web3 import Web3

# ─── CONFIG ────────────────────────────────────────────────────────────────────
BOT_TOKEN      = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID        = os.environ["TELEGRAM_CHAT_ID"]
WALLET_ADDRESS = os.environ["WALLET_ADDRESS"]

CELO_RPC      = "https://forno.celo.org"
USAT_CONTRACT = "0xD2ab3C9A02DBBAB236BfEC45D1d755DF4267F771"
CELOSCAN_URL  = "https://celoscan.io/address/"

ERC20_ABI = [
    {
        "inputs": [{"name": "owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    }
]


def get_usat_balance(address: str) -> float:
    w3 = Web3(Web3.HTTPProvider(CELO_RPC))
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(USAT_CONTRACT),
        abi=ERC20_ABI,
    )
    raw = contract.functions.balanceOf(
        Web3.to_checksum_address(address)
    ).call()
    return raw / 10**6


def send_telegram_message(text: str) -> None:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    resp = requests.post(url, json=payload)
    print(f"Telegram response: {resp.status_code} — {resp.text}")


def main():
    print(f"Checking USAT balance for: {WALLET_ADDRESS}")
    balance = get_usat_balance(WALLET_ADDRESS)
    short = f"{WALLET_ADDRESS[:6]}...{WALLET_ADDRESS[-4:]}"
    print(f"Balance: {balance} USAT")

    if balance > 0:
        message = (
            f"🎉 *USAT Tokens Received!*\n\n"
            f"💰 Balance: *{balance:.6f} USA₮*\n"
            f"👛 Wallet: `{short}`\n\n"
            f"[View on CeloScan]({CELOSCAN_URL}{WALLET_ADDRESS})"
        )
        send_telegram_message(message)
        print("✅ Notification sent!")
    else:
        print("⏳ No USAT yet. Will check again next hour.")


if __name__ == "__main__":
    main()
