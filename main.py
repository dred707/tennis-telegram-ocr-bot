
import logging
import os
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, ContextTypes, filters
)

from ocr_parser import parse_receipt_text
from excel_writer import fill_excel_template

# --- Налаштування логування ---
logging.basicConfig(level=logging.WARNING)
for noisy_logger in ["telegram", "telegram.ext", "httpx", "httpcore", "asyncio"]:
    logging.getLogger(noisy_logger).setLevel(logging.INFO)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

main_keyboard = ReplyKeyboardMarkup(
    [["🧾 Завантажити фото чека"]],
    resize_keyboard=True
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привіт! Обери дію:", reply_markup=main_keyboard)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "🧾 Завантажити фото чека":
        context.user_data["awaiting_receipt"] = True
        await update.message.reply_text("Надішли фото чека або скан як документ.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_receipt"):
        await update.message.reply_text("Спочатку обери дію.")
        return

    photo_file = await update.message.photo[-1].get_file()
    img_bytes = await photo_file.download_as_bytearray()
    await process_and_respond(update, context, img_bytes)

async def handle_image_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_receipt"):
        await update.message.reply_text("Спочатку обери дію.")
        return

    document = update.message.document
    if document.mime_type and "image" in document.mime_type:
        file = await document.get_file()
        img_bytes = await file.download_as_bytearray()
        await process_and_respond(update, context, img_bytes)
    else:
        await update.message.reply_text("Будь ласка, надішли саме зображення (jpg/png) як документ.")

async def process_and_respond(update: Update, context: ContextTypes.DEFAULT_TYPE, img_bytes: bytes):
    try:
        parsed = parse_receipt_text(img_bytes)
        filename = f"{datetime.now():%y%m%d}_BreiksCalc.xlsx"
        excel_bytes = fill_excel_template(parsed)
        await update.message.reply_document(document=InputFile(excel_bytes, filename=filename))
    except Exception as e:
        logging.exception("Помилка при обробці чека/документа:")
        await update.message.reply_text("Не вдалося обробити файл 😢")
    context.user_data["awaiting_receipt"] = False

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.IMAGE, handle_image_file))
    app.run_polling()
