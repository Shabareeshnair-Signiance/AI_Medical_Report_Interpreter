import os
import re
import hashlib
from logger_config import logger
from storage.medical_history_db import check_file_exists, get_history_for_patient, get_existing_analysis
from processing.pdf_reader import read_pdf
from processing.llm_validation_extractor import llm_extract_identity

class DoctorValidationAgent:
    def __init__(self):
        self.allowed_extensions = [".pdf"]

    def generate_file_hash(self, file_path):
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def validate_for_doctor(self, file_path):
        logger.info("Doctor Validation: Starting identity check")

        result = {
            "is_valid": True,
            "status": "NEW_REPORT",
            "file_hash": self.generate_file_hash(file_path),
            "patient_name": None,
            "pid": None,
            "history_count": 0,
            "existing_analysis": None
        }

        # Checking if file is a duplicate first
        existing = get_existing_analysis(result["file_hash"])
        if existing:
            result["status"] = "DUPLICATE"
            result["existing_analysis"] = existing
            return result
        
        # Extract Identity (Using your LLM Extractor for accuracy)
        text = read_pdf(file_path)
        identity = llm_extract_identity(text)

        result["patient_name"] = identity.get("name")
        result["pid"] = identity.get("identifier")

        if not result["patient_name"]:
            result["is_valid"] = False
            return result
        
        # Checking for patient history in DB
        history = get_history_for_patient(pid=result["pid"], name = result["patient_name"])

        if history:
            result["status"] = "HISTORY FOUND"
            result["history_count"] = len(history)
        else:
            result["status"] = "NEW PATIENT"
            
        return result