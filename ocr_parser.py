from PIL import Image
import pytesseract
import io
import re
import logging

logging.basicConfig(level=logging.INFO)

def parse_receipt_text(img_bytes: bytes):
    image = Image.open(io.BytesIO(img_bytes))
    text = pytesseract.image_to_string(image)

    #logging.debug("\n=== OCR TEXT START ===\n%s\n=== OCR TEXT END ===", text)
    #logging.INFO("\n=== OCR TEXT START ===\n%s\n=== OCR TEXT END ===", text)

    # Виправлення частих помилок OCR
    text = text.replace("TeHHnc", "Теннис").replace("Теннic", "Теннис").replace("Теніс", "Теннис")

    # Пошук столів: _V\d+
    tables = re.findall(r'_V\d+', text)

    # Формат 1: 20:04-21:29 (звичайний)
    normal_matches = re.findall(r'(\d{2}:\d{2})\s*[-–]\s*(\d{2}:\d{2})', text)

    # Формат 2: 20:\n04-21:29 або 20:\n04\n-21:\n29
    split_matches = re.findall(r'(\d{2})[:\n]{1,2}(\d{2})\s*[-–]\s*(\d{2})[:\n]{1,2}(\d{2})', text)
    normalized_split = [(f"{h1}:{m1}", f"{h2}:{m2}") for h1, m1, h2, m2 in split_matches]

    # Обʼєднаний список пар часу
    time_pairs = normal_matches + normalized_split

    result = []
    for i in range(min(len(tables), len(time_pairs))):
        result.append({
            "Стіл": tables[i],
            "З": time_pairs[i][0],
            "По": time_pairs[i][1]
        })

    if not result:
        raise ValueError("Не знайдено жодного чека.")

    return result
