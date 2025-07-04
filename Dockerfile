# Базовий Python-образ
FROM python:3.11-slim

# Встановлюємо системні залежності, включаючи Tesseract
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Встановлюємо робочий каталог
WORKDIR /app

# Копіюємо залежності та встановлюємо їх
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо решту проєкту
COPY . .

# Встановлюємо змінну середовища (опціонально, для Railway)
ENV PYTHONUNBUFFERED=1

# Запускаємо бота
CMD ["python", "main.py"]