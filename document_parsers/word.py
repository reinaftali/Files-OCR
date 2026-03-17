import os
import tempfile
import docx
import win32com.client as win32

def convert_doc_to_docx_windows(file_path):
    abs_file_path = os.path.abspath(file_path)
    out_dir = tempfile.gettempdir()
    base_name = os.path.basename(abs_file_path)
    name_without_ext = os.path.splitext(base_name)[0]
    new_file_path = os.path.join(out_dir, f"{name_without_ext}.docx")
    
    word = win32.DispatchEx('Word.Application')
    word.Visible = False 
    
    try:
        doc = word.Documents.Open(abs_file_path)
        doc.SaveAs(new_file_path, FileFormat=16)
        doc.Close()
    finally:
        word.Quit()
        
    return new_file_path

def get_docx_page_generator(file_path, paragraphs_per_chunk=30):
    doc = docx.Document(file_path)
    chunk = []
    
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            chunk.append(text)
            
        if len(chunk) >= paragraphs_per_chunk:
            yield {"type": "text", "data": "\n".join(chunk)}
            chunk = []
            
    if chunk:
        yield {"type": "text", "data": "\n".join(chunk)}