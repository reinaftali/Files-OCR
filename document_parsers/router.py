import os
from .pdf import get_pdf_page_generator
from .word import get_docx_page_generator, convert_doc_to_docx_windows
from .tabular import get_csv_page_generator, get_excel_page_generator, convert_xls_to_xlsx_windows
from .ocr_engine import run_tesseract_ocr

def get_combined_page_iterator(file_path):
    _, file_extension = os.path.splitext(file_path)
    ext = file_extension.lower().strip('.')
    
    if ext == 'pdf':
        gen = get_pdf_page_generator(file_path)
    elif ext == 'docx':
        gen = get_docx_page_generator(file_path)
    elif ext == 'doc':
        gen = get_docx_page_generator(convert_doc_to_docx_windows(file_path))
    elif ext == 'csv':
        gen = get_csv_page_generator(file_path)
    elif ext == 'xlsx':
        gen = get_excel_page_generator(file_path)
    elif ext == 'xls':
        gen = get_excel_page_generator(convert_xls_to_xlsx_windows(file_path))
    else:
        raise ValueError(f"Format {ext} not supported")

    for item in gen:
        if isinstance(item, dict):
            if item.get("type") == "needs_ocr":
                yield run_tesseract_ocr(item["data"])
            else:
                yield item.get("data", "")
        else:
            yield item