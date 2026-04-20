import sqlite3
import hashlib
import json
import os
from logger_config import logger

DB_PATH = os.path.join(os.getcwd(), "data", "medical_reports.db")


def init_database():
    try:
        os.makedirs("data", exist_ok=True)

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            file_hash TEXT PRIMARY KEY,
            medical_data TEXT,
            analysis TEXT,
            explanation TEXT,
            guidance TEXT
        )
        """)

        conn.commit()
        conn.close()

        logger.info("Database initialized successfully")

    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")


# SINGLE SOURCE OF TRUTH FOR HASH
def generate_file_hash_from_bytes(file_bytes):
    try:
        sha256 = hashlib.sha256()
        sha256.update(file_bytes)
        return sha256.hexdigest()
    except Exception as e:
        logger.error(f"Hash generation failed: {str(e)}")
        return None


def check_existing_report(file_hash):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT medical_data, analysis, explanation, guidance
            FROM reports
            WHERE file_hash = ?
        """, (file_hash,))

        result = cursor.fetchone()
        conn.close()

        if result:
            logger.info("Report found in database cache")
            return {
                "medical_data": json.loads(result[0]),
                "analysis": result[1],
                "explanation": result[2],
                "guidance": result[3]
            }

        return None

    except Exception as e:
        logger.error(f"Database lookup failed: {str(e)}")
        return None


def save_report(file_hash, state):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # NEW CODE ADDED: CATCH OCR PATIENT DATA
        try:
            med_data = state.get("medical_data", {})
            if isinstance(med_data, str):
                med_data = json.loads(med_data)
                
            # If the OCR pipeline found a name, save it to the fast cache!
            if isinstance(med_data, dict) and med_data.get("user_name"):
                extracted_for_cache = {"user_name": med_data.get("user_name")}
                id_used = None
                for k in ["reg_no", "pid", "lab_no", "patient_id", "accession_no", "visit_no"]:
                    if med_data.get(k):
                        extracted_for_cache[k] = med_data.get(k)
                        id_used = f"{k}: {med_data.get(k)}"
                        break
                save_validation_cache(file_hash, extracted_for_cache, id_used)
        except Exception as e:
            pass

        # SAFE CONVERSION (ADD THIS LOGIC)
        explanation = state.get("explanation")
        if isinstance(explanation, (list, dict)):
            explanation = json.dumps(explanation)

        guidance = state.get("guidance")
        if isinstance(guidance, (list, dict)):
            guidance = json.dumps(guidance)

        medical_data = state.get("medical_data")
        if isinstance(medical_data, (list, dict)):
            medical_data = json.dumps(medical_data)

        cursor.execute("""
        INSERT OR REPLACE INTO reports
        (file_hash, medical_data, analysis, explanation, guidance)
        VALUES (?, ?, ?, ?, ?)
        """, (
            file_hash,
            # json.dumps(state.get("medical_data")),
            # state.get("analysis"),
            # state.get("explanation"),
            # state.get("guidance")
            medical_data,
            state.get("analysis"),
            explanation,
            guidance
        ))

        conn.commit()
        conn.close()

        logger.info("Report saved into database")

    except Exception as e:
        logger.error(f"Failed to save report: {str(e)}")


# ==========================================
# NEW CODE ADDED: VALIDATION CACHE (FOR SCANNED REPORTS)
# ==========================================
def save_validation_cache(file_hash, extracted_data, identifier_used):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS validation_cache (
            file_hash TEXT PRIMARY KEY,
            extracted_data TEXT,
            identifier_used TEXT
        )
        """)
        cursor.execute("""
        INSERT OR REPLACE INTO validation_cache (file_hash, extracted_data, identifier_used)
        VALUES (?, ?, ?)
        """, (file_hash, json.dumps(extracted_data), identifier_used))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to save validation cache: {str(e)}")

def get_validation_cache(file_hash):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='validation_cache'")
        if not cursor.fetchone(): return None
        
        cursor.execute("SELECT extracted_data, identifier_used FROM validation_cache WHERE file_hash = ?", (file_hash,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                "extracted_data": json.loads(result[0]) if result[0] else {},
                "identifier_used": result[1]
            }
        return None
    except Exception:
        return None