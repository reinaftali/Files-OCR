import os
import json
import uuid
import boto3
import pandas as pd
import psycopg2
from dotenv import load_dotenv
from document_parsers.router import get_combined_page_iterator, SUPPORTED_EXTENSIONS
from search_engine import process_and_search
from db_manager import DatabaseManager

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": int(os.getenv("DB_PORT", 5432))
}

MINIO_CONFIG = {
    'endpoint_url': os.getenv("MINIO_ENDPOINT"),
    'aws_access_key_id': os.getenv("MINIO_ACCESS_KEY"),
    'aws_secret_access_key': os.getenv("MINIO_SECRET_KEY")
}

BUCKET_NAME = 'raw-documents'
FOLDER_PATH = os.getenv("TEST_DOCS_FOLDER")

s3_client = boto3.client('s3', **MINIO_CONFIG)

def upload_to_s3(file_path):
    filename = os.path.basename(file_path)
    file_extension = os.path.splitext(filename)[1].lower().replace('.', '')
    object_name = f"{uuid.uuid4().hex}.{file_extension}"
    
    s3_client.upload_file(file_path, BUCKET_NAME, object_name)
    return f"s3://{BUCKET_NAME}/{object_name}"

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
    raw_phrases = os.getenv("SEARCH_PHRASES")
    if not raw_phrases:
        print("[!] Error: 'SEARCH_PHRASES' is not set in your .env file.")
        print("    Please add: SEARCH_PHRASES=phrase1,phrase2... to your .env")
        return # Stop, phrases are mandatory

    phrases = [p.strip() for p in raw_phrases.split(",") if p.strip()]

    # check the list isn't just empty commas (e.g., ",,,")
    if not phrases:
        print("[!] Error: 'SEARCH_PHRASES' was found but contains no valid phrases.")
        return
        
    db = DatabaseManager(DB_CONFIG)
    
    print(f"[*] Starting End-to-End Pipeline on {FOLDER_PATH}...\n")

    if not os.path.exists(FOLDER_PATH):
        print(f"[X] Error: Folder '{FOLDER_PATH}' does not exist.")
        return

    existing_buckets = [b['Name'] for b in s3_client.list_buckets().get('Buckets', [])]
    if BUCKET_NAME not in existing_buckets:
        s3_client.create_bucket(Bucket=BUCKET_NAME)

    for filename in os.listdir(FOLDER_PATH):
        file_path = os.path.join(FOLDER_PATH, filename)
        
        if not os.path.isfile(file_path) or filename.startswith(('$', '.')):
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
            print(f"    [OK] Finished: {filename}")
            
        except Exception as e:
            print(f"    [X] Error on {filename}: {e}")

    db.close()
    
    generate_final_report(DB_CONFIG)
    print("\n[*] Pipeline Finished Successfully.")

if __name__ == "__main__":
    main()