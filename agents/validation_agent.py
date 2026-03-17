import os
import hashlib
import re
import pdfplumber

from logger_config import logger
from storage.database import check_existing_report


class ValidationAgent:
    def __init__(self, allowed_extensions=None, max_file_size_mb=10):
        self.allowed_extensions = allowed_extensions or [".pdf"]
        self.max_file_size_mb = max_file_size_mb

    # Extract text from PDF
    def extract_text(self, file_path: str) -> str:
        try:
            text = ""
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
            return text
        except Exception as e:
            logger.error(f"Error extracting PDF text: {e}")
            return ""

    # Extract user details from text (UPDATED)
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

        # Name patterns
        name_patterns = [
            r"Name[:\-]?\s*(.+)",
            r"Patient[:\-]?\s*(.+)"
        ]
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data["user_name"] = match.group(1).strip()
                break

        # Reg No
        reg_match = re.search(r"(Reg\s*No|Registration\s*No)[:\-]?\s*(\w+)", text, re.IGNORECASE)
        if reg_match:
            data["reg_no"] = reg_match.group(2).strip()

        # Lab No
        lab_match = re.search(r"(Lab\s*No)[:\-]?\s*(\w+)", text, re.IGNORECASE)
        if lab_match:
            data["lab_no"] = lab_match.group(2).strip()

        # PID (very common)
        pid_match = re.search(r"(PID)[:\-]?\s*(\w+)", text, re.IGNORECASE)
        if pid_match:
            data["pid"] = pid_match.group(2).strip()

        # Patient ID
        patient_id_match = re.search(r"(Patient\s*ID)[:\-]?\s*(\w+)", text, re.IGNORECASE)
        if patient_id_match:
            data["patient_id"] = patient_id_match.group(2).strip()

        # Accession Number
        accession_match = re.search(r"(Accession)[:\-]?\s*(\S+)", text, re.IGNORECASE)
        if accession_match:
            data["accession_no"] = accession_match.group(2).strip()

        # Visit Number
        visit_match = re.search(r"(Visit\s*Number)[:\-]?\s*(\S+)", text, re.IGNORECASE)
        if visit_match:
            data["visit_no"] = visit_match.group(2).strip()

        return data

    # Generate file hash
    def generate_file_hash(self, file_path: str) -> str:
        try:
            hasher = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            logger.error(f"Error generating file hash: {str(e)}")
            return None

    # Validate extracted data
    def validate_user(self, data: dict) -> list:
        errors = []

        # Name check
        if not data.get("user_name"):
            errors.append("User name not found in report.")

        # Identifier check (ANY ONE should exist)
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

    # File extension check
    def validate_extension(self, file_path: str) -> bool:
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.allowed_extensions:
            logger.warning(f"Invalid file extension: {ext}")
            return False
        return True

    # File size check
    def validate_size(self, file_path: str) -> bool:
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if size_mb > self.max_file_size_mb:
            logger.warning(f"File too large: {size_mb:.2f} MB")
            return False
        return True

    # Empty file check
    def validate_not_empty(self, file_path: str) -> bool:
        if os.path.getsize(file_path) == 0:
            logger.warning("File is empty")
            return False
        return True

    # Main validation pipeline
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

        # File validation
        if not self.validate_extension(file_path):
            result["is_valid"] = False
            result["errors"].append("Invalid file type. Only PDF allowed.")

        if not self.validate_size(file_path):
            result["is_valid"] = False
            result["errors"].append("File size exceeds limit.")

        if not self.validate_not_empty(file_path):
            result["is_valid"] = False
            result["errors"].append("File is empty.")

        # Extract data
        if result["is_valid"]:
            text = self.extract_text(file_path)
            extracted = self.extract_user_details(text)
            result["extracted_data"] = extracted

            # Validate extracted data
            user_errors = self.validate_user(extracted)
            if user_errors:
                result["is_valid"] = False
                result["errors"].extend(user_errors)

            # Identifier priority logic
            for key in ["reg_no", "lab_no", "pid", "patient_id", "accession_no", "visit_no"]:
                if extracted.get(key):
                    result["identifier_used"] = f"{key}: {extracted.get(key)}"
                    break

        # Hash and duplicate check
        if result["is_valid"]:
            file_hash = self.generate_file_hash(file_path)
            result["file_hash"] = file_hash

            existing = check_existing_report(file_hash)

            if existing:
                logger.info("Duplicate file detected.")
                result["is_duplicate"] = True
                result["existing_result"] = existing

        logger.info(f"Validation result: {result}")
        return result