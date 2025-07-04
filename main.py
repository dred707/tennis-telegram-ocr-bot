import logging
import os
from datetime import datetime
import pytesseract
from PIL import Image
import io
import re

from telegram import Update, ReplyKeyboardMarkup, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, ContextTypes, filters
)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

main_keyboard = ReplyKeyboardMarkup(
    [["🧾 Завантажити фото чека"]],
    resize_keyboard=True
)

def normalize_text(text: str) -> str:
    substitutions = {
        'TeHHuc': 'Теннис',
        'TeHHMc': 'Теннис',
        '¥': 'V',
        'V ': 'V',
        'Теннic': 'Теннис',
    }
    for wrong, correct in substitutions.items():
        text = text.replace(wrong, correct)
    return text

def split_receipts_blocks(text: str):
    text = normalize_text(text)
    blocks = re.split(r'(Стiл\s*#\s*Теннис_V\d)', text)
    receipts = []
    for i in range(1, len(blocks), 2):
        full = blocks[i] + (blocks[i + 1] if i + 1 < len(blocks) else '')
        receipts.append(full)
    return receipts

def parse_single_receipt(text: str):
    text = normalize_text(text)
    table_match = re.search(r'(Теннис_V\d)', text)
    times = re.findall(r'(\d{2}:\d{2})', text)

    if not table_match or len(times) < 2:
        return None

    return {
        "Стіл": table_match.group(1),
        "З": times[0],
        "По": times[1]
    }

def parse_receipt_text(img_bytes: bytes):
    image = Image.open(io.BytesIO(img_bytes))
    text = pytesseract.image_to_string(image)
    blocks = split_receipts_blocks(text)
    result = []
    for block in blocks:
        parsed = parse_single_receipt(block)
        if parsed:
            result.append(parsed)
    if not result:
        raise ValueError("Не знайдено жодного чека.")
    return result

def fill_excel_template(data, filename):
    import pandas as pd
    from io import BytesIO
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Результат')
    output.seek(0)
    return output

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
        await update.message.reply_document(document=InputFile(excel_bytes, filename=filename))
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
