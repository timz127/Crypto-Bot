import os
import google.generativeai as genai
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackContext,
)
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get API keys from environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)

def split_text(text, max_length=4096):
    """Splits a message into chunks of max_length characters."""
    return [text[i : i + max_length] for i in range(0, len(text), max_length)]

# Function to handle user messages
async def handle_message(update: Update, context: CallbackContext) -> None:
    user_message = update.message.text

    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(user_message)

        if response and response.text:
            bot_reply = response.text.strip()
            for chunk in split_text(bot_reply):
                await update.message.reply_text(chunk)
        else:
            await update.message.reply_text("Sorry, I couldn't generate a response.")

    except Exception as e:
        await update.message.reply_text("Error: " + str(e))

# Start command
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Hello! I'm your AI chatbot using Gemini. Ask me anything!")

# Main function
def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the bot
    app.run_polling()

if __name__ == "__main__":
    main()
