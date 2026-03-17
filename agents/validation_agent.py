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

    # Extract user details from text
    def extract_user_details(self, text: str) -> dict:
        data = {
            "user_name": None,
            "reg_no": None,
            "lab_no": None
        }

        # Name (simple pattern)
        name_match = re.search(r"Name[:\-]?\s*(.+)", text, re.IGNORECASE)
        if name_match:
            data["user_name"] = name_match.group(1).strip()

        # Registration Number
        reg_match = re.search(r"(Reg\s*No|Registration\s*No)[:\-]?\s*(\w+)", text, re.IGNORECASE)
        if reg_match:
            data["reg_no"] = reg_match.group(2).strip()

        # Lab Number
        lab_match = re.search(r"(Lab\s*No)[:\-]?\s*(\w+)", text, re.IGNORECASE)
        if lab_match:
            data["lab_no"] = lab_match.group(2).strip()

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
    def validate_user(self, user_name: str, reg_no: str, lab_no: str) -> list:
        errors = []

        if not user_name:
            errors.append("User name not found in report.")

        if not reg_no and not lab_no:
            errors.append("Neither Reg No nor Lab No found in report.")

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

    # Main validation pipeline (AUTO MODE)
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

            user_name = extracted["user_name"]
            reg_no = extracted["reg_no"]
            lab_no = extracted["lab_no"]

            # Validate extracted data
            user_errors = self.validate_user(user_name, reg_no, lab_no)
            if user_errors:
                result["is_valid"] = False
                result["errors"].extend(user_errors)

            # Identifier logic
            if reg_no:
                result["identifier_used"] = f"Reg No: {reg_no}"
            elif lab_no:
                result["identifier_used"] = f"Lab No: {lab_no}"

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