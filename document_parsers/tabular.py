import os
import csv
import tempfile
import openpyxl
import win32com.client as win32

def convert_xls_to_xlsx_windows(file_path):
    abs_file_path = os.path.abspath(file_path)
    out_dir = tempfile.gettempdir()
    base_name = os.path.basename(abs_file_path)
    name_without_ext = os.path.splitext(base_name)[0]
    new_file_path = os.path.join(out_dir, f"{name_without_ext}.xlsx")
    
    excel = win32.DispatchEx('Excel.Application')
    excel.Visible = False
    excel.DisplayAlerts = False 
    
    try:
        wb = excel.Workbooks.Open(abs_file_path)
        wb.SaveAs(new_file_path, FileFormat=51)
        wb.Close()
    finally:
        excel.Quit()
        
    return new_file_path

def get_csv_page_generator(file_path, rows_per_chunk=50):
    chunk = []
    with open(file_path, mode='r', encoding='utf-8-sig', errors='replace') as f:
        reader = csv.reader(f)
        for row in reader:
            text = " ".join([str(cell).strip() for cell in row if str(cell).strip()])
            if text:
                chunk.append(text)
                
            if len(chunk) >= rows_per_chunk:
                yield {"type": "text", "data": "\n".join(chunk)}
                chunk = []
                
        if chunk:
            yield {"type": "text", "data": "\n".join(chunk)}

def get_excel_page_generator(file_path, rows_per_chunk=50):
    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    chunk = []
    
    try:
        for sheet in wb.worksheets:
            for row in sheet.iter_rows(values_only=True):
                text = " ".join([str(cell).strip() for cell in row if cell is not None and str(cell).strip()])
                if text:
                    chunk.append(text)
                    
                if len(chunk) >= rows_per_chunk:
                    yield {"type": "text", "data": "\n".join(chunk)}
                    chunk = []
        if chunk:
            yield {"type": "text", "data": "\n".join(chunk)}
    finally:
        wb.close()