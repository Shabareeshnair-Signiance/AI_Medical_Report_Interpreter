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

        # Added patient_id and report_date to support TrendAgent logic
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS patient_reports (
            file_hash TEXT PRIMARY KEY,
            patient_id TEXT,          -- PID, LabNo, or UHID
            patient_name TEXT,        -- Fallback identity
            report_date TEXT,         -- Essential for chronological trends
            medical_data TEXT,        -- JSON string of lab results
            llm_insight TEXT          -- The Doctor-specific clinical analysis
        )
        """)
        
        # Indexing for lightning-fast history lookups when a patient returns
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_patient_history ON patient_reports(patient_id, patient_name)")

        conn.commit()
        conn.close()
        logger.info("Doctor's History Database initialized successfully")
    except Exception as e:
        logger.error(f"History Database initialization failed: {str(e)}")

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

def get_history_for_patient(pid=None, name=None):
    """Retrieves all previous reports for the Trend Agent to compare against."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Query history based on 'Unbreakable' identity logic
        if pid:
            cursor.execute("SELECT medical_data, report_date FROM patient_reports WHERE patient_id = ? ORDER BY report_date ASC", (pid,))
        else:
            cursor.execute("SELECT medical_data, report_date FROM patient_reports WHERE patient_name = ? ORDER BY report_date ASC", (name,))

        rows = cursor.fetchall()
        conn.close()

        history = []
        for row in rows:
            # We reconstruct the report structure expected by the Trend Agent
            data = {
                "lab_results": json.loads(row[0]),
                "report_date": row[1],
                "patient_id": pid,
                "patient_name": name
            }
            history.append(data)
        
        return history
    except Exception as e:
        logger.error(f"Failed to fetch history: {str(e)}")
        return []

def get_report_scenario(file_hash, extracted_data):
    """
    PRODUCTION LOGIC: Determines which scenario the current report falls into.
    Returns: (scenario_name, history_list)
    """
    pid = extracted_data.get("pid") or extracted_data.get("lab_no")
    name = extracted_data.get("patient_name", "").lower().strip()
    report_date = extracted_data.get("report_date")

    # 1. Check for Duplicate File (Scenario 4 Part A)
    if check_file_exists(file_hash):
        return "EXISTS_IN_DB", []

    # 2. Get history to check for other scenarios
    history = get_history_for_patient(pid=pid, name=name)

    if not history:
        # Scenario 1 & 2: New User or No history
        return "NEW_PATIENT", []

    # 3. Check for Duplicate Date (Scenario 4 Part B: Same report but different file)
    existing_dates = [h.get('report_date') for h in history]
    if report_date in existing_dates:
        return "SAME_DATE_REPORT", history

    # 4. Scenario 3: Success, history exists for comparison
    return "HISTORY_AVAILABLE", history

def save_patient_trend_data(file_hash, extracted_data, trend_result):
    """Saves the extraction and trend insights into history."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        pid = extracted_data.get("pid") or extracted_data.get("lab_no")
        name = extracted_data.get("patient_name", "").lower().strip()
        report_date = extracted_data.get("report_date")
        
        # We store just the results list to keep the DB light
        medical_json = json.dumps(extracted_data.get("lab_results", []))
        insight = trend_result.get("llm_insight", "")

        cursor.execute("""
        INSERT OR REPLACE INTO patient_reports
        (file_hash, patient_id, patient_name, report_date, medical_data, llm_insight)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (file_hash, pid, name, report_date, medical_json, insight))

        conn.commit()
        conn.close()
        logger.info(f"Report for {name} ({report_date}) committed to history.")
    except Exception as e:
        logger.error(f"Failed to save trend data: {str(e)}")