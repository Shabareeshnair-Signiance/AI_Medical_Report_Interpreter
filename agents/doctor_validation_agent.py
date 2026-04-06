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

        # 1. Read PDF first to check content validity
        text = read_pdf(file_path)
        
        # ADDED: Medical Content Check
        if not self._is_medical_content(text):
            logger.warning(f"Validation Failed: {file_path} does not appear to be a medical report.")
            return {
                "is_valid": False,
                "status": "INVALID_FORMAT",
                "error_message": "The uploaded file does not appear to be a valid medical lab report."
            }

        # 2. Generate Hash for Duplicate Check
        file_hash = calculate_file_hash(file_path)
        
        # 3. Instant Check: Is this exact file already in the DB?
        existing = get_existing_analysis(file_hash)
        if existing:
            logger.info("Duplicate file detected. Loading real data from cache.")
            # Note: 'existing' structure depends on your DB schema. 
            # Assuming: (id, hash, name, pid, report_date, analysis_json, created_at)
            return {
                "status": "DUPLICATE",
                "is_valid": True,
                "file_hash": file_hash,
                "existing_analysis": existing, 
                "patient_name": existing[2], 
                "pid": existing[3],          
                "report_date": existing[4],
                "stored_on": existing[6] if len(existing) > 6 else "Unknown", # ADDED: created_at date
                "history_count": 0
            }

        # 4. Extract Identity using HYBRID TIERED LOGIC (Regex + LLM)
        identity = self._get_hybrid_identity(text)

        result = {
            "is_valid": True,
            "status": "NEW_REPORT",
            "file_hash": file_hash,
            "patient_name": identity.get("name"),
            # Tiered Fallback for PID: 
            # If both Regex and LLM fail, we mark as N/A to prevent KeyError
            "pid": str(identity.get("pid")).strip() if identity.get("pid") else "N/A",
            "report_date": identity.get("date"),
            "history_count": 0,
            "existing_analysis": None
        }
        
        # # 4. Extract Identity using Doctor-Specific LLM
        # identity = llm_extract_doctor_identity(text)

        # result = {
        #     "is_valid": True,
        #     "status": "NEW_REPORT",
        #     "file_hash": file_hash,
        #     "patient_name": identity.get("name"),
        #     "pid": identity.get("identifier") or identity.get("pid") or "N/A",
        #     "report_date": identity.get("date"),
        #     "history_count": 0,
        #     "existing_analysis": None
        # }

        # 5. Mandatory Field Check: Patient Name
        if not result["patient_name"] or result["patient_name"].lower() in ["unknown", "not found"]:
            result["is_valid"] = False
            result["status"] = "MISSING_IDENTITY"
            logger.warning("Validation Failed: No patient name extracted.")
            return result
        
        # 6. Check for Patient History (PID or Name match)
        history = get_history_for_patient(pid=result["pid"], name=result["patient_name"])

        if history:
            # Sort history by date to find the 'most recent stored' date
            result["status"] = "HISTORY_FOUND"
            result["history_count"] = len(history)
            # Pass the date of the last report to the UI
            result["last_visit"] = history[-1][4] if history else None 
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