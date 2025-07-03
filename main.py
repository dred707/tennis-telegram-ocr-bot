import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, ContextTypes, filters
)
from datetime import datetime
from ocr_parser import parse_receipt_text
from excel_writer import fill_excel_template
from pathlib import Path

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

logging.basicConfig(level=logging.INFO)

main_keyboard = ReplyKeyboardMarkup(
    [["🧾 Завантажити фото чека"]],
    resize_keyboard=True
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привіт! Обери дію:", reply_markup=main_keyboard)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "🧾 Завантажити фото чека":
        context.user_data["awaiting_receipt"] = True
        await update.message.reply_text("Надішли фото чека.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_receipt"):
        await update.message.reply_text("Спочатку обери дію.")
        return

    photo_file = await update.message.photo[-1].get_file()
    img_bytes = await photo_file.download_as_bytearray()

    try:
        parsed = parse_receipt_text(img_bytes)
        filename = f"{datetime.now():%y%m%d}_BreiksCalc.xlsx"
        excel_bytes = fill_excel_template(parsed, filename)
        await update.message.reply_document(document=excel_bytes, filename=filename)
    except Exception as e:
        logging.exception("Помилка при обробці чека:")
        await update.message.reply_text("Не вдалося обробити чек 😢")

    context.user_data["awaiting_receipt"] = False

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.run_polling()