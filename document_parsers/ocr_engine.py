import pytesseract
from PIL import Image
import io
import fitz

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def run_tesseract_ocr(page_obj):
    try:
        mat = fitz.Matrix(2, 2)
        pix = page_obj.get_pixmap(matrix=mat)
        
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))
        
        text = pytesseract.image_to_string(img, lang='heb+eng')
        
        return text.strip()
        
    except Exception as e:
        print(f"    [X] OCR Engine Error: {e}")
        return ""