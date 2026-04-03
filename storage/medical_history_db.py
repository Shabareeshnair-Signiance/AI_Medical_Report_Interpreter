import sqlite3
import hashlib
import json
import os
from logger_config import logger

DB_PATH = os.path.join(os.getcwd(), "data", "medical_history.db")

def calculate_file_hash(file_path):
    """Generates a SHA-256 hash to uniquely identify the report file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def init_history_database():
    """Initializes the doctor's history table with the clinical suggestion column."""
    try:
        os.makedirs("data", exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS patient_reports (
            file_hash TEXT PRIMARY KEY,
            patient_id TEXT,          
            patient_name TEXT,        
            report_date TEXT,         
            medical_data TEXT,        
            llm_insight TEXT,         
            clinical_suggestion TEXT  
        )
        """)
        
        # Check if column exists for older databases
        cursor.execute("PRAGMA table_info(patient_reports)")
        columns = [column[1] for column in cursor.fetchall()]
        if "clinical_suggestion" not in columns:
            cursor.execute("ALTER TABLE patient_reports ADD COLUMN clinical_suggestion TEXT")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_patient_history ON patient_reports(patient_id, patient_name)")

        conn.commit()
        conn.close()
        logger.info("Doctor's History Database initialized with Hash support.")
    except Exception as e:
        logger.error(f"DB Init failed: {str(e)}")


def save_patient_trend_data(file_hash, extracted_data, trend_result):
    """Saves the AI results using the file_hash as the unique key."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        pid = extracted_data.get("pid") or extracted_data.get("lab_no")
        name = extracted_data.get("patient_name", "").strip()
        report_date = extracted_data.get("report_date")
        medical_json = json.dumps(extracted_data.get("lab_results", []))
        
        insight = trend_result.get("trend_insight", "")
        suggestion = trend_result.get("clinical_suggestion", "")

        cursor.execute("""
        INSERT OR REPLACE INTO patient_reports
        (file_hash, patient_id, patient_name, report_date, medical_data, llm_insight, clinical_suggestion)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (file_hash, str(pid), name, report_date, medical_json, insight, suggestion))

        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to save data for hash {file_hash}: {str(e)}")


def check_file_exists(file_hash):
    """Uses the hashlib hash to see if we have already processed this file."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT file_hash FROM patient_reports WHERE file_hash = ?", (file_hash,))
        result = cursor.fetchone()
        conn.close()
        return result is not None
    except Exception as e:
        logger.error(f"Hash check failed: {str(e)}")
        return False
    
def get_existing_analysis(file_hash):
    """Checks if we already have the analysis for this specific file in the DB."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # We fetch both the Trend Agent result and the Symlink Agent result
        cursor.execute("""
            SELECT llm_insight, clinical_suggestion 
            FROM patient_reports WHERE file_hash = ?
        """, (file_hash,))
        row = cursor.fetchone()
        conn.close()
        return row if row else None
    except Exception as e:
        logger.error(f"Error fetching existing analysis: {e}")
        return None


def get_report_scenario(file_hash, extracted_data):
    """PRODUCTION LOGIC: Determines which scenario the current report falls into."""
    pid = extracted_data.get("pid") or extracted_data.get("lab_no")
    name = extracted_data.get("patient_name", "").lower().strip()
    report_date = extracted_data.get("report_date")

    if check_file_exists(file_hash):
        return "EXISTS_IN_DB", []

    history = get_history_for_patient(pid=pid, name=name)

    if not history:
        return "NEW_PATIENT", []

    existing_dates = [h.get('report_date') for h in history]
    if report_date in existing_dates:
        return "SAME_DATE_REPORT", history

    return "HISTORY_AVAILABLE", history