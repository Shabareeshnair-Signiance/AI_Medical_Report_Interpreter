import os
import hashlib
from logger_config import logger
from storage.database import check_existing_report


class ValidationAgent:
    def __init__(self, allowed_extensions = None, max_file_size_mb = 10):
        self.allowed_extensions = allowed_extensions or [".pdf"]
        self.max_file_size_mb = max_file_size_mb

    # generating the file hash
    def generate_file_hash(self, file_path: str) -> str:
        try:
            hasher = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            logger.error(f"Erro generating file hash: {str(e)}")
            return None
        
    # Validating the user details
    def validate_user(self, user_name: str, user_id: str) -> list:
        errors = []

        if not user_name or user_name.strip() == "":
            errors.append("User name is required.")

        if not user_id or user_id.strip() == "":
            errors.append("User id is required.")

        return errors
    
    # File extenstion check
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
    def validate(self, file_path: str, user_name: str, user_id: str) -> dict:
        logger.info("Starting validation process")

        result = {
            "is_valid": True,
            "error": [],
            "file_hash": None,
            "is_duplicate": False,
            "existing_result": None
        }

        # validating the user
        user_errors = self.validate_user(user_name, user_id)
        if user_errors:
            result["is_valid"] = False
            result["errors"].extend(user_errors)

        # validating the file
        if not self.validate_extension(file_path):
            result["is_valid"] = False
            result["errors"].append("Invalid file type. Only PDF allowed.")

        if not self.validate_size(file_path):
            result["is_valid"] = False
            result["errors"].append("File Size exceeds limit.")

        if not self.validate_not_empty(file_path):
            result["is_valid"] = False
            result["errors"].append("File is empty.")

        # Generating hash and checking for duplicate
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