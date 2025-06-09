import os
import logging
import requests
from dotenv import load_dotenv
from aiohttp import web
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

load_dotenv("/shared/envs/.env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
JACKETT_API_KEY = os.getenv("JACKETT_API_KEY")
JACKETT_API_URL = os.getenv("JACKETT_API_URL")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not all([TELEGRAM_BOT_TOKEN, JACKETT_API_KEY, JACKETT_API_URL, WEBHOOK_URL]):
    raise EnvironmentError("Missing required environment variables.")

RESULTS_PER_PAGE = 2


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Welcome to Jackett Search Bot!\nUse /search <query> to search.")


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

    api_url = f"{JACKETT_API_URL}/api/v2.0/indexers/all/results"
    params = {
        "apikey": JACKETT_API_KEY,
        "Query": query,
        "Limit": 50,
        "SortBy": "seeders",
        "SortDirection": "desc",
    }

    try:
        response = requests.get(api_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        results = data.get("Results", [])
        if not results:
            await update.message.reply_text("No results found.")
            return

        context.user_data["search_results"] = results
        context.user_data["search_pos"] = 0
        await show_result_page(update, context)
    except Exception as e:
        logger.error(f"Search error: {e}")
        await update.message.reply_text(f"Error: {e}")


async def show_result_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    results = context.user_data.get("search_results", [])
    pos = context.user_data.get("search_pos", 0)
    page_results = results[pos:pos + RESULTS_PER_PAGE]

    buttons = []
    if pos > 0:
        buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data="page_prev"))
    if pos + RESULTS_PER_PAGE < len(results):
        buttons.append(InlineKeyboardButton("Next ➡️", callback_data="page_next"))

    reply_markup = InlineKeyboardMarkup([buttons]) if buttons else None
    reply_text = "\n\n".join(format_result(r) for r in page_results)

    if update.callback_query:
        await update.callback_query.edit_message_text(
            reply_text, parse_mode="Markdown", disable_web_page_preview=True, reply_markup=reply_markup
        )
        await update.callback_query.answer()
    else:
        await update.message.reply_text(
            reply_text, parse_mode="Markdown", disable_web_page_preview=True, reply_markup=reply_markup
        )


async def paginate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    pos = context.user_data.get("search_pos", 0)
    if query.data == "page_next":
        context.user_data["search_pos"] = pos + RESULTS_PER_PAGE
    elif query.data == "page_prev":
        context.user_data["search_pos"] = max(0, pos - RESULTS_PER_PAGE)
    await show_result_page(update, context)


async def info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"Jackett URL:\n`{JACKETT_API_URL}`", parse_mode="Markdown")


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Bot stopping...")
    await context.application.shutdown()


async def health_check(request):
    return web.Response(text="OK", status=200)


async def handle_webhook(request: web.Request) -> web.Response:
    bot = request.app["bot"]
    application = request.app["app"]
    data = await request.json()
    update = Update.de_json(data, bot)
    await application.update_queue.put(update)
    return web.Response(text="ok")


async def on_startup(app: web.Application):
    bot = app["bot"]
    await bot.set_webhook(WEBHOOK_URL)


async def on_cleanup(app: web.Application):
    bot = app["bot"]
    await bot.delete_webhook()


def main():
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    application = Application.builder().bot(bot).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("search", search))
    application.add_handler(CommandHandler("info", info))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CallbackQueryHandler(paginate, pattern="page_.*"))

    app = web.Application()
    app["bot"] = bot
    app["app"] = application

    app.router.add_post(f"/{TELEGRAM_BOT_TOKEN}", handle_webhook)
    app.router.add_get("/ping", health_check)

    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)

    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))


if __name__ == "__main__":
    main()
