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

    def validate_for_doctor(self, file_path):
        logger.info(f"Doctor Validation: Checking file {file_path}")

        # 1. Generate Hash for Duplicate Check
        file_hash = calculate_file_hash(file_path)
        
        # 2. Instant Check: Is this exact file already in the DB?
        existing = get_existing_analysis(file_hash)
        if existing:
            logger.info("Duplicate file detected. Loading from cache.")
            return {
                "status": "DUPLICATE",
                "is_valid": True,
                "file_hash": file_hash,
                "existing_analysis": existing,
                "patient_name": "Cached Patient",
                "pid": "Cached ID",
                "history_count": 0
            }

        # 3. Extract Identity using Doctor-Specific LLM
        text = read_pdf(file_path)
        identity = llm_extract_doctor_identity(text)

        result = {
            "is_valid": True,
            "status": "NEW_REPORT",
            "file_hash": file_hash,
            "patient_name": identity.get("name"),
            "pid": identity.get("identifier"),
            "report_date": identity.get("date"),
            "history_count": 0,
            "existing_analysis": None
        }

        # 4. Basic Validation: Name is mandatory
        if not result["patient_name"]:
            result["is_valid"] = False
            logger.warning("Validation Failed: No patient name extracted.")
            return result
        
        # 5. Check for Patient History (PID or Name match)
        history = get_history_for_patient(pid=result["pid"], name=result["patient_name"])

        if history:
            result["status"] = "HISTORY_FOUND"
            result["history_count"] = len(history)
        else:
            result["status"] = "NEW_PATIENT"
            
        return result

# --- TESTING CODE ---
if __name__ == "__main__":
    # 1. Setup DB
    init_history_database()
    
    agent = DoctorValidationAgent()
    
    # 2. Define a test file path (Make sure this file exists in your data/uploads)
    test_file_path = "sample_data/Glucose_report.pdf" 
    
    if os.path.exists(test_file_path):
        print("\n" + "="*30)
        print("RUNNING DOCTOR VALIDATION TEST")
        print("="*30)
        
        test_result = agent.validate_for_doctor(test_file_path)
        
        print(f"File Status:    {test_result['status']}")
        print(f"Patient Name:   {test_result['patient_name']}")
        print(f"Identifier:     {test_result['pid']}")
        print(f"Report Date:    {test_result.get('report_date')}")
        print(f"History Found:  {test_result['history_count']} reports")
        print("-" * 30)
        
        if test_result['is_valid']:
            print("SUCCESS: Validation logic is working!")
        else:
            print("FAILED: Validation marked as invalid.")
    else:
        print(f"\n[!] Test Skipped: Please place a file at {test_file_path} to run the test.")