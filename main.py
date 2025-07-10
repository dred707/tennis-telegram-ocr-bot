
import os
import logging
import asyncio
import glob
from datetime import datetime
import nest_asyncio
from telegram import Update, InputFile
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    filters,
    ContextTypes,
)
from excel_writer import create_excel_from_parsed_data
from ocr_parser import parse_receipts_from_image

nest_asyncio.apply()

logging.basicConfig(level=logging.WARNING)
for noisy_logger in ["telegram", "telegram.ext", "httpx", "httpcore", "asyncio"]:
    logging.getLogger(noisy_logger).setLevel(logging.INFO)


async def handle_file_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        count = int(update.message.text.strip())
        if not 1 <= count <= 5:
            raise ValueError()
    except ValueError:
        await update.message.reply_text("Введіть число від 1 до 5 для обробки чеків.")
        return

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

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_file_count))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.IMAGE, handle_photo))

    return app


async def run_webhook():
    from aiohttp import web

    app = await build_application()
    webhook_url = os.getenv("WEBHOOK_URL", "").rstrip("/")
    await app.bot.set_webhook(f"{webhook_url}/webhook")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    print(f"🌐 Webhook зареєстровано: {webhook_url}/webhook")

    aio_app = web.Application()
    async def telegram_webhook_handler(request):
        data = await request.json()
        await app.update_queue.put(data)
        print("📥 Запит оброблено Telegram Application")
        return web.Response()

    aio_app.router.add_post("/webhook", telegram_webhook_handler)
    aio_app.router.add_get("/", lambda request: web.Response(text="Bot is alive."))

    return aio_app


async def run_polling():
    print("🖥 Запуск у polling-режимі")
    app = await build_application()

    print("🧼 Знімаю webhook...")
    await app.bot.delete_webhook(drop_pending_updates=True)

    print("🚀 Запуск Application (polling)...")
    await app.run_polling()


if __name__ == "__main__":
    if os.getenv("WEBHOOK_URL"):
        print("🌐 Запуск у режимі webhook (Railway)")
        import aiohttp.web

        async def start_webhook_server():
            aio_app = await run_webhook()
            runner = aiohttp.web.AppRunner(aio_app)
            await runner.setup()
            site = aiohttp.web.TCPSite(runner, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
            await site.start()
            print("✅ AIOHTTP сервер запущено — очікуємо запити...")
            while True:
                await asyncio.sleep(3600)

        asyncio.run(start_webhook_server())
    else:
        asyncio.run(run_polling())
