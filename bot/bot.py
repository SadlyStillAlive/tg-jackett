import os
import logging
import requests
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

load_dotenv("/shared/envs/.env")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
JACKETT_API_KEY = os.getenv("JACKETT_API_KEY")
DOCKER_JACKETT_URL = os.getenv("JACKETT_API_URL") or "http://0.0.0.0:9117"
LOCAL_JACKETT_URL = "https://jackett-ewy7.onrender.com/"  # Your local Jackett URL

if not all([TELEGRAM_BOT_TOKEN, JACKETT_API_KEY]):
    raise EnvironmentError("Missing TELEGRAM_BOT_TOKEN or JACKETT_API_KEY")

CURRENT_JACKETT_URL = DOCKER_JACKETT_URL  # Default source

RESULTS_PER_PAGE = 2


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    buttons = [
        [
            InlineKeyboardButton("Switch to Local Jackett", callback_data="switch_local"),
            InlineKeyboardButton("Switch to Docker Jackett", callback_data="switch_docker"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(buttons)

    await update.message.reply_text(
        "Welcome to Jackett Search Bot!\n"
        "Use /search <query> to search.\n"
        "You can switch the Jackett source below:",
        reply_markup=reply_markup,
    )


async def switch_source(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global CURRENT_JACKETT_URL
    query = update.callback_query
    await query.answer()

    if query.data == "switch_local":
        CURRENT_JACKETT_URL = LOCAL_JACKETT_URL
        await query.edit_message_text(
            "Switched to the **Local Jackett** source.\n"
            "Now you can use /search <query> to search there.",
            parse_mode="Markdown",
        )
    elif query.data == "switch_docker":
        CURRENT_JACKETT_URL = DOCKER_JACKETT_URL
        await query.edit_message_text(
            "Switched to the **Docker Jackett** source.\n"
            "Now you can use /search <query> to search there.",
            parse_mode="Markdown",
        )


def format_result(result):
    title = result.get("Title")
    size = result.get("Size", 0)
    size_mb = size / (1024 * 1024)
    size_str = f"{size_mb:.2f} MB" if size_mb < 1024 else f"{size_mb / 1024:.2f} GB"
    seeders = result.get("Seeders", 0)
    link = result.get("MagnetUri") or result.get("Link")
    return (
        f"🎬 *{title}*\n"
        f"📦 Size: {size_str}\n"
        f"🌱 Seeders: {seeders}\n"
        f"🔗 [Magnet/Link]({link})"
    )


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("Usage: /search <query>")
        return

    api_url = f"{CURRENT_JACKETT_URL}/api/v2.0/indexers/all/results"
    params = {
        "apikey": JACKETT_API_KEY,
        "Query": query,
        "Limit": 50,  # Fetch up to 50 results to paginate locally
        "SortBy": "seeders",
        "SortDirection": "desc",
    }

    try:
        response = requests.get(api_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        results = data.get("Results")
        if not results:
            await update.message.reply_text("No results found for your query.")
            return

        # Save results & position in user_data
        context.user_data["search_results"] = results
        context.user_data["search_pos"] = 0

        # Show first page
        await show_result_page(update, context)

    except requests.RequestException as e:
        logger.error(f"Jackett API error: {e}")
        await update.message.reply_text(f"Error fetching results: {e}")


async def show_result_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    results = context.user_data.get("search_results", [])
    pos = context.user_data.get("search_pos", 0)

    if not results:
        await update.message.reply_text("No search results stored.")
        return

    # Calculate page slice
    page_results = results[pos : pos + RESULTS_PER_PAGE]
    texts = [format_result(r) for r in page_results]
    reply_text = "\n\n".join(texts)

    # Navigation buttons
    buttons = []
    if pos > 0:
        buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data="page_prev"))
    if pos + RESULTS_PER_PAGE < len(results):
        buttons.append(InlineKeyboardButton("Next ➡️", callback_data="page_next"))

    reply_markup = InlineKeyboardMarkup([buttons]) if buttons else None

    # Edit or send new message
    if update.callback_query:
        await update.callback_query.edit_message_text(
            reply_text, parse_mode="Markdown", disable_web_page_preview=True, reply_markup=reply_markup
        )
        await update.callback_query.answer()
    else:
        await update.message.reply_text(
            reply_text, parse_mode="Markdown", disable_web_page_preview=True, reply_markup=reply_markup
        )


async def paginate_results(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    pos = context.user_data.get("search_pos", 0)
    results = context.user_data.get("search_results", [])

    if not results:
        await query.edit_message_text("No active search to paginate.")
        return

    if query.data == "page_next":
        pos = min(pos + RESULTS_PER_PAGE, len(results) - RESULTS_PER_PAGE)
    elif query.data == "page_prev":
        pos = max(pos - RESULTS_PER_PAGE, 0)

    context.user_data["search_pos"] = pos

    # Show updated page
    await show_result_page(update, context)


async def info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        f"Current Jackett source URL:\n`{CURRENT_JACKETT_URL}`", parse_mode="Markdown"
    )


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Stopping the bot...")
    context.application.stop()


def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("search", search))
    application.add_handler(CommandHandler("info", info))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CallbackQueryHandler(switch_source, pattern="switch_.*"))
    application.add_handler(CallbackQueryHandler(paginate_results, pattern="page_.*"))

    print("Bot is running...")
    application.run_polling()


if __name__ == "__main__":
    main()
