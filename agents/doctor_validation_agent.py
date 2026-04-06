import os
import hashlib
from logger_config import logger

# Import your new specialized Doctor LLM
from processing.llm_doctor_validator import llm_extract_doctor_identity

# Database and Reader imports
from storage.medical_history_db import (
    get_existing_analysis, 
    get_history_for_patient, 
    calculate_file_hash,
    init_history_database
)
from processing.pdf_reader import read_pdf

class DoctorValidationAgent:
    def __init__(self):
        self.allowed_extensions = [".pdf"]

        # Adding the keywords to verify if the documents is actually a medical report
        self.medical_keywords = [
            "hemoglobin", "platelet", "blood", "urine",
            "test", "lab", "report", "glucose", "wbc",
            "rbc", "thyroid", "vitamin", "serum"
        ]

    def _is_medical_content(self, text):
        """Helper to check if the text contains medical terminology."""
        if not text: return False
        text_lower = text.lower()
        # Count how many medical keywords appear in the text
        matches = sum(1 for word in self.medical_keywords if word in text_lower)
        # If at least 3 keywords match, we consider it a medical report
        return matches >= 3
    
    def _get_hybrid_identity(self, text):
        """Tiered Identity Matching: Tier 1 (Strict Regex) -> Tier 2 (Fuzzy Regex) -> Tier 3 (LLM)"""
        import re
        identity = {"pid": None, "name": None, "date": None}

        # --- TIER 1: Strict Regex (Fastest) ---
        strict_match = re.search(r"PID:\s*(\d+)", text)
        if strict_match:
            identity["pid"] = strict_match.group(1)
            logger.info(f"Tier 1 Match Success: Found PID {identity['pid']}")

        # --- TIER 2: Fuzzy Regex (Handles pipes '|' and different labels) ---
        if not identity["pid"]:
            # Looks for PID, ID, or Lab No followed by symbols and 3-6 digits
            fuzzy_match = re.search(r"(?:PID|ID|Lab No|UHID)[\s|:]*(\d{3,6})", text, re.IGNORECASE)
            if fuzzy_match:
                identity["pid"] = fuzzy_match.group(1)
                logger.info(f"Tier 2 Match Success: Found PID {identity['pid']}")

        # --- TIER 3: LLM Extractor (The Ultimate Fallback) ---
        # We call the LLM to get the Name and Date, and to find the PID if Regex failed
        logger.info("Running Tier 3: LLM Identity Extraction")
        llm_identity = llm_extract_doctor_identity(text)
        
        # Final Decision Logic:
        # 1. Use Regex PID if found; otherwise, use LLM's identified PID.
        final_pid = identity["pid"] or llm_identity.get("identifier") or llm_identity.get("pid")
        
        # 2. Use LLM for Name and Date as they are too complex for reliable Regex.
        return {
            "pid": final_pid,
            "name": llm_identity.get("name"),
            "date": llm_identity.get("date")
        }

    def validate_for_doctor(self, file_path):
        logger.info(f"Doctor Validation: Checking file {file_path}")

        # 1. Read PDF first
        text = read_pdf(file_path)
        
        if not self._is_medical_content(text):
            return {
                "is_valid": False,
                "status": "INVALID_FORMAT",
                "error_message": "The uploaded file does not appear to be a valid medical lab report."
            }

        # 2. Generate Hash
        file_hash = calculate_file_hash(file_path)
        
        # 3. Instant Check: Duplicate Detection
        existing = get_existing_analysis(file_hash)
        if existing:
            logger.info("Duplicate file detected. Loading real data from cache.")
            # SAFE ACCESS: Using names instead of [index]
            return {
                "status": "DUPLICATE",
                "is_valid": True,
                "file_hash": file_hash,
                "existing_analysis": existing, 
                "patient_name": existing["patient_name"], 
                "pid": existing["patient_id"],           
                "report_date": existing["report_date"],
                "stored_on": "Already Analyzed", 
                "history_count": 0
            }

        # 4. Extract Identity
        identity = self._get_hybrid_identity(text)

        result = {
            "is_valid": True,
            "status": "NEW_REPORT",
            "file_hash": file_hash,
            "patient_name": identity.get("name"),
            "pid": str(identity.get("pid")).strip() if identity.get("pid") else "N/A",
            "report_date": identity.get("date"),
            "history_count": 0,
            "existing_analysis": None
        }

        # 5. Mandatory Field Check
        if not result["patient_name"] or result["patient_name"].lower() in ["unknown", "not found"]:
            result["is_valid"] = False
            result["status"] = "MISSING_IDENTITY"
            return result
        
        # 6. Check for Patient History
        history = get_history_for_patient(pid=result["pid"], name=result["patient_name"])

        if history:
            result["status"] = "HISTORY_FOUND"
            result["history_count"] = len(history)
            # SAFE ACCESS: history is a list of dicts, get the date from the last one
            result["last_visit"] = history[-1].get("report_date") if history else None 
        else:
            result["status"] = "NEW_PATIENT"
            
        return result

# --- TESTING CODE ---
# if __name__ == "__main__":
#     # 1. Setup DB
#     init_history_database()
    
#     agent = DoctorValidationAgent()
    
#     # 2. Define a test file path (Make sure this file exists in your data/uploads)
#     test_file_path = "sample_data/Glucose_report.pdf" 
    
#     if os.path.exists(test_file_path):
#         print("\n" + "="*30)
#         print("RUNNING DOCTOR VALIDATION TEST")
#         print("="*30)
        
#         test_result = agent.validate_for_doctor(test_file_path)
        
#         print(f"File Status:    {test_result['status']}")
#         print(f"Patient Name:   {test_result['patient_name']}")
#         print(f"Identifier:     {test_result['pid']}")
#         print(f"Report Date:    {test_result.get('report_date')}")
#         print(f"History Found:  {test_result['history_count']} reports")
#         print("-" * 30)
        
#         if test_result['is_valid']:
#             print("SUCCESS: Validation logic is working!")
#         else:
#             print("FAILED: Validation marked as invalid.")
#     else:
#         print(f"\n[!] Test Skipped: Please place a file at {test_file_path} to run the test.")