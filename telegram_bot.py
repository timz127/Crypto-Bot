import logging
from telegram import Update, ForceReply
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from binance.client import Client
from dotenv import dotenv_values
import google.generativeai as genai
import traceback

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Load environment variables
config = dotenv_values(".env")
TOKEN = config['TELEGRAM_BOT_TOKEN']
API_KEY = config['BINANCE_API_KEY']
SECRET_KEY = config['BINANCE_API_SECRET']
GEMINI_KEY = config['GEMINI_API_KEY']

# Initialize clients
client = Client(API_KEY, SECRET_KEY, testnet=True)
genai.configure(api_key=GEMINI_KEY)
gemini_model = genai.GenerativeModel("gemini-1.5-flash")

INTENT_PROMPT = """Analyze the user's message and identify the intent:
- balance: Check wallet balance
- price: Check cryptocurrency price
- buy: Buy cryptocurrency
- sell: Sell cryptocurrency
- greeting: Hello/start
- unknown: Other

Respond ONLY with the intent name. Examples:
User: "Show my balance" → balance
User: "What's BTC worth?" → price
User: "Purchase 0.5 ETH" → buy
Message: "{message}"
Intent:"""

async def get_intent(message: str) -> str:
    response = gemini_model.generate_content(INTENT_PROMPT.format(message=message))
    return response.text.strip().lower()

async def extract_coins(message: str) -> list:
    """Extract cryptocurrency symbols from user messages"""
    prompt = f"""Analyze the message and extract ALL cryptocurrency symbols mentioned. 
    Convert common names to their symbols (e.g., Bitcoin→BTC, Ethereum→ETH, Dogecoin→DOGE, Shiba Inu→SHIB).
    Respond ONLY with space-separated uppercase symbols or 'NONE'.

    Examples:
    Message: "Check balance" → NONE
    Message: "Show my Bitcoin" → BTC
    Message: "How much Dogecoin and Ethereum?" → DOGE ETH
    Message: "What's my Shiba balance?" → SHIB
    Message: "I want to see USDT, BTC and ETH" → USDT BTC ETH
    Message: "Check my balance for Bitcoin, Ethereum and shiba" → BTC ETH SHIB
    Message: "{message}" → """
    
    try:
        response = gemini_model.generate_content(prompt)
        raw = response.text.strip().upper()
        return raw.split() if raw != 'NONE' else []
    except Exception as e:
        logger.error(f"Error extracting coins: {e}")
        return []

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_msg = update.message.text
    intent = await get_intent(user_msg)
    
    try:
        if intent == 'balance':
            requested_coins = await extract_coins(user_msg)
            response = ["💰 Your Balances:"]
            
            # Always show USDT
            try:
                usdt_balance = client.get_asset_balance(asset='USDT')
                free = float(usdt_balance['free'])
                locked = float(usdt_balance['locked'])
                response.append(f"💵 USDT: ${free + locked:.2f}")
            except Exception as e:
                response.append("❌ Failed to get USDT balance")
            
            # If specific coins were requested, show only those
            if requested_coins:
                for symbol in requested_coins:
                    if symbol == 'USDT':
                        continue  # Already shown
                    
                    try:
                        balance = client.get_asset_balance(asset=symbol)
                        free = float(balance['free'])
                        locked = float(balance['locked'])
                        total = free + locked
                        response.append(f"🔷 {symbol}: {total:.8f}")
                    except Exception as e:
                        response.append(f"❌ {symbol}: Not available or invalid symbol")
            
            await update.message.reply_text("\n".join(response))
            
        elif intent == 'buy':
            prompt = f"Extract coin and amount from: '{user_msg}'. Respond as 'COIN AMOUNT'"
            parts = gemini_model.generate_content(prompt).text.strip().split()
            coin, amount = parts[0].upper(), float(parts[1])
            order = client.order_market_buy(
                symbol=f"{coin}USDT",
                quantity=amount
            )
            await update.message.reply_text(f"✅ Bought {amount} {coin}\nOrder ID: {order['orderId']}")
            
        elif intent == 'sell':
            prompt = f"Extract coin and amount from: '{user_msg}'. Respond as 'COIN AMOUNT'"
            parts = gemini_model.generate_content(prompt).text.strip().split()
            coin, amount = parts[0].upper(), float(parts[1])
            order = client.order_market_sell(
                symbol=f"{coin}USDT",
                quantity=amount
            )
            await update.message.reply_text(f"✅ Sold {amount} {coin}\nOrder ID: {order['orderId']}")
        elif intent == 'price':
        # Extract the cryptocurrency symbol from user message
            prompt = f"""Extract the cryptocurrency symbol from this message.
            Convert common names to their symbol (Bitcoin→BTC, Ethereum→ETH, Dogecoin→DOGE, Shiba Inu→SHIB).
            Respond ONLY with the uppercase symbol. If multiple coins, pick the first one mentioned.
            Examples:
            "How much is Dogecoin?" → DOGE
            "What's the price of ETH?" → ETH
            "Tell me Bitcoin price" → BTC
            Message: "{user_msg}" → """
            
            try:
                # Get the coin symbol from Gemini
                coin_symbol = gemini_model.generate_content(prompt).text.strip().upper()
                
                if not coin_symbol:
                    await update.message.reply_text("❌ Please specify which cryptocurrency you want to check.")
                    return
                    
                # Get ticker price from Binance API
                ticker = client.get_symbol_ticker(symbol=f"{coin_symbol}USDT")
                price = float(ticker['price'])
                
                # Format the response with appropriate decimal places
                if price < 0.01:
                    formatted_price = f"${price:.8f}"
                elif price < 1:
                    formatted_price = f"${price:.6f}"
                elif price < 1000:
                    formatted_price = f"${price:.4f}"
                else:
                    formatted_price = f"${price:.2f}"
                    
                await update.message.reply_text(f"💲 Current {coin_symbol} price: {formatted_price}")
                
            except Exception as e:
                await update.message.reply_text(f"⚠️ Error getting price: {str(e)}\nMake sure you specified a valid cryptocurrency.")
            
        elif intent == 'greeting':
            await update.message.reply_text("👋 Hello there! I'm your friendly crypto trading assistant. "
            "What would you like to do today?\n\nI can help you with:\n- "
            "Check your balance (e.g., \"Show my BTC balance\")\n- Check crypto prices "
            "(e.g., \"What's the price of Ethereum?\")\n- Buy crypto (e.g., \"Buy 0.01 BTC\")\n- Sell crypto (e.g., \"Sell 100 DOGE\")")
            
        else:
        # For unknown intents, provide a friendly response with suggestions
            await update.message.reply_text("I'm not sure I understood that correctly. "
            "🤔\n\nHere's what I can help you with:\n\n💰 "
            "Check your balance\n- \"What's my ETH balance?\"\n- \"Show me my DOGE and BTC\"\n\n💲 Check crypto prices\n- \"How much is Bitcoin?\"\n- "
            "\"What's the current SHIB price?\"\n\n🛒 Trading\n- \"Buy 0.1 ETH\"\n- \"Sell 50 DOGE\"\n\nLet me know how I can assist you!")
    except Exception as e:
        # Log detailed error information to the terminal
        logger.error(f"Error in handle_message: {type(e).__name__}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Send a simplified error message to the user
        await update.message.reply_text(f"⚠️ Error: {str(e)}")

def main() -> None:
    application = Application.builder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CommandHandler("start", lambda u,c: u.message.reply_text("Welcome to Binance Testnet Bot!")))
    application.run_polling()

if __name__ == "__main__":
    main()