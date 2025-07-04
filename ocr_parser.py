
from PIL import Image
import pytesseract
import io
import re
import logging
import cv2
import numpy as np

logging.basicConfig(level=logging.DEBUG)

def split_image_horizontally(img_bytes: bytes, parts: int = 3):
    image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    np_img = np.array(image)
    width = np_img.shape[1]
    step = width // parts

    segments = []
    for i in range(parts):
        x_start = i * step
        x_end = (i + 1) * step if i < parts - 1 else width
        crop = np_img[:, x_start:x_end]
        buffer = io.BytesIO()
        Image.fromarray(crop).save(buffer, format="PNG")
        segments.append(buffer.getvalue())

    return segments

def parse_receipt_text(img_bytes: bytes):
    sub_images = split_image_horizontally(img_bytes, parts=3)

    results = []
    for sub_img in sub_images:
        image = Image.open(io.BytesIO(sub_img))
        text = pytesseract.image_to_string(image)

        logging.debug("\n=== OCR TEXT ===\n%s\n", text)

        # Шукаємо номер столу
        table_match = re.search(r'V\d+', text)
        table = table_match.group(0) if table_match else "V?"

        # Рядки тексту
        lines = text.splitlines()

        # Шукаємо часи тільки в тих рядках, що не містять "відкрито"/"надруковано"
        valid_lines = [line for line in lines if not re.search(r'(відкрито|надруковано)', line, re.IGNORECASE)]
        valid_text = ' '.join(valid_lines)

        # Шукаємо всі часи у форматі hh:mm або hh;mm
        times = re.findall(r'(\d{2}[:;]\d{2})', valid_text)
        times = [t.replace(';', ':') for t in times]

        if len(times) >= 2:
            results.append({
                "Стіл": table,
                "З": times[0],
                "По": times[1]
            })

    if not results:
        raise ValueError("Не знайдено жодного чека.")

    return results
