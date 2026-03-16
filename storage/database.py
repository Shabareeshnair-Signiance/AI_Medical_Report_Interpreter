import sqlite3
import hashlib
import json
import os
from logger_config import logger

# path of sqlite database
DB_PATH = "data/medical_reports.db"


def init_database():
    """
    Create database and table if it doesn't exist.
    """

    try:

        # make sure data folder exists
        os.makedirs("data", exist_ok=True)

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # create table for storing report outputs
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


def generate_file_hash(file_path):
    """
    Generate SHA256 hash of uploaded PDF file.
    Used to detect duplicate reports.
    """

    try:

        sha256 = hashlib.sha256()

        # read file in chunks
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)

        return sha256.hexdigest()

    except Exception as e:
        logger.error(f"Hash generation failed: {str(e)}")
        return None


def check_existing_report(file_hash):
    """
    Check whether the report already exists in database.
    """

    try:

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT medical_data, analysis, explanation, guidance
            FROM reports
            WHERE file_hash = ?
            """,
            (file_hash,)
        )

        result = cursor.fetchone()

        conn.close()

        # if report already exists return stored results
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
    """
    Save generated AI response into database.
    """

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