
import logging
from telegram import Update, ReplyKeyboardMarkup, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes
import os
import glob
from datetime import datetime
from excel_writer import create_excel_from_parsed_data
from ocr_parser import parse_receipts_from_image

# --- Налаштування логування ---
logging.basicConfig(level=logging.WARNING)
for noisy_logger in ["telegram", "telegram.ext", "httpx", "httpcore", "asyncio"]:
    logging.getLogger(noisy_logger).setLevel(logging.INFO)

ASK_FILE_COUNT = range(1)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["Порахувати"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Виберіть дію:", reply_markup=reply_markup)

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

    image_files = sorted(glob.glob("received/*.jpg"), reverse=True)[:count]
    all_data = []

    for img_path in image_files:
        parsed = parse_receipts_from_image(img_path)
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

def main():
    application = ApplicationBuilder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^Порахувати$"), ask_file_count)],
        states={ASK_FILE_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_file_count)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)

    application.run_polling()

if __name__ == "__main__":
    main()