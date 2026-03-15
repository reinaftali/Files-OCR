import os
from document_parsers.router import get_combined_page_iterator
from search_engine import process_and_search

def main():
    folder_path = r"C:\Projects\Files-OCR\testfiles"
    phrases = ["בית אדום", "בית ירוק", "בית כחול"]
    
    print(f"[*] Starting Batch Processing...\n")

    for filename in os.listdir(folder_path):
        if filename.endswith('.py'): continue
        
        file_path = os.path.join(folder_path, filename)
        print(f"[-] Processing: {filename}")
        
        try:
            # 1. Get iterator (Auto-detects format & OCR needs)
            page_iterator = get_combined_page_iterator(file_path)
            
            # 2. Run Robust Search
            results = process_and_search(filename, page_iterator, phrases)
            
            print(f"    Results: {results}\n")
            
        except Exception as e:
            print(f"    [X] Error: {e}\n")

if __name__ == "__main__":
    main()