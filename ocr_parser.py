
from PIL import Image
import pytesseract
import io
import re
import logging
import cv2
import numpy as np

logging.basicConfig(level=logging.DEBUG)

def normalize_time_fragment(value: str, pad: str) -> str:
    if len(value) == 2 and value.isdigit():
        return value
    elif len(value) == 1 and value.isdigit():
        return pad + value
    elif any(c.isdigit() for c in value):
        return ''.join(c if c.isdigit() else pad for c in value).ljust(2, pad)
    return pad * 2

def parse_receipt_text_block(text: str):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    logging.debug("OCR TEXT BLOCK:\n" + "\n".join(lines))

    table_match = re.search(r'V(\d+)', text)
    table = table_match.group(1) if table_match else ""

    # Знаходимо якірний рядок: найкоротший рядок з лише цифрами або з ":" і "-"
    anchor_line = None
    min_len = float('inf')
    for line in lines:
        stripped = line.replace(" ", "")
        if re.fullmatch(r'[\d:;-]+', stripped):
            if len(stripped) < min_len:
                anchor_line = stripped
                min_len = len(stripped)

    if not anchor_line:
        return {
            "Стіл": table,
            "З": "",
            "По": ""
        }

    try:
        anchor_idx = lines.index(next(l for l in lines if anchor_line in l.replace(" ", "")))
    except StopIteration:
        return {
            "Стіл": table,
            "З": "",
            "По": ""
        }

    upper_line = lines[anchor_idx - 1] if anchor_idx > 0 else ""
    upper_match = re.search(r'(\d{1,2})[:;]', upper_line)
    start_hh_raw = upper_match.group(1) if upper_match else ""

    anchor_match = re.search(r'(\d{1,2})[-:;](\d{1,2})[:;](\d{1,2})', anchor_line)
    if anchor_match:
        start_mm_raw = anchor_match.group(1)
        end_hh_raw = anchor_match.group(2)
        end_mm_raw = anchor_match.group(3)
    else:
        fallback = re.findall(r'(\d{1,2})', anchor_line)
        if len(fallback) >= 2:
            end_hh_raw, end_mm_raw = fallback[-2], fallback[-1]
            start_mm_raw = fallback[0] if len(fallback) >= 3 else ""
        else:
            start_mm_raw = end_hh_raw = end_mm_raw = ""

    start_hh = normalize_time_fragment(start_hh_raw, 'h')
    start_mm = normalize_time_fragment(start_mm_raw, 'm')
    end_hh = normalize_time_fragment(end_hh_raw, 'h')
    end_mm = normalize_time_fragment(end_mm_raw, 'm')

    start_time = f"{start_hh}:{start_mm}" if start_hh or start_mm else ""
    end_time = f"{end_hh}:{end_mm}" if end_hh or end_mm else ""

    return {
        "Стіл": table,
        "З": start_time,
        "По": end_time
    }

def parse_receipts_from_image(image_path):
    image = Image.open(image_path).convert("RGB")
    full_text = pytesseract.image_to_string(image)

    logging.debug(f"Обробка зображення: {image_path}")
    logging.debug("Повний OCR текст:\n" + full_text)

    # Розділити текст на блоки по кожному знайденому V\d+
    split_indices = [m.start() for m in re.finditer(r'V\d+', full_text)]
    split_indices.append(len(full_text))

    blocks = [full_text[split_indices[i]:split_indices[i+1]] for i in range(len(split_indices)-1)]

    for i, block in enumerate(blocks):
        logging.debug(f"--- Блок #{i+1} ---\n{block}\n----------------")

    results = [parse_receipt_text_block(block) for block in blocks]

    logging.debug(f"Результати парсингу: {results}")
    return results