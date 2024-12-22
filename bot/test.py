import logging
import requests
import os
import json
from dotenv import load_dotenv
from telegram import Update, ForceReply
from telegram.ext import Application, CommandHandler, ContextTypes

# Load environment variables from the specific .env file
load_dotenv("/shared/envs/.env")

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
JACKETT_API_KEY = os.getenv("JACKETT_API_KEY")
JACKETT_BASE_URL = os.getenv("JACKETT_API_URL")
CONFIG_FILE_PATH = "/shared/envs/config.json"  # Update this to the correct path if needed

# Validate and fix JACKETT_BASE_URL
if not JACKETT_BASE_URL.startswith(("http://", "https://")):
    JACKETT_BASE_URL = f"http://{JACKETT_BASE_URL}:9117"

if not all([TELEGRAM_BOT_TOKEN, JACKETT_API_KEY, JACKETT_BASE_URL]):
    raise EnvironmentError("One or more required environment variables are missing.")

# # Define the Jackett API URL and API key
# JACKETT_API_URL = "http://127.0.0.1:9117/api/v2.0/indexers/all/results/torznab/api"
# JACKETT_API_KEY = "2noh0zf99aga6te0b2uf4a2boj8jeeod"

# Command handler for /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}! Welcome to the Jackett Search Bot. Use /search <query> to search.",
        reply_markup=ForceReply(selective=True),
    )

# async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     """
#     Handles the /start command. Sends a welcome message.
#     """
#     try:
#         user = update.effective_user
#         user_name = escape(user.full_name)
#         message = (
#             f"Hi <b>{user_name}</b>! Welcome to mitSu's Jackett Search Bot.\n\n"
#             "Use /search <query> to search for content."
#         )
#         await update.message.reply_html(message, reply_markup=ForceReply(selective=True))
#     except Exception as e:
#         # Log error and inform the user
#         print(f"Error in /start: {e}")
#         await update.message.reply_text("An error occurred while processing your request. Please try again later.")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Stopping the bot...")
    context.application.stop()

# async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     """
#     Handles the /stop command. Sends a goodbye message.
#     """
#     try:
#         user = update.effective_user
#         user_name = escape(user.full_name)
#         await update.message.reply_text(f"Goodbye, {user_name}!")
#     except Exception as e:
#         # Log error and inform the user
#         print(f"Error in /stop: {e}")
#         await update.message.reply_text("An error occurred while processing your request. Please try again later.")

# Command handler for /info
async def info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Check if the config.json file exists
        if not os.path.exists(CONFIG_FILE_PATH):
            await update.message.reply_text("The config.json file does not exist.")
            return

        # Read and send the contents of the config.json file
        with open(CONFIG_FILE_PATH, "r") as file:
            config_data = json.load(file)

        # Send the contents of the file to the user
        formatted_data = json.dumps(config_data, indent=4)
        await update.message.reply_text(
            f"📄 *Config File Contents:*\n```\n{formatted_data}\n```",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error reading config file: {e}")
        await update.message.reply_text("An error occurred while fetching the config file contents.")


# async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     """
#     Handles the /search command. Queries the Jackett API for search results.
#     """
#     if not context.args:
#         await update.message.reply_text("Usage: /search <query>")
#         return

#     query = " ".join(context.args)
#     params = {
#         "apikey": JACKETT_API_KEY,
#         "t": "search",
#         "q": query
#     }

#     try:
#         response = requests.get(JACKETT_API_URL, params=params, timeout=10)
#         response.raise_for_status()

#         # Check response content
#         if response.text.strip():
#             await update.message.reply_text(f"Search results for '{query}':\n\n{response.text}")
#         else:
#             await update.message.reply_text(f"No results found for '{query}'.")
#     except ConnectionError:
#         await update.message.reply_text("Unable to connect to the Jackett server. Please try again later.")
#     except Timeout:
#         await update.message.reply_text("The Jackett server took too long to respond. Please try again later.")
#     except requests.HTTPError as e:
#         await update.message.reply_text(f"Jackett server returned an error: {e}")
#     except Exception as e:
#         # Log unexpected errors and notify the user
#         print(f"Unexpected error in /search: {e}")
#         await update.message.reply_text("An unexpected error occurred. Please try again later.")

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /search <query>")
        return

    query = " ".join(context.args)
    await update.message.reply_text(f"Searching for '{query}'...")

    try:
        # Request parameters for Jackett API
        params = {"apikey": JACKETT_API_KEY, "Query": query}
        response = requests.get(JACKETT_BASE_URL, params=params)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Parse and respond with results
        results = response.json().get("Results", [])
        if not results:
            await update.message.reply_text("No results found.")
            return

        for result in results[:5]:
            title = result.get("Title", "No title")
            seeders = result.get("Seeders", 0)
            leechers = result.get("Peers", 0) - seeders
            link = result.get("Link", "No link")
            await update.message.reply_text(
                f"🎬 *Title*: {title}\n"
                f"🌱 *Seeders*: {seeders} | 🐛 *Leechers*: {leechers}\n"
                f"🔗 [Download Link]({link})",
                parse_mode="Markdown"
            )
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching results: {e}")
        await update.message.reply_text("An error occurred while fetching results.")


def main():
    """
    Main function to start the Telegram bot.
    """
    # # Replace 'your-bot-token' with your Telegram bot token
    # bot_token = "TELEGRAM_BOT_TOKEN"

    # Create the application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("search", search))
    application.add_handler(CommandHandler("info", info))

    # Start the bot
    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
