import pytesseract
from PIL import Image
import io
import re

def parse_receipt_text(img_bytes: bytes):
    image = Image.open(io.BytesIO(img_bytes))
    text = pytesseract.image_to_string(image)
    pattern = re.compile(r"(V\d).*?(\d{2}:\d{2}).*?(\d{2}:\d{2})", re.DOTALL)
    matches = pattern.findall(text)

    result = []
    for table, start, end in matches:
        result.append({"Стіл": table, "З": start, "По": end})
    if not result:
        raise ValueError("Не знайдено жодного столу.")
    return result