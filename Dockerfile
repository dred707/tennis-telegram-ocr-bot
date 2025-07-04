FROM python:3.11-slim

# Встановлюємо залежності для Tesseract і Python
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    && rm -rf /var/lib/apt/lists/*

# Копіюємо файли
WORKDIR /app
COPY . .

# Встановлюємо Python-залежності
RUN pip install --no-cache-dir -r requirements.txt

# Запускаємо бота
CMD ["python", "main.py"]