import os
import pandas as pd
import psycopg2
from dotenv import load_dotenv
from document_parsers.router import get_combined_page_iterator, SUPPORTED_EXTENSIONS
from search_engine import process_and_search
from db_manager import DatabaseManager

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "database": os.getenv("DB_NAME", "ocr_db"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
    "port": int(os.getenv("DB_PORT", 5432))
}


FOLDER_PATH = os.getenv("TEST_DOCS_FOLDER")


def upload_to_s3(file_path):
    filename = os.path.basename(file_path)
    return f"s3://my-bucket/documents/{filename}"

def generate_final_report(db_config, output_csv_path="final_report.csv"):

    print("\n[*] Generating final CSV report...")
    query = """
        SELECT d.file_name, pm.phrase, pm.is_found
        FROM documents d
        JOIN phrase_matches pm ON d.id = pm.document_id
    """
    conn = psycopg2.connect(**db_config)
    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        print("    [!] No data to report.")
        return

    
    pivot_df = df.pivot_table(
        index='file_name', 
        columns='phrase', 
        values='is_found', 
        aggfunc='first'
    ).reset_index()

    pivot_df.to_csv(output_csv_path, index=False, encoding='utf-8-sig')
    print(f"    [V] Report saved to: {output_csv_path}")


def main():
    phrases = ["בית אדום", "בית ירוק", "בית כחול"] 
    
    db = DatabaseManager(DB_CONFIG)
    print(f"[*] Starting End-to-End Pipeline on {FOLDER_PATH}...\n")

    if not os.path.exists(FOLDER_PATH):
        print(f"[X] Error: Folder '{FOLDER_PATH}' does not exist.")
        return

    for filename in os.listdir(FOLDER_PATH):
        file_path = os.path.join(FOLDER_PATH, filename)
        
        if not os.path.isfile(file_path):
            continue
            
        if filename.startswith('~$') or filename.startswith('.'):
            continue
            
        if not filename.lower().endswith(SUPPORTED_EXTENSIONS):
            continue

        print(f"[-] Processing: {filename}")
        
        try:
            s3_path = upload_to_s3(file_path)
            doc_id = db.register_document(filename, s3_path)
            
            page_iterator = get_combined_page_iterator(file_path)
            results = process_and_search(filename, page_iterator, phrases)
            
            db.save_search_results(doc_id, results)
            print(f"    [OK] DB updated for {filename}")
            
        except Exception as e:
            print(f"    [X] Error on {filename}: {e}")

    db.close()
    
    generate_final_report(DB_CONFIG)
    print("\n[*] Pipeline Finished Successfully.")

if __name__ == "__main__":
    main()