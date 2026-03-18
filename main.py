import os
import json
import uuid
import boto3
import pandas as pd
import psycopg2
import itertools
from dotenv import load_dotenv
from document_parsers.router import get_combined_page_iterator, SUPPORTED_EXTENSIONS
from search_engine import process_and_search, check_subject_relevance
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

SUBJECT_HEADER = os.getenv("SUBJECT_HEADER")
SUBJECT_KEYWORD = os.getenv("SUBJECT_KEYWORD")

s3_client = boto3.client('s3', **MINIO_CONFIG)

def upload_to_s3(file_path):
    filename = os.path.basename(file_path)
    file_extension = os.path.splitext(filename)[1].lower().replace('.', '')
    object_name = f"{uuid.uuid4().hex}.{file_extension}"
    
    s3_client.upload_file(file_path, BUCKET_NAME, object_name)
    return f"s3://{BUCKET_NAME}/{object_name}"

def generate_final_report(db_config, intersection_cats, output_csv_path="final_report.csv"):
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

    # Pivot: Creates a column for each category or specific word we searched exactly as named in the dict
    pivot_df = df.pivot_table(
        index='file_name', 
        columns='phrase', 
        values='is_found', 
        aggfunc='first'
    ).reset_index()

    # --- Create the dynamic intersection column ---
    if intersection_cats and len(intersection_cats) == 2:
        cat1, cat2 = intersection_cats
        
        # Check if both columns exist in the DB results to avoid KeyError
        if cat1 in pivot_df.columns and cat2 in pivot_df.columns:
            # Dynamically name the column
            intersection_col_name = f"{cat1} ו{cat2}"
            
            # The intersection is True only if BOTH categories are True
            pivot_df[intersection_col_name] = pivot_df[cat1] & pivot_df[cat2]

    # Save to CSV using utf-8-sig to ensure Hebrew characters display correctly in Excel
    pivot_df.to_csv(output_csv_path, index=False, encoding='utf-8-sig')
    print(f"    [V] Report saved to: {output_csv_path}")

def main():
    #Validate mandatory subject header and keyword
    if not SUBJECT_HEADER:
        print("[!] Error: 'SUBJECT_HEADER' is not set in your .env file.")
        return
        
    if not SUBJECT_KEYWORD:
        print("[!] Error: 'SUBJECT_KEYWORD' is not set in your .env file.")
        return

    # Parse the dynamic search categories from JSON in .env
    raw_categories = os.getenv("SEARCH_CATEGORIES")
    if not raw_categories:
        print("[!] Error: 'SEARCH_CATEGORIES' is not set in your .env file.")
        return
        
    try:
        SEARCH_CATEGORIES = json.loads(raw_categories)
    except json.JSONDecodeError as e:
        print(f"[!] Error: 'SEARCH_CATEGORIES' in .env is not valid JSON. Exception: {e}")
        return

    # 3. Parse intersection categories for the final report
    raw_intersection = os.getenv("INTERSECTION_CATEGORIES", "")
    intersection_cats = [c.strip() for c in raw_intersection.split(",") if c.strip()]
        
    db = DatabaseManager(DB_CONFIG)
    print(f"[*] Starting End-to-End Pipeline on {FOLDER_PATH}...\n")

    if not os.path.exists(FOLDER_PATH):
        print(f"[X] Error: Folder '{FOLDER_PATH}' does not exist.")
        return

    # Ensure the target bucket exists 
    existing_buckets = [b['Name'] for b in s3_client.list_buckets().get('Buckets', [])]
    if BUCKET_NAME not in existing_buckets:
        s3_client.create_bucket(Bucket=BUCKET_NAME)

    for filename in os.listdir(FOLDER_PATH):
        file_path = os.path.join(FOLDER_PATH, filename)
        
        # Skip directories and hidden/temporary files
        if not os.path.isfile(file_path) or filename.startswith(('$', '.')):
            continue
            
        # Enforce whitelist of supported extensions
        if not filename.lower().endswith(SUPPORTED_EXTENSIONS):
            continue

        print(f"[-] Processing: {filename}")
        
        try:
            # Always upload to S3 and register in DB regardless of content
            s3_path = upload_to_s3(file_path)
            doc_id = db.register_document(filename, s3_path)
            
            # Check extension - skip subject verification for Tabular data
            ext = filename.lower().split('.')[-1]
            if ext in ['csv', 'xlsx', 'xls']:
                page_iterator = get_combined_page_iterator(file_path)
                results = process_and_search(filename, page_iterator, SEARCH_CATEGORIES)
                db.save_search_results(doc_id, results)
                print(f"    [OK] Tabular file processed fully: {filename}")
                continue

            # PDF/Word Smart Extraction - Early Exit Logic
            page_iterator = get_combined_page_iterator(file_path)
            consumed_pages = []
            overlap_buffer = ""
            is_relevant = False
            subject_found = False
            
            for page_num, chunk in enumerate(page_iterator):
                consumed_pages.append(chunk)
                text_to_search = overlap_buffer + chunk
                
                if not subject_found:
                    # Pass BOTH the dynamic header and keyword to the validation function
                    found_subj, found_key = check_subject_relevance(text_to_search, SUBJECT_HEADER, SUBJECT_KEYWORD)
                    if found_subj:
                        subject_found = True
                        if found_key:
                            is_relevant = True
                        break # Stop checking for subject once we found the header
                        
                # Give up if we checked the first 3 chunks (pages) and didn't find the header
                if page_num >= 2:
                    break
                    
                overlap_buffer = chunk[-150:] if len(chunk) > 150 else chunk

            # Skip searching the rest of the document if the keyword wasn't in the subject
            if not is_relevant:
                print(f"    [!] Skipped: Keyword '{SUBJECT_KEYWORD}' not found under '{SUBJECT_HEADER}'. (File stored in S3)")
                continue 

            # If relevant, reconnect the consumed pages with the rest of the document
            full_iterator = itertools.chain(consumed_pages, page_iterator)
            
            # Run the search engine with the JSON dictionary
            results = process_and_search(filename, full_iterator, SEARCH_CATEGORIES)
            db.save_search_results(doc_id, results)
            print(f"    [OK] Finished: {filename}")
            
        except Exception as e:
            print(f"    [X] Error on {filename}: {e}")

    db.close()
    
    generate_final_report(DB_CONFIG, intersection_cats)
    print("\n[*] Pipeline Finished Successfully.")

if __name__ == "__main__":
    main()