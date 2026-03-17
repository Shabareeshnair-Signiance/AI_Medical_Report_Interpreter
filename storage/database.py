import sqlite3
import hashlib
import json
import os
from logger_config import logger

DB_PATH = "data/medical_reports.db"


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


# 🔥 SINGLE SOURCE OF TRUTH FOR HASH
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

        cursor.execute("""
        INSERT OR REPLACE INTO reports
        (file_hash, medical_data, analysis, explanation, guidance)
        VALUES (?, ?, ?, ?, ?)
        """, (
            file_hash,
            json.dumps(state.get("medical_data")),
            state.get("analysis"),
            state.get("explanation"),
            state.get("guidance")
        ))

        conn.commit()
        conn.close()

        logger.info("Report saved into database")

    except Exception as e:
        logger.error(f"Failed to save report: {str(e)}")