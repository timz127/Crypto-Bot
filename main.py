import logging

from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from binance.client import Client

from dotenv import dotenv_values

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

config = dotenv_values(".env")

TOKEN = config['TOKEN']
API_KEY = config['API_KEY']
SECRET_KEY = config['SECRET_KEY']
client = Client(API_KEY, SECRET_KEY, testnet=True)

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bal = client.get_account()['balances']
    await update.message.reply_html(bal[:10])

async def price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) < 1:
        await update.message.reply_text("enter symbol")
    else:
        sym = context.args[0]
        try:
            price = client.get_symbol_ticker(symbol=sym)['price']
            await update.message.reply_text(price)
        except Exception as e:
            await update.message.reply_text(str(e))

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) < 2:
        await update.message.reply_text("enter symbol and quantity")
    else:
        sym, quant = context.args[:2]
        try:
            order = client.order_market_buy(symbol=sym, quantity=quant)
            await update.message.reply_text(order)
        except Exception as e:
            await update.message.reply_text(str(e))

async def sell(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) < 2:
        await update.message.reply_text("enter symbol and quantity")
    else:
        sym, quant = context.args[:2]
        try:
            order = client.order_market_sell(symbol=sym, quantity=quant)
            await update.message.reply_text(order)
        except Exception as e:
            await update.message.reply_text(str(e))

def main() -> None:
    """Start the bot."""
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(CommandHandler("price", price))
    application.add_handler(CommandHandler("buy", buy))
    application.add_handler(CommandHandler("sell", sell))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()