from PIL import Image
import pytesseract
import re
import logging

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
    logging.debug("OCR TEXT BLOCK:")
    for l in lines:
        logging.debug("    " + l)

    table_match = re.search(r'V(\d+)', text)
    table = table_match.group(1) if table_match else ""

    anchor_line = None
    min_len = float('inf')
    for line in lines:
        stripped = line.replace(" ", "")
        if re.fullmatch(r'[\d:;-]+', stripped):
            logging.debug(f"🟡 Anchor-кандидат: {stripped}")
            if len(stripped) < min_len:
                anchor_line = stripped
                min_len = len(stripped)
    logging.debug(f"✅ Anchor-line знайдено: {anchor_line}")

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

    # Показуємо сирий OCR текст
    logging.debug("📄 OCR сирий текст:")
    for line in full_text.splitlines():
        logging.debug("    " + line)

    # Передаємо весь текст як один блок
    results = []
    result = parse_receipt_text_block(full_text)
    results.append(result)

    logging.debug(f"✅ Результат для зображення: {results}")
    return results
