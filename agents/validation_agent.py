import os
import re

from logger_config import logger
from storage.database import check_existing_report
from processing.pdf_reader import read_pdf


class ValidationAgent:

    def __init__(self, allowed_extensions=None, max_file_size_mb=10):
        self.allowed_extensions = allowed_extensions or [".pdf"]
        self.max_file_size_mb = max_file_size_mb

    def normalize_text(self, text: str) -> str:
        text = re.sub(r'\s+', ' ', text)
        text = text.replace(" - ", ": ")
        text = text.replace("–", ":")
        text = text.replace("—", ":")
        text = re.sub(r'P\s*I\s*D', 'PID', text, flags=re.IGNORECASE)
        return text.strip()

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
            "reg_no": r'(Reg\s*No)\s*[:\-]?\s*(\w+)',
            "lab_no": r'(Lab\s*No)\s*[:\-]?\s*(\w+)',
            "pid": r'(PID)\s*[:\-]?\s*(\d+)'
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data[key] = match.group(2)

        return data

    def validate(self, file_path: str, file_hash: str) -> dict:

        logger.info("Starting validation process")

        result = {
            "is_valid": True,
            "errors": [],
            "file_hash": file_hash,
            "is_duplicate": False,
            "existing_result": None,
            "extracted_data": {},
            "identifier_used": None
        }

        # File checks
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.allowed_extensions:
            result["is_valid"] = False
            result["errors"].append("Invalid file type.")

        if os.path.getsize(file_path) == 0:
            result["is_valid"] = False
            result["errors"].append("File is empty.")

        # Extract text
        if result["is_valid"]:
            text = read_pdf(file_path)

            extracted = self.extract_user_details(text)
            result["extracted_data"] = extracted

            if not extracted.get("user_name"):
                result["errors"].append("User name not found")

        # DUPLICATE CHECK (CORRECT)
        if result["is_valid"]:
            existing = check_existing_report(file_hash)

            if existing:
                result["is_duplicate"] = True
                result["existing_result"] = existing

        return result