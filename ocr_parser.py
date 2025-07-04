import easyocr
from PIL import Image
import io
import re
import numpy as np

# Ініціалізація OCR-читача (англійська, українська, російська)
reader = easyocr.Reader(['uk', 'ru', 'en'], gpu=False)

def parse_receipt_text(img_bytes: bytes):
    # Завантаження зображення
    image = Image.open(io.BytesIO(img_bytes))
    image_np = np.array(image)

    # Отримання тексту з фото
    lines = reader.readtext(image_np, detail=0)
    text = "\n".join(lines)

    # Пошук шаблону: V + цифри + час відкриття і закриття
    pattern = re.compile(r"(?:V|v)?(\d+).*?(\d{2}:\d{2}).*?(\d{2}:\d{2})", re.DOTALL)
    matches = pattern.findall(text)

    result = []
    for table_num, start, end in matches:
        result.append({
            "Стіл": table_num.strip(),
            "З": start.strip(),
            "По": end.strip()
        })

    if not result:
        raise ValueError("Не знайдено жодного столу.")
    return result
