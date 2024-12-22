import os
import json
import logging
import requests
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,  # Import MessageHandler
    filters          # Import filters for filtering messages
)

# Load environment variables from .env file
load_dotenv("/shared/envs/.env")

# Configure logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
JACKETT_API_KEY = os.getenv("JACKETT_API_KEY")
DOCKER_JACKETT_URL = os.getenv("JACKETT_API_URL")
LOCAL_JACKETT_URL = "https://mitsuapp-khv748is.b4a.run"
CONFIG_FILE_PATH = "/shared/envs/config.json"

if not DOCKER_JACKETT_URL.startswith(("http://", "https://")):
    DOCKER_JACKETT_URL = f"http://0.0.0.0:9117"

if not all([TELEGRAM_BOT_TOKEN, JACKETT_API_KEY, DOCKER_JACKETT_URL]):
    raise EnvironmentError("One or more required environment variables are missing.")

# Store the current Jackett URL (default to Docker Jackett)
CURRENT_JACKETT_URL = DOCKER_JACKETT_URL

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    buttons = [
        [
            InlineKeyboardButton("Switch to Local Source", callback_data="switch_local"),
            InlineKeyboardButton("Switch to Docker Source", callback_data="switch_docker"),
        ],
        [
            InlineKeyboardButton("Search", callback_data="set_type:search"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(buttons)

    await update.message.reply_text(
        "Welcome to the Jackett Search Bot!\nUse the buttons below to choose the search source or start searching.",
        reply_markup=reply_markup,
    )

# Handle switching the source between local and docker
async def switch_source(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global CURRENT_JACKETT_URL
    query = update.callback_query
    await query.answer()

    if query.data == "switch_local":
        CURRENT_JACKETT_URL = LOCAL_JACKETT_URL
        await query.edit_message_text("Switched to the local Jackett instance. Use /search to search.")
    elif query.data == "switch_docker":
        CURRENT_JACKETT_URL = DOCKER_JACKETT_URL
        await query.edit_message_text("Switched to the Docker Jackett instance. Use the buttons to search.")

# # /search command for plain search (local Jackett)
# async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     query = " ".join(context.args)
#     if not query:
#         await update.message.reply_text("Usage: /search <query>")
#         return

#     # If the current URL is the local Jackett instance, proceed with plain search
#     if CURRENT_JACKETT_URL == LOCAL_JACKETT_URL:
#         api_url = f"{CURRENT_JACKETT_URL}/UI/Api/Search"
#         params = {
#             "apikey": JACKETT_API_KEY,
#             "q": query,
#             "category": "1000",  # Example category (can be updated)
#         }

#         try:
#             response = requests.get(api_url, params=params)
#             response.raise_for_status()
#             results = response.json().get("Results", [])

#             if not results:
#                 await update.message.reply_text("No results found.")
#                 return

#             # Send results to the user
#             result_text = "\n\n".join(
#                 [f"🎬 {result['Title']}\n🔗 {result['Link']}" for result in results[:5]]
#             )
#             await update.message.reply_text(f"Search results:\n\n{result_text}")
#         except requests.RequestException as e:
#             await update.message.reply_text(f"Error fetching results: {e}")
#     else:
#         await update.message.reply_text(
#             "You are using the Docker Jackett instance. Please use the buttons for search."
#         )

# # /search command for plain search (local Jackett) gives Url
# async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     query = " ".join(context.args)
#     if not query:
#         await update.message.reply_text("Usage: /search <query>")
#         return

#     # If the current URL is the local Jackett instance, proceed with plain search
#     if CURRENT_JACKETT_URL == LOCAL_JACKETT_URL:
#         # Construct the correct search URL
#         search_url = f"{LOCAL_JACKETT_URL}/UI/Dashboard#search={query}&filter=all"

#         # Send the URL to the user
#         await update.message.reply_text(
#             f"Click here to view the search results for '{query}':\n<a href='{search_url}'>Results</a>"
#         )
#     else:
#         await update.message.reply_text(
#             "You are using the Docker Jackett instance. Please use the buttons for search."
#         )

# /search command for plain search (local Jackett)
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("Usage: /search <query>")
        return

    # If the current URL is the local Jackett instance, proceed with the API search
    if CURRENT_JACKETT_URL == LOCAL_JACKETT_URL:
        # Construct the correct search URL
        api_url = f"{LOCAL_JACKETT_URL}/UI/Dashboard#search={query}&filter=all"

        # api_url = f"{CURRENT_JACKETT_URL}/UI/Api/Search"
        # params = {
        #     # "apikey": JACKETT_API_KEY,
        #     "q": query,
        #     # "category": "1000",  # Example category (can be updated)
        # }

        try:
            response = requests.get(api_url)
            response.raise_for_status()
            results = response.json().get("Results", [])

            if not results:
                await update.message.reply_text("No results found.")
                return

            # Limit to 10 results
            limited_results = results[:10]

            # Send results to the user
            result_text = "\n\n".join(
                [f"🎬 {result['Title']}\n🔗 {result['Link']}" for result in limited_results]
            )
            await update.message.reply_text(f"Search results:\n\n{result_text}")
        except requests.RequestException as e:
            await update.message.reply_text(f"Error fetching results: {e}")
    else:
        await update.message.reply_text(
            "You are using the Docker Jackett instance. Please use the buttons for search."
        )

# /search command for Docker Jackett
async def docker_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    buttons = [
        [InlineKeyboardButton("Query (q)", callback_data="set_param:q")],
        [InlineKeyboardButton("Year", callback_data="set_param:year")],
        [InlineKeyboardButton("Genre", callback_data="set_param:genre")],
        [InlineKeyboardButton("Done", callback_data="execute_search")],
    ]
    reply_markup = InlineKeyboardMarkup(buttons)

    await query.edit_message_text(
        text="Add parameters for your search or press 'Done' to execute:",
        reply_markup=reply_markup,
    )

# Handle setting a parameter (for Docker Jackett search)
async def handle_parameter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    param_key = query.data.split(":")[1]

    # Ask user to provide the value for the parameter
    await query.edit_message_text(text=f"Please enter a value for '{param_key}':")
    context.user_data["current_param"] = param_key


# Execute the Docker search
async def execute_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if user_id not in context.user_data or "current_param" not in context.user_data:
        await query.edit_message_text(text="No parameter selected. Start over.")
        return

    param_key = context.user_data.pop("current_param")
    param_value = update.message.text

    # Build the API request
    api_url = f"{CURRENT_JACKETT_URL}/api"
    params = {
        "apikey": JACKETT_API_KEY,
        "t": "search",
        "q": param_value,
    }

    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()
        results = response.json().get("Results", [])

        if not results:
            await query.edit_message_text(text="No results found.")
            return

        result_text = "\n\n".join(
            [f"🎬 {result['Title']}\n🔗 {result['Link']}" for result in results[:5]]
        )
        await query.edit_message_text(text=f"Search results:\n\n{result_text}")
    except requests.RequestException as e:
        await query.edit_message_text(text=f"Error fetching results: {e}")

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
        
# Command handler for /info
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Stopping the bot...")
    context.application.stop()

# Main function to set up the bot
def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("info", info))
    application.add_handler(CommandHandler("search", search))
    application.add_handler(CallbackQueryHandler(switch_source, pattern="switch_.*"))
    application.add_handler(CallbackQueryHandler(docker_search, pattern="set_type:.*"))
    application.add_handler(CallbackQueryHandler(handle_parameter, pattern="set_param:.*"))
    application.add_handler(CallbackQueryHandler(execute_search, pattern="execute_search"))
    # application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))

    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
