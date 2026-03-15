import fitz

def get_pdf_page_generator(file_path):
    doc = fitz.open(file_path)
    try:
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text("text").strip()
            
            if len(text) < 10:
                yield {"type": "needs_ocr", "page_num": page_num, "data": page}
            else:
                yield {"type": "text", "page_num": page_num, "data": text}
    finally:
        doc.close()