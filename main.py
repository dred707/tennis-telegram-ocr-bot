import os
import logging
import asyncio
import glob
from datetime import datetime
import nest_asyncio
from aiohttp import web
from telegram import Update, ReplyKeyboardMarkup, InputFile
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes,
)
from excel_writer import create_excel_from_parsed_data
from ocr_parser import parse_receipts_from_image

nest_asyncio.apply()

# --- Налаштування логування ---
logging.basicConfig(level=logging.WARNING)
for noisy_logger in ["telegram", "telegram.ext", "httpx", "httpcore", "asyncio"]:
    logging.getLogger(noisy_logger).setLevel(logging.INFO)

ASK_FILE_COUNT = range(1)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["Порахувати"]]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Виберіть дію:", reply_markup=markup)

async def ask_file_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Скільки останніх файлів опрацювати? (1-5)")
    return ASK_FILE_COUNT

async def handle_file_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        count = int(update.message.text.strip())
        if not 1 <= count <= 5:
            raise ValueError()
    except ValueError:
        await update.message.reply_text("Введіть число від 1 до 5.")
        return ASK_FILE_COUNT

    await update.message.reply_text("🕓 Опрацьовую чеки...")
    image_files = sorted(glob.glob("received/*.jpg"), reverse=True)[:count]
    all_data = []

    for path in image_files:
        parsed = parse_receipts_from_image(path)
        all_data.extend(parsed)

    os.makedirs("output", exist_ok=True)
    today_str = datetime.now().strftime("%y%m%d")
    filename = f"{today_str}_CalcTennis.xlsx"
    output_path = f"output/{filename}"
    create_excel_from_parsed_data(all_data, output_path)

    with open(output_path, "rb") as f:
        await update.message.reply_document(document=InputFile(f), filename=os.path.basename(output_path))

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Операцію скасовано.")
    return ConversationHandler.END

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = None
    if update.message.document and update.message.document.mime_type.startswith("image/"):
        file = await context.bot.get_file(update.message.document.file_id)
    elif update.message.photo:
        file = await context.bot.get_file(update.message.photo[-1].file_id)

    filename = datetime.now().strftime("%Y%m%d_%H%M%S_%f.jpg")
    if file:
        os.makedirs("received", exist_ok=True)
        path = os.path.join("received", filename)
        await file.download_to_drive(path)
        await update.message.reply_text("✅ Фото збережено")
    else:
        await update.message.reply_text("⚠️ Це не зображення")

async def build_application():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("❌ TELEGRAM_BOT_TOKEN не встановлено")

    app = ApplicationBuilder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^Порахувати$"), ask_file_count)],
        states={ASK_FILE_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_file_count)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.IMAGE, handle_photo))

    return app

async def run_webhook():
    app = await build_application()
    webhook_url = os.getenv("WEBHOOK_URL", "").rstrip("/")
    await app.bot.set_webhook(f"{webhook_url}/webhook")
    print(f"🌐 Webhook зареєстровано: {webhook_url}/webhook")

    async def telegram_webhook_handler(request):
        print("📥 Запит від Telegram отримано")
        data = await request.json()
        await app.update_queue.put(data)
        return web.Response()

    aio_app = web.Application()
    aio_app.router.add_post("/webhook", telegram_webhook_handler)
    aio_app.router.add_get("/", lambda request: web.Response(text="Bot is alive."))
    return aio_app

async def run_polling():
    print("🖥 Запуск у polling-режимі")
    app = await build_application()
    await app.run_polling()

if __name__ == "__main__":
    if os.getenv("WEBHOOK_URL"):
        print("🌐 Запуск у режимі webhook (Railway)")
        aio_app = asyncio.get_event_loop().run_until_complete(run_webhook())
        web.run_app(aio_app, port=int(os.getenv("PORT", "8000")))
    else:
        asyncio.run(run_polling())
