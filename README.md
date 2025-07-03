# Telegram OCR Bot

## Можливості
- Приймає фото чека
- Розпізнає номер столу та час
- Записує дані у Excel
- Надсилає файл назад

## Швидкий старт
1. Створи Telegram-бота через @BotFather
2. Замінити `TOKEN` в main.py або задати TELEGRAM_BOT_TOKEN в Railway
3. Встанови залежності:
```
pip install -r requirements.txt
```
4. Запусти бота:
```
python main.py
```

Файл-шаблон повинен мати назву `template.xlsx` та аркуш `"main"`.