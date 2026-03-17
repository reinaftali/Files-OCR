
# Files-OCR 

An end-to-end automated document processing pipeline that extracts text from various file formats, performs regex-based phrase searching (optimized for Hebrew and hidden PDF characters), uploads files to S3/MinIO, logs results to a PostgreSQL database, and generates a final CSV  report.

## 🚀 Features
* **Multi-Format Support**: Native parsing for `.pdf`, `.docx`, `.doc`, `.xlsx`, `.xls`, and `.csv`.
* **Smart OCR Fallback**: Automatically detects scanned PDFs (images) and routes them through Tesseract OCR.
* **Legacy Windows File Conversion**: Automatically converts legacy `.doc` and `.xls` files using hidden MS Office COM instances.
* **Robust Search Engine**: Built-in Regex engine handles broken words, hidden characters, and multiline phrases, ensuring high accuracy (especially for RTL languages like Hebrew).
* **S3/MinIO Integration**: Uploads raw documents to cloud storage and tracks their URIs.
* **PostgreSQL Logging**: Tracks processed documents and saves detailed search matches.
* **Automated Reporting**: Generates a dynamic CSV pivot table summarizing findings per document.

## 📋 Prerequisites
* **Python 3.9+**
* **PostgreSQL** database up and running.
* **MinIO/S3** instance up and running.
* **Microsoft Office** (Word and Excel) installed on the host machine (Required ONLY if you need to process legacy `.doc` and `.xls` files via `win32com`).

## 🛠️ Installation & Setup

### 1. Clone the Repository
```bash
git clone [https://github.com/reinaftali/Files-OCR.git]
cd Files-OCR
```

### 2. Set Up the Virtual Environment
It is highly recommended to run this project inside an isolated virtual environment.

**On Windows:**
```bash
python -m venv .venv
.\.venv\Scripts\activate
```

### 3. Install Dependencies
Once your virtual environment is activated, install the required Python packages:
```bash
pip install -r requirements.txt
```

### 4. Install Tesseract OCR
This project uses Tesseract for OCR processing on scanned PDFs. 
An executable installer is included in the root of this repository (`tesseract-ocr-w64-setup-5.5.0.20241111.exe`). Please run this file to install Tesseract on your Windows system. 

*Note: The script expects Tesseract to be installed at `C:\Program Files\Tesseract-OCR\tesseract.exe`. If you install it elsewhere, update the path in `document_parsers/ocr_engine.py`.*

### 5. Environment Variables Configuration
The project relies on environment variables for sensitive configurations (Database, S3, and target phrases).

1. Locate the `.env.example` file in the root directory.
2. Copy it and rename the new file to `.env`:
   * **Windows:** `copy .env.example .env`
3. Open the `.env` file and fill in your actual credentials and settings:

```env
# Database Configuration
DB_HOST=localhost
DB_NAME=your_db_name
DB_USER=your_username
DB_PASSWORD=your_password
DB_PORT=5432

# MinIO/S3 Configuration
MINIO_ENDPOINT=http://localhost:9000
MINIO_ACCESS_KEY=your_access_key
MINIO_SECRET_KEY=your_secret_key
MINIO_BUCKET=raw-documents

# Folders
TEST_DOCS_FOLDER=C:\Path\To\Your\Documents

# Search Phrases (comma-separated list, no spaces around commas)
SEARCH_PHRASES=phrase1,phrase2,phrase3
```

## 🖥️ Usage

Once everything is configured and your database/S3 instances are running, execute the main pipeline:

```bash
python main.py
```

**Pipeline Workflow:**
1. Validates `.env` variables and ensures the target folder exists.
2. Checks/Creates the designated MinIO bucket.
3. Iterates through the supported documents in the `TEST_DOCS_FOLDER`.
4. Uploads each document to MinIO.
5. Registers the document in the `documents` PostgreSQL table.
6. Parses the document (Triggering OCR if it's a scanned PDF).
7. Searches for the configured `SEARCH_PHRASES`.
8. Saves the match results to the `phrase_matches` PostgreSQL table.
9. Exports a final `final_report.csv` pivot table to your root directory.


*(Note: Any Kubernetes deployment files found in the `k8s/` directory are maintained separately and are not required to run the Python application locally).*
