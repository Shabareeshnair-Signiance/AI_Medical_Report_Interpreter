import os
import re
import hashlib

from logger_config import logger
from storage.database import check_existing_report
from processing.pdf_reader import read_pdf


class ValidationAgent:

    def __init__(self, allowed_extensions=None, max_file_size_mb=10):
        self.allowed_extensions = allowed_extensions or [".pdf"]
        self.max_file_size_mb = max_file_size_mb

    # -------- TEXT NORMALIZATION --------
    def normalize_text(self, text: str) -> str:
        text = re.sub(r'\s+', ' ', text)
        text = text.replace(" - ", ": ")
        text = text.replace("–", ":")
        text = text.replace("—", ":")
        text = re.sub(r'P\s*I\s*D', 'PID', text, flags=re.IGNORECASE)
        return text.strip()

    # -------- EXTRACT USER DETAILS --------
    def extract_user_details(self, text: str) -> dict:
        data = {
            "user_name": None,
            "reg_no": None,
            "lab_no": None,
            "pid": None,
            "patient_id": None,
            "accession_no": None,
            "visit_no": None
        }

        text = self.normalize_text(text)

        match = re.search(r'\b([A-Z][a-z]+\s[A-Z][a-z]+)\b', text)
        if match:
            data["user_name"] = match.group(1)

        patterns = {
            "reg_no": r'(?:Reg\s*No|Registration\s*No)\s*[:\-]?\s*(\w+)',
            "lab_no": r'(?:Lab\s*No)\s*[:\-]?\s*(\w+)',
            "pid": r'(?:PID)\s*[:\-]?\s*(\d+)'
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data[key] = match.group(1).strip()

        return data

    # -------- HASH GENERATION --------
    def generate_file_hash(self, file_path: str) -> str:
        try:
            sha256 = hashlib.sha256()

            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256.update(chunk)

            return sha256.hexdigest()

        except Exception as e:
            logger.error(f"Hash generation failed: {str(e)}")
            return None

    # -------- MAIN VALIDATION --------
    def validate(self, file_path: str) -> dict:

        logger.info("Starting validation process")

        result = {
            "is_valid": True,
            "errors": [],
            "file_hash": None,
            "is_duplicate": False,
            "existing_result": None,
            "extracted_data": {},
            "identifier_used": None
        }

        # -------- FILE CHECKS --------
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.allowed_extensions:
            result["is_valid"] = False
            result["errors"].append("Invalid file type.")

        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            result["is_valid"] = False
            result["errors"].append("File is empty.")

        # -------- EXTRACT TEXT --------
        if result["is_valid"]:
            text = read_pdf(file_path)

            extracted = self.extract_user_details(text)
            result["extracted_data"] = extracted

            if not extracted.get("user_name"):
                result["errors"].append("User name not found in report.")

        # -------- HASH AND DUPLICATE CHECK --------
        if result["is_valid"]:

            file_hash = self.generate_file_hash(file_path)
            result["file_hash"] = file_hash

            # DEBUG (keep temporarily)
            print("HASH:", file_hash)

            existing = check_existing_report(file_hash)

            if existing:
                print("DUPLICATE FOUND")
                result["is_duplicate"] = True
                result["existing_result"] = existing
            else:
                print("NEW FILE")

        logger.info(f"Validation result: {result}")

        return result