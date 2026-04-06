import sqlite3
import hashlib
import json
import os
from logger_config import logger

DB_PATH = os.path.join(os.getcwd(), "data", "medical_history.db")


def _get_fuzzy_clean_name(name):
    """Tier 3: Normalizes names by removing middle initials and extra dots."""
    import re
    if not name: return "unknown"
    # Convert to lowercase and remove dots (e.g., 'M.' -> 'M')
    name = name.lower().replace(".", "").strip()
    # Remove single character middle initials (e.g., 'yash m patel' -> 'yash patel')
    # This regex looks for a single letter surrounded by spaces
    name = re.sub(r'\s[a-z]\s', ' ', name)
    # Remove all spaces for the final hash key
    return name.replace(" ", "")


def generate_internal_uid(name, age=None, dob=None, report_date_str=None):
    """Hybrid UID Generator: Tier 1 (Full) -> Tier 2 (Partial) -> Tier 3 (Fuzzy)"""
    try:
        # TIER 3: Use the fuzzy cleaner to handle 'Yash M. Patel' vs 'Yash Patel'
        clean_name = _get_fuzzy_clean_name(name)
        
        birth_year = "0000" 

        # TIER 2: Match based on Birth Year if PID/DOB is messy
        if dob and len(str(dob)) >= 4:
            birth_year = str(dob)[:4]
        elif age and report_date_str:
            try:
                report_year = int(str(report_date_str)[:4])
                # Ensure age is numeric before subtraction
                clean_age = int(re.search(r'\d+', str(age)).group())
                birth_year = str(report_year - clean_age)
            except:
                pass

        # TIER 1: The Final Identity String
        identity_string = f"{clean_name}-{birth_year}"
        uid = hashlib.md5(identity_string.encode()).hexdigest()
        
        logger.info(f"Hybrid UID Generated: {uid} for {name} (Birth Year: {birth_year})")
        return uid
    except Exception as e:
        logger.error(f"UID Generation failed: {e}")
        return name.lower().strip().replace(" ", "")
    
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


def get_history_for_patient(pid=None, name=None):
    """Retrieves all previous reports for the table and trend agent."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()

        clean_name = name.lower().strip() if name else None

        # Added llm_insight as 'summary' so the table has text to show
        query = """
            SELECT medical_data, report_date, patient_id, patient_name, llm_insight
            FROM patient_reports 
            WHERE patient_id = ? 
               OR LOWER(patient_name) = ? 
               OR patient_id = (SELECT patient_id FROM patient_reports WHERE LOWER(patient_name) LIKE ? LIMIT 1)
            ORDER BY report_date ASC
        """

        # Using a wildcard match for the fuzzy name
        fuzzy_search = f"%{clean_name}%"
        cursor.execute(query, (str(pid), clean_name, fuzzy_search))

        rows = cursor.fetchall()
        conn.close()

        history = []
        for row in rows:
            history.append({
                "lab_results": json.loads(row["medical_data"]),
                "report_date": row["report_date"],
                "pid": row["patient_id"],
                "patient_name": row["patient_name"],
                "lab_name": "Stored Report", # Placeholder since lab_name isn't in your schema yet
                "summary": row["llm_insight"][:100] + "..." if row["llm_insight"] else "No summary available"
            })
        
        return history
    except Exception as e:
        logger.error(f"Failed to fetch history: {str(e)}")
        return []

def save_patient_trend_data(file_hash, extracted_data, trend_result):
    """Saves the AI results using the file_hash as the unique key."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        raw_pid = extracted_data.get("pid") or extracted_data.get("lab_no") or "Unknown"
        name = extracted_data.get("patient_name", "").strip()
        report_date = extracted_data.get("report_date")
        age = extracted_data.get("age")
        dob = extracted_data.get("dob")

        # Generating Permanent Internal ID
        # this links Report A (LabID 101) and Report B (LabID 999) to the same name
        internal_pid = generate_internal_uid(name, age, dob, report_date)

        medical_json = json.dumps(extracted_data.get("lab_results", []))
        insight = trend_result.get("trend_insight", "")
        suggestion = trend_result.get("clinical_suggestion", "")

        cursor.execute("""
        INSERT OR REPLACE INTO patient_reports
        (file_hash, patient_id, patient_name, report_date, medical_data, llm_insight, clinical_suggestion)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (file_hash, str(internal_pid), name, report_date, medical_json, insight, suggestion))

        conn.commit()
        conn.close()

        # logging both the original Lab ID and the new Internal UID so i can track the change
        logger.info(f"Report (lab ID: {raw_pid}) successfully mapped to Internal UID: {internal_pid}")
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
        # FIX: Added patient_name, patient_id, and report_date to the SELECT
        cursor.execute("""
            SELECT 
                llm_insight, 
                clinical_suggestion, 
                patient_name, 
                patient_id, 
                report_date 
            FROM patient_reports 
            WHERE file_hash = ?
        """, (file_hash,))
        
        row = cursor.fetchone()
        conn.close()
        
        # This now returns a tuple of 5 items, preventing the Index Error
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

    # Calculating UID to search for history across different Lab IDs
    internal_id = generate_internal_uid(name, extracted_data.get("age"), extracted_data.get("dob"), report_date)
    history = get_history_for_patient(pid=pid, name=name)

    if not history:
        return "NEW_PATIENT", []

    existing_dates = [h.get('report_date') for h in history]
    if report_date in existing_dates:
        return "SAME_DATE_REPORT", history

    return "HISTORY_AVAILABLE", history