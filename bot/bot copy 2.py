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
JACKETT_BASE_URL = os.getenv("JACKETT_API_URL")
CONFIG_FILE_PATH = "/shared/envs/config.json"

if not JACKETT_BASE_URL.startswith(("http://", "https://")):
    JACKETT_BASE_URL = f"http://0.0.0.0:9117"

if not all([TELEGRAM_BOT_TOKEN, JACKETT_API_KEY, JACKETT_BASE_URL]):
    raise EnvironmentError("One or more required environment variables are missing.")

# Global state dictionary to track user queries
user_queries = {}

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    buttons = [
        [
            InlineKeyboardButton("Search", callback_data="set_type:search"),
            InlineKeyboardButton("TV Search", callback_data="set_type:tvsearch"),
        ],
        [
            InlineKeyboardButton("Movie", callback_data="set_type:movie"),
            InlineKeyboardButton("Music", callback_data="set_type:music"),
        ],
        [InlineKeyboardButton("Book", callback_data="set_type:book")],
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(
        "Welcome to the Jackett Search Bot!\nChoose a search type to begin:",
        reply_markup=reply_markup,
    )

# Handle setting the search type
async def handle_search_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    search_type = query.data.split(":")[1]

    # Initialize user query state
    user_queries[user_id] = {"t": search_type, "params": {}}

    if search_type == "search":
        # Plain text for "Search" type
        await query.edit_message_text(
            text="Search type set to 'Search'. Please send your query as plain text."
        )
    else:
        # Show parameter menu for other types
        await query.edit_message_text(
            text=f"Search type set to '{search_type}'. Add parameters to refine your search.",
        )
        await show_parameter_menu(query)

# Show parameter menu
async def show_parameter_menu(query) -> None:
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

# Handle setting a parameter
async def handle_parameter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if user_id not in user_queries:
        await query.edit_message_text(text="No search type selected. Start with /start.")
        return

    param_key = query.data.split(":")[1]

    # Ask user to provide the value for the parameter
    await query.edit_message_text(text=f"Please enter a value for '{param_key}':")
    context.user_data["current_param"] = param_key

# Handle user text input for parameter value
async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if "current_param" not in context.user_data:
        if user_id in user_queries and user_queries[user_id]["t"] == "search":
            # Directly set the query parameter for "Search"
            user_queries[user_id]["params"]["q"] = update.message.text
            await execute_search(update, context)
        else:
            await update.message.reply_text("No parameter selected. Use the buttons to add parameters.")
        return

    param_key = context.user_data.pop("current_param")
    param_value = update.message.text

    # Save the parameter value in the user's query state
    user_queries[user_id]["params"][param_key] = param_value

    # Acknowledge and show the parameter menu again
    await update.message.reply_text(
        f"Parameter '{param_key}' set to '{param_value}'.",
    )
    query_message = await context.bot.send_message(
        chat_id=update.message.chat_id, text="Updating parameters..."
    )
    await show_parameter_menu(query_message)

# Execute the search
async def execute_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id if update.message else update.callback_query.from_user.id
    query = update.callback_query if update.callback_query else None

    if user_id not in user_queries or not user_queries[user_id]["params"]:
        if query:
            await query.edit_message_text(text="No parameters set. Please add parameters before searching.")
        else:
            await update.message.reply_text("No parameters set. Please add parameters before searching.")
        return

    # Generate API URL with user-specified parameters
    params = user_queries[user_id]["params"]
    query_type = user_queries[user_id]["t"]
    api_url = f"{JACKETT_BASE_URL}/api"
    params["apikey"] = JACKETT_API_KEY
    params["t"] = query_type

    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()
        results = response.json().get("Results", [])

        if not results:
            if query:
                await query.edit_message_text(text="No results found.")
            else:
                await update.message.reply_text("No results found.")
            return

        # Send results to the user
        result_text = "\n\n".join(
            [f"🎬 {result['Title']}\n🔗 {result['Link']}" for result in results[:5]]
        )
        if query:
            await query.edit_message_text(text=f"Search results:\n\n{result_text}")
        else:
            await update.message.reply_text(text=f"Search results:\n\n{result_text}")
    except requests.RequestException as e:
        error_message = f"Error fetching results: {e}"
        if query:
            await query.edit_message_text(text=error_message)
        else:
            await update.message.reply_text(error_message)

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
    application.add_handler(CallbackQueryHandler(handle_search_type, pattern="set_type:.*"))
    application.add_handler(CallbackQueryHandler(handle_parameter, pattern="set_param:.*"))
    application.add_handler(CallbackQueryHandler(execute_search, pattern="execute_search"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))

    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
