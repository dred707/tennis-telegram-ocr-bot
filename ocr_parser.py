
from PIL import Image
import pytesseract
import io
import re
import logging
import cv2
import numpy as np

logging.basicConfig(level=logging.DEBUG)

def split_image_vertically(img_bytes, max_parts=4):
    image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    np_img = np.array(image)
    height = np_img.shape[0]
    step = height // max_parts

    parts = []
    for i in range(max_parts):
        y_start = i * step
        y_end = (i + 1) * step if i < max_parts - 1 else height
        crop = np_img[y_start:y_end, :]
        buffer = io.BytesIO()
        Image.fromarray(crop).save(buffer, format="PNG")
        parts.append(buffer.getvalue())

    return parts

def parse_receipt_text(img_bytes: bytes):
    sub_images = split_image_vertically(img_bytes, max_parts=4)

    tables = []
    time_pairs = []

    for sub_img in sub_images:
        image = Image.open(io.BytesIO(sub_img))
        text = pytesseract.image_to_string(image)

        logging.debug("\n=== OCR TEXT ===\n%s\n", text)

        text = text.replace("TeHHnc", "Теннис").replace("Теннic", "Теннис").replace("Теніс", "Теннис")

        tables.extend(re.findall(r'_V\d+', text))

        normal_matches = re.findall(r'(\d{2}:\d{2})\s*[-–]\s*(\d{2}:\d{2})', text)
        split_matches = re.findall(r'(\d{2})[:\n]{1,2}(\d{2})\s*[-–]\s*(\d{2})[:\n]{1,2}(\d{2})', text)
        normalized_split = [(f"{h1}:{m1}", f"{h2}:{m2}") for h1, m1, h2, m2 in split_matches]

        time_pairs.extend(normal_matches + normalized_split)

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
