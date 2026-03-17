import os
import hashlib
import re

from logger_config import logger
from storage.database import check_existing_report
from processing.pdf_reader import read_pdf   


class ValidationAgent:
    def __init__(self, allowed_extensions=None, max_file_size_mb=10):
        self.allowed_extensions = allowed_extensions or [".pdf"]
        self.max_file_size_mb = max_file_size_mb

    # -------- TEXT NORMALIZATION --------
    def normalize_text(self, text: str) -> str:
        text = re.sub(r'\s+', ' ', text)  # remove extra spaces
        text = text.replace(" - ", ": ")
        text = text.replace("–", ":")
        text = text.replace("—", ":")

        # Fix broken PID like "P I D"
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

        # -------- NAME (SMART EXTRACTION) --------
        match = re.search(
            r'\b([A-Z][a-z]+(?:\s[A-Z]\.)?\s[A-Z][a-z]+)\b',
            text
        )

        if match:
            data["user_name"] = match.group(1)

        # -------- IDENTIFIERS --------
        patterns = {
            "reg_no": r'(?:Reg\s*No|Registration\s*No)\s*[:\-]?\s*(\w+)',
            "lab_no": r'(?:Lab\s*No)\s*[:\-]?\s*(\w+)',
            "pid": r'(?:PID)\s*[:\-]?\s*(\d+)',
            "patient_id": r'(?:Patient\s*ID)\s*[:\-]?\s*(\w+)',
            "accession_no": r'(?:Accession\s*No?)\s*[:\-]?\s*([\w\-]+)',
            "visit_no": r'(?:Visit\s*No|Visit\s*Number)\s*[:\-]?\s*([\w\-]+)'
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data[key] = match.group(1).strip()

        return data

    # -------- HASH --------
    def generate_file_hash(self, file_path: str) -> str:
        try:
            hasher = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            logger.error(f"Error generating file hash: {str(e)}")
            return None

    # -------- VALIDATE USER --------
    def validate_user(self, data: dict) -> list:
        errors = []

        if not data.get("user_name"):
            errors.append("User name not found in report.")

        identifiers = [
            data.get("reg_no"),
            data.get("lab_no"),
            data.get("pid"),
            data.get("patient_id"),
            data.get("accession_no"),
            data.get("visit_no"),
        ]

        if not any(identifiers):
            errors.append("No valid identifier found (Reg No / Lab No / PID / etc).")

        return errors

    # -------- FILE CHECKS --------
    def validate_extension(self, file_path: str) -> bool:
        ext = os.path.splitext(file_path)[1].lower()
        return ext in self.allowed_extensions

    def validate_size(self, file_path: str) -> bool:
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        return size_mb <= self.max_file_size_mb

    def validate_not_empty(self, file_path: str) -> bool:
        return os.path.getsize(file_path) > 0

    # -------- MAIN PIPELINE --------
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

        # File checks
        if not self.validate_extension(file_path):
            result["is_valid"] = False
            result["errors"].append("Invalid file type.")

        if not self.validate_size(file_path):
            result["is_valid"] = False
            result["errors"].append("File too large.")

        if not self.validate_not_empty(file_path):
            result["is_valid"] = False
            result["errors"].append("File is empty.")

        # -------- FIX IS HERE --------
        if result["is_valid"]:
            text = read_pdf(file_path)   

            logger.info(f"DEBUG TEXT: {text[:500]}")  

            extracted = self.extract_user_details(text)
            result["extracted_data"] = extracted

            user_errors = self.validate_user(extracted)
            if user_errors:
                result["is_valid"] = False
                result["errors"].extend(user_errors)

            # Identifier priority
            for key in ["reg_no", "lab_no", "pid", "patient_id", "accession_no", "visit_no"]:
                if extracted.get(key):
                    result["identifier_used"] = f"{key}: {extracted.get(key)}"
                    break

        # Hash check
        if result["is_valid"]:
            file_hash = self.generate_file_hash(file_path)
            result["file_hash"] = file_hash

            existing = check_existing_report(file_hash)
            if existing:
                result["is_duplicate"] = True
                result["existing_result"] = existing

        logger.info(f"Validation result: {result}")
        return result