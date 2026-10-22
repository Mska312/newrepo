"""
USAT Celo Telegram Bot
======================
Guides Indian residents through:
1. Verifying eAadhaar on self.app
2. Getting their seed phrase
3. Submitting Celo address to USAT faucet
4. Auto-checking USAT token balance on Celo
"""

import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from web3 import Web3

# ─── CONFIG ────────────────────────────────────────────────────────────────────
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

CELO_RPC        = "https://forno.celo.org"
USAT_CONTRACT   = "0xD2ab3C9A02DBBAB236BfEC45D1d755DF4267F771"
FAUCET_URL      = "https://cloud.google.com/application/web3/faucet/celo/mainnet"
SELF_APP_URL    = "https://self.xyz"
CELOSCAN_URL    = "https://celoscan.io/address/"

ERC20_ABI = [
    {
        "inputs": [{"name": "owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    }
]

# In-memory store: { chat_id: { "address": "0x...", "claimed": bool } }
user_data_store: dict = {}

# ─── LOGGING ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ─── HELPERS ───────────────────────────────────────────────────────────────────
def get_usat_balance(wallet_address: str) -> float:
    """Fetch USAT token balance from Celo mainnet."""
    try:
        w3 = Web3(Web3.HTTPProvider(CELO_RPC))
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(USAT_CONTRACT),
            abi=ERC20_ABI,
        )
        raw = contract.functions.balanceOf(
            Web3.to_checksum_address(wallet_address)
        ).call()
        return raw / 10**6  # USAT has 6 decimals
    except Exception as e:
        logger.error(f"Balance check error: {e}")
        return -1.0


def is_valid_celo_address(address: str) -> bool:
    """Check if address is a valid Ethereum/Celo address."""
    return Web3.is_address(address)


# ─── HANDLERS ──────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Step 1 — Welcome and guide to self.app eAadhaar upload."""
    chat_id = update.effective_chat.id
    user_data_store[chat_id] = {"address": None, "claimed": False}

    keyboard = [
        [InlineKeyboardButton("📱 Open self.app", url=SELF_APP_URL)],
        [InlineKeyboardButton("✅ I've verified my Aadhaar", callback_data="verified")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        "👋 *Welcome to the USAT Celo Faucet Bot!*\n\n"
        "This bot helps Indian residents claim *USA₮ tokens* on the Celo network.\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📌 *STEP 1 — Verify your Aadhaar in self\\.app*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "1\\. Download *self\\.app* from Play Store / App Store\n"
        "2\\. Open the app → Tap *'Verify Identity'*\n"
        "3\\. Choose *'Upload eAadhaar PDF'* \\(India option\\)\n"
        "4\\. Upload your eAadhaar PDF from your phone\n"
        "5\\. Wait for verification to complete ✅\n\n"
        "Once done, tap the button below 👇"
    )

    await update.message.reply_text(
        text, parse_mode="MarkdownV2", reply_markup=reply_markup
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button presses."""
    query = update.callback_query
    await query.answer()

    if query.data == "verified":
        await show_seed_phrase_guide(query)
    elif query.data == "got_address":
        await query.edit_message_text(
            "📨 Please send me your Celo wallet address\\.\n\n"
            "Type it like this:\n`/address 0xYourCeloAddressHere`",
            parse_mode="MarkdownV2",
        )


async def show_seed_phrase_guide(query) -> None:
    """Step 2 — Show seed phrase instructions."""
    keyboard = [
        [InlineKeyboardButton("✅ I have my Celo address", callback_data="got_address")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        "✅ *Aadhaar Verified\\!*\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🔑 *STEP 2 — Find Your Seed Phrase*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "After verification, self\\.app gives you a *Wallet Seed Phrase*\\.\n\n"
        "📍 *Where to find it:*\n"
        "self\\.app → *Settings* → *Wallet* → *Recovery Phrase*\n\n"
        "📝 *Write it down on paper* \\(12 or 24 words\\)\n"
        "⚠️ *Never screenshot or share it with anyone*\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "💼 *STEP 3 — Import into a Wallet*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Import your seed phrase into *MetaMask* or *Valora*:\n\n"
        "1\\. Open MetaMask → *Import Wallet* → Enter your seed phrase\n"
        "2\\. Add *Celo Network* manually:\n"
        "   • Network Name: `Celo Mainnet`\n"
        "   • RPC URL: `https://forno.celo.org`\n"
        "   • Chain ID: `42220`\n"
        "   • Symbol: `CELO`\n"
        "3\\. *Copy your wallet address* \\(starts with 0x\\.\\.\\.\\)\n\n"
        "Tap below when you have your Celo address 👇"
    )

    await query.edit_message_text(
        text, parse_mode="MarkdownV2", reply_markup=reply_markup
    )


async def set_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Step 3 — Accept Celo wallet address from user."""
    chat_id = update.effective_chat.id

    if not context.args:
        await update.message.reply_text(
            "⚠️ Please provide your Celo address\\.\n\n"
            "Usage: `/address 0xYourCeloAddressHere`",
            parse_mode="MarkdownV2",
        )
        return

    address = context.args[0].strip()

    if not is_valid_celo_address(address):
        await update.message.reply_text(
            "❌ *Invalid address\\!*\n\n"
            "Please send a valid Celo wallet address starting with `0x`\\.",
            parse_mode="MarkdownV2",
        )
        return

    # Save address
    if chat_id not in user_data_store:
        user_data_store[chat_id] = {}
    user_data_store[chat_id]["address"] = address
    user_data_store[chat_id]["claimed"] = False

    celoscan_link = f"{CELOSCAN_URL}{address}"
    faucet_link   = FAUCET_URL

    keyboard = [
        [InlineKeyboardButton("🚰 Go to USAT Faucet", url=faucet_link)],
        [InlineKeyboardButton("🔍 View on CeloScan", url=celoscan_link)],
        [InlineKeyboardButton("✅ I've scanned the QR", callback_data="check_balance")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    short_addr = f"{address[:6]}...{address[-4:]}"

    text = (
        f"✅ *Address saved\\!* `{short_addr}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🚰 *STEP 4 — Claim from USAT Faucet*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "1\\. Tap *'Go to USAT Faucet'* below\n"
        "2\\. Click *'Connect Wallet'* on the page\n"
        "3\\. Connect your MetaMask/Valora wallet\n"
        "4\\. A *QR code* will appear on the faucet page\n"
        "5\\. Open *self\\.app* → Scan that QR code\n"
        "6\\. self\\.app sends your ZK proof → faucet verified ✅\n\n"
        "After scanning, tap *'I've scanned the QR'* 👇"
    )

    await update.message.reply_text(
        text, parse_mode="MarkdownV2", reply_markup=reply_markup
    )


async def check_balance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Step 5 — Check USAT balance after QR scan."""
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id

    user = user_data_store.get(chat_id, {})
    address = user.get("address")

    if not address:
        await query.edit_message_text(
            "⚠️ No address found\\. Please start again with /start",
            parse_mode="MarkdownV2",
        )
        return

    await query.edit_message_text("⏳ *Checking your USAT balance on Celo\\.\\.\\.*", parse_mode="MarkdownV2")

    balance = get_usat_balance(address)
    short_addr = f"{address[:6]}...{address[-4:]}"

    if balance < 0:
        text = (
            "❌ *Could not connect to Celo network\\.*\n\n"
            "Please try again with /balance"
        )
    elif balance == 0:
        text = (
            f"⏳ *No USAT received yet* for `{short_addr}`\n\n"
            "The faucet may take a few minutes\\.\n"
            "Use /balance to check again anytime\\.\n\n"
            "💡 Make sure you completed the QR scan in self\\.app\\."
        )
    else:
        text = (
            f"🎉 *USAT Received\\!*\n\n"
            f"💰 Balance: *{balance:.6f} USA₮*\n"
            f"👛 Wallet: `{short_addr}`\n\n"
            f"[View on CeloScan]({CELOSCAN_URL}{address})"
        )

    keyboard = [[InlineKeyboardButton("🔄 Check Again", callback_data="check_balance")]]
    await query.edit_message_text(
        text,
        parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup(keyboard),
        disable_web_page_preview=True,
    )


async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/balance command — manual balance check."""
    chat_id = update.effective_chat.id
    user = user_data_store.get(chat_id, {})
    address = user.get("address")

    # Allow custom address: /balance 0x...
    if context.args:
        address = context.args[0].strip()

    if not address or not is_valid_celo_address(address):
        await update.message.reply_text(
            "⚠️ No address found\\.\n\n"
            "Set one first: `/address 0xYourCeloAddress`\n"
            "Or check directly: `/balance 0xYourCeloAddress`",
            parse_mode="MarkdownV2",
        )
        return

    await update.message.reply_text("⏳ Checking USAT balance\\.\\.\\.", parse_mode="MarkdownV2")
    balance = get_usat_balance(address)
    short_addr = f"{address[:6]}...{address[-4:]}"

    if balance < 0:
        text = "❌ Could not connect to Celo network\\. Try again later\\."
    elif balance == 0:
        text = f"⏳ Balance: *0 USA₮* for `{short_addr}`\n\nNot received yet\\. Try again in a few minutes\\."
    else:
        text = (
            f"✅ *USAT Balance*\n\n"
            f"💰 *{balance:.6f} USA₮*\n"
            f"👛 `{short_addr}`\n\n"
            f"[View on CeloScan]({CELOSCAN_URL}{address})"
        )

    await update.message.reply_text(
        text, parse_mode="MarkdownV2", disable_web_page_preview=True
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/help command."""
    text = (
        "🤖 *USAT Celo Bot — Commands*\n\n"
        "/start — Begin the full process\n"
        "/address `0x\\.\\.\\.` — Set your Celo wallet address\n"
        "/balance — Check your USAT balance\n"
        "/balance `0x\\.\\.\\.` — Check any wallet's USAT balance\n"
        "/help — Show this message\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🔗 *Useful Links*\n"
        f"• [self\\.app]({SELF_APP_URL})\n"
        f"• [USAT Faucet]({FAUCET_URL})\n"
        f"• [CeloScan Explorer](https://celoscan.io)\n"
    )
    await update.message.reply_text(text, parse_mode="MarkdownV2", disable_web_page_preview=True)


# ─── MAIN ──────────────────────────────────────────────────────────────────────

def main() -> None:
    """Start the bot."""
    app = Application.builder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start",   start))
    app.add_handler(CommandHandler("address", set_address))
    app.add_handler(CommandHandler("balance", balance_command))
    app.add_handler(CommandHandler("help",    help_command))

    # Inline buttons
    app.add_handler(CallbackQueryHandler(button_callback,          pattern="^(verified|got_address)$"))
    app.add_handler(CallbackQueryHandler(check_balance_callback,   pattern="^check_balance$"))

    logger.info("🤖 Bot started. Polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
