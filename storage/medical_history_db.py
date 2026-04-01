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
            data = json.loads(row[0])
            data['report_date'] = row[1]
            history.append(data)
        
        return history
    except Exception as e:
        logger.error(f"Failed to fetch history: {str(e)}")
        return []

def save_patient_trend_data(file_hash, extracted_data, trend_result):
    """Saves the new extraction and the trend analysis into the history store."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Prepare values for the Unbreakable identity match
        pid = extracted_data.get("pid") or extracted_data.get("lab_no")
        name = extracted_data.get("patient_name", "").lower().strip()
        report_date = extracted_data.get("report_date")
        
        # Serialize the medical data JSON
        medical_json = json.dumps(extracted_data.get("lab_results", []))
        # Store the LLM clinical insight from the Trend Agent
        insight = trend_result.get("llm_insight", "")

        cursor.execute("""
        INSERT OR REPLACE INTO patient_reports
        (file_hash, patient_id, patient_name, report_date, medical_data, llm_insight)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (file_hash, pid, name, report_date, medical_json, insight))

        conn.commit()
        conn.close()
        logger.info(f"Trend data for {name} saved successfully")
    except Exception as e:
        logger.error(f"Failed to save trend data: {str(e)}")