import sqlite3
import hashlib
import json
import os
from logger_config import logger

# Storing in the same 'data' folder as your existing project
DB_PATH = os.path.join(os.getcwd(), "data", "medical_history.db")

def init_history_database():
    """Initializes a database specifically designed for tracking patient trends over time."""
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
        
        # Ensure column exists for older DB versions
        cursor.execute("PRAGMA table_info(patient_reports)")
        columns = [column[1] for column in cursor.fetchall()]
        if "clinical_suggestion" not in columns:
            cursor.execute("ALTER TABLE patient_reports ADD COLUMN clinical_suggestion TEXT")
            logger.info("Added clinical_suggestion column to existing database.")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_patient_history ON patient_reports(patient_id, patient_name)")

        conn.commit()
        conn.close()
        logger.info("Doctor's History Database initialized successfully")
    except Exception as e:
        logger.error(f"History Database initialization failed: {str(e)}")

def get_history_for_patient(pid=None, name=None):
    """Retrieves all previous reports for the Trend Agent to compare against."""
    try:
        conn = sqlite3.connect(DB_PATH)
        # Allows accessing columns by name
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()

        # Clean the name for better matching
        clean_name = name.lower().strip() if name else None

        # FIX: Select ALL columns so the TrendAgent has the data it needs for Identity Checks
        if pid:
            cursor.execute("""
                SELECT medical_data, report_date, patient_id, patient_name 
                FROM patient_reports 
                WHERE patient_id = ? 
                ORDER BY report_date ASC
            """, (pid,))
        else:
            cursor.execute("""
                SELECT medical_data, report_date, patient_id, patient_name 
                FROM patient_reports 
                WHERE LOWER(patient_name) = ? 
                ORDER BY report_date ASC
            """, (clean_name,))

        rows = cursor.fetchall()
        conn.close()

        history = []
        for row in rows:
            # FIX: Ensure lab_results is parsed from JSON string back to a list
            history.append({
                "lab_results": json.loads(row["medical_data"]),
                "report_date": row["report_date"],
                "pid": row["patient_id"],
                "patient_name": row["patient_name"]
            })
        
        return history
    except Exception as e:
        logger.error(f"Failed to fetch history: {str(e)}")
        return []

def save_patient_trend_data(file_hash, extracted_data, trend_result):
    """Saves the extraction, trend insights, and clinical suggestions into history."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        pid = extracted_data.get("pid") or extracted_data.get("lab_no")
        name = extracted_data.get("patient_name", "").strip()
        report_date = extracted_data.get("report_date")
        
        # Save the lab results as a JSON string
        medical_json = json.dumps(extracted_data.get("lab_results", []))
        
        # 1. Capture Trend Agent Output
        insight = trend_result.get("trend_insight", "")
        
        # 2. Capture Symlink Agent Output (Using the key that matches your App/UI)
        suggestion = trend_result.get("clinical_suggestion", "")

        cursor.execute("""
        INSERT OR REPLACE INTO patient_reports
        (file_hash, patient_id, patient_name, report_date, medical_data, llm_insight, clinical_suggestion)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (file_hash, str(pid), name, report_date, medical_json, insight, suggestion))

        conn.commit()
        conn.close()
        logger.info(f"Analysis for {name} ({report_date}) saved to Database.")
    except Exception as e:
        logger.error(f"Failed to save trend data: {str(e)}")

def check_file_exists(file_hash):
    """Checks if this exact file has already been processed using its hash."""
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