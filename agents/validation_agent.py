import os
import hashlib
from logger_config import logger
from storage.database import check_existing_report


class ValidationAgent:
    def __init__(self, allowed_extensions=None, max_file_size_mb=10):
        self.allowed_extensions = allowed_extensions or [".pdf"]
        self.max_file_size_mb = max_file_size_mb

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

    # Validate user details (UPDATED LOGIC)
    def validate_user(self, user_name: str, reg_no: str, lab_no: str) -> list:
        errors = []

        # Name validation
        if not user_name or user_name.strip() == "":
            errors.append("User name is required.")

        # Reg No / Lab No validation (at least one required)
        if (not reg_no or reg_no.strip() == "") and (not lab_no or lab_no.strip() == ""):
            errors.append("Either Registration Number or Lab Number is required.")

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
    def validate(self, file_path: str, user_name: str, reg_no: str = "", lab_no: str = "") -> dict:
        logger.info("Starting validation process")

        result = {
            "is_valid": True,
            "errors": [],   
            "file_hash": None,
            "is_duplicate": False,
            "existing_result": None,
            "identifier_used": None 
        }

        # Validate user
        user_errors = self.validate_user(user_name, reg_no, lab_no)
        if user_errors:
            result["is_valid"] = False
            result["errors"].extend(user_errors)

        # Decide identifier (Reg No preferred)
        if reg_no and reg_no.strip() != "":
            result["identifier_used"] = f"Reg No: {reg_no}"
        elif lab_no and lab_no.strip() != "":
            result["identifier_used"] = f"Lab No: {lab_no}"

        # Validate file
        if not self.validate_extension(file_path):
            result["is_valid"] = False
            result["errors"].append("Invalid file type. Only PDF allowed.")

        if not self.validate_size(file_path):
            result["is_valid"] = False
            result["errors"].append("File size exceeds limit.")

        if not self.validate_not_empty(file_path):
            result["is_valid"] = False
            result["errors"].append("File is empty.")

        # Generate hash & check duplicate
        if result["is_valid"]:
            file_hash = self.generate_file_hash(file_path)
            result["file_hash"] = file_hash

            existing = check_existing_report(file_hash)

            if existing:
                logger.info("Duplicate file detected. Fetching from DB.")
                result["is_duplicate"] = True
                result["existing_result"] = existing

        logger.info(f"Validation result: {result}")
        return result