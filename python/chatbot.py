import os
import requests
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

BOT_JS_API = "http://localhost:3000"

genai.configure(api_key=GEMINI_API_KEY)

# Improved prompt engineering for better intent recognition
INTENT_PROMPT = """Analyze the user's message and identify the intent from these options:
- check_balance: Questions about balance, funds, or wallet amount
- airdrop: Requests for free SOL or tokens
- buy_token: Purchase requests using SOL
- sell_token: Selling tokens for SOL
- price_check: Price inquiries
- greeting: Hello, hi, hey
- unknown: Unrelated or unclear requests

Respond ONLY with the intent name. Example messages:
User: How much SOL do I have? -> check_balance
User: Send me 2 SOL -> airdrop
User: I want to buy 10 USD worth of BTC -> buy_token
User: What's the price of ETH? -> price_check
User: Hello there -> greeting

Message: '{user_message}'
Intent: """

async def get_intent(user_message: str) -> str:
    """Get classified intent using Gemini AI"""
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(INTENT_PROMPT.format(user_message=user_message))
    return response.text.strip().lower()

async def handle_message(update: Update, context: CallbackContext) -> None:
    user_message = update.message.text
    intent = await get_intent(user_message)

    try:
        # Handle different intents
        if intent == 'check_balance':
            response = requests.get(f"{BOT_JS_API}/balance")
            await update.message.reply_text(f"Wallet Balance: {response.json()['balance']} SOL")

        elif intent == 'airdrop':
            # Extract amount using more robust parsing
            try:
                amount = next((word for word in user_message.split() if word.isdigit()), 5)
                response = requests.post(f"{BOT_JS_API}/airdrop", json={"amount": int(amount)})
                data = response.json()
                await update.message.reply_text(f"Airdrop requested: {data['message']} (Tx: {data['tx']})")
            except Exception as e:
                await update.message.reply_text("Please specify an amount, e.g., 'Airdrop 5 SOL'")

        elif intent == 'buy_token':
            # Improved token/amount extraction
            try:
                parts = [p for p in user_message.split() if p.lower() not in ['buy', 'purchase']]
                token = parts[0].upper()
                amount = parts[1] if len(parts) > 1 else None
                if not amount:
                    raise ValueError
                response = requests.post(f"{BOT_JS_API}/buy", json={"tokenMint": token, "amount": float(amount)})
                await update.message.reply_text(response.json()['message'])
            except:
                await update.message.reply_text("Please specify a token and amount, e.g., 'Buy BTC 0.5'")

        elif intent == 'sell_token':
            # Similar improvements as buy_token
            ...

        elif intent == 'price_check':
            try:
                token = next((word for word in user_message.split() if len(word) >= 3), None)
                if token:
                    response = requests.get(f"{BOT_JS_API}/price/{token.upper()}")
                    await update.message.reply_text(f"Price of {token.upper()}: {response.json()['price']} SOL")
                else:
                    await update.message.reply_text("Please specify a token, e.g., 'Price of BTC'")
            except:
                await update.message.reply_text("Couldn't fetch price. Please check the token name.")

        elif intent == 'greeting':
            await update.message.reply_text("Hello! I'm your crypto trading assistant. How can I help you today? 🚀")

        else:
            await handle_unknown_intent(update)

    except requests.exceptions.RequestException:
        await update.message.reply_text("Our services are currently unavailable. Please try again later.")

async def handle_unknown_intent(update: Update):
    """Handle unrecognized requests with helpful suggestions"""
    suggestions = [
        "Check your wallet balance",
        "Get an SOL airdrop",
        "Buy/Sell tokens",
        "Check crypto prices"
    ]
    response = (
        "I'm not sure how to help with that. Here's what I can do:\n"
        + "\n".join(f"• {suggestion}" for suggestion in suggestions)
    )
    await update.message.reply_text(response)

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        "Welcome to CryptoBot! Here's what I can help with:\n"
        "- Check your wallet balance\n"
        "- Request SOL airdrops\n"
        "- Buy/Sell tokens\n"
        "- Check crypto prices\n\n"
        "Try saying something like 'How much SOL do I have?' or 'What's the price of BTC?'"
    )

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()