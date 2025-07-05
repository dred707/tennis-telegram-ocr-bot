from openpyxl import load_workbook
from io import BytesIO
import logging

logging.basicConfig(level=logging.DEBUG)

def fill_excel_template(entries, template_path="template.xlsx"):
    wb = load_workbook(template_path)
    ws = wb["main"]

    row = 15
    for entry in entries:
        table_str = entry.get("Стіл", "")
        table_digits = "".join(filter(str.isdigit, table_str))
        try:
            table = int(table_digits) if table_digits else ""
        except ValueError:
            table = ""

        start_time = entry.get("З", "")
        end_time = entry.get("По", "")

        logging.debug(f"Row {row}: Стіл={table}, З={start_time}, По={end_time}")

        ws[f"A{row}"] = table
        ws[f"B{row}"] = start_time
        ws[f"C{row}"] = end_time
        row += 1

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output
