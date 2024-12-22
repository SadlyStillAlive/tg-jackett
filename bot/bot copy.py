import os
import json
from dotenv import load_dotenv
from telegram import Update, ForceReply
from telegram.ext import Application, CommandHandler, ContextTypes
import requests

# Load environment variables from the specific .env file
load_dotenv("/shared/envs/.env")

# Read environment variables
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
JACKETT_API_URL = os.getenv("JACKETT_API_URL")
JACKETT_API_KEY = os.getenv("JACKETT_API_KEY")
CONFIG_FILE_PATH = "/shared/envs/config.json"  # Update this to the correct path if needed

# Validate and fix JACKETT_BASE_URL
if not JACKETT_API_URL.startswith(("http://", "https://")):
    JACKETT_API_URL = f"http://{JACKETT_API_URL}:9117"

if not BOT_TOKEN or not JACKETT_API_KEY:
    raise ValueError("Please set the BOT_TOKEN and JACKETT_API_KEY environment variables.")

def parse_results(xml_data, min_seeds=1):
    """
    Parses the XML response from Jackett and filters results based on minimum seeds.
    """
    from xml.etree import ElementTree as ET

    try:
        root = ET.fromstring(xml_data)
        results = []
        for item in root.findall(".//item"):
            title = item.find("title").text
            link = item.find("link").text
            seeds = int(item.find(".//seeders").text or 0)

            if seeds >= min_seeds:
                results.append(f"Title: {title}\nSeeds: {seeds}\nLink: {link}\n")
        
        return results
    except ET.ParseError as e:
        print(f"XML parsing error: {e}")
        return []

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the /search command. Allows category, limit, and seed-based filtering.
    """
    if not context.args:
        await update.message.reply_text(
            "Usage: /search <query> [category=<category_id>] [limit=<number>] [min_seeds=<number>]"
        )
        return

    query = " ".join(arg for arg in context.args if "=" not in arg)
    params = {"apikey": JACKETT_API_KEY, "t": "search", "q": query}

    # Parse additional parameters
    for arg in context.args:
        if "=" in arg:
            key, value = arg.split("=", 1)
            if key == "category":
                params["cat"] = value  # Category ID
            elif key == "limit":
                params["limit"] = value  # Max results
            elif key == "min_seeds":
                params["min_seeds"] = int(value)  # Minimum seeders

    try:
        response = requests.get(JACKETT_API_URL, params=params, timeout=10)
        response.raise_for_status()

        # Parse and filter results
        min_seeds = params.get("min_seeds", 1)
        results = parse_results(response.text, min_seeds)

        if results:
            limited_results = results[: int(params.get("limit", 5))]
            await update.message.reply_text(
                "Search Results:\n\n" + "\n\n".join(limited_results)
            )
        else:
            await update.message.reply_text(f"No results found for '{query}'.")

    except requests.exceptions.RequestException as e:
        await update.message.reply_text(f"Error querying Jackett: {e}")
    except Exception as e:
        print(f"Unexpected error in /search: {e}")
        await update.message.reply_text("An unexpected error occurred. Please try again later.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the /start command. Sends a welcome message.
    """
    try:
        user = update.effective_user
        message = (
            f"Hi {user.full_name}! Welcome to the Jackett Search Bot.\n\n"
            "Use /search <query> [category=<id>] [limit=<n>] [min_seeds=<n>] to search.\n\n"
            "Example: /search inception category=2000 limit=5 min_seeds=10"
        )
        await update.message.reply_text(message, reply_markup=ForceReply(selective=True))
    except Exception as e:
        print(f"Error in /start: {e}")
        await update.message.reply_text("An error occurred. Please try again later.")

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

def main():
    """
    Main function to start the Telegram bot.
    """
    application = Application.builder().token(BOT_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("search", search))
    application.add_handler(CommandHandler("info", info))

    # Start the bot
    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
