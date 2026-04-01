import os
import hashlib
from processing.llm_doctor_extractor import llm_doctor_extractor 
from doctors.trend_agent import TrendAgent
from processing.pdf_reader import read_pdf
# Import our production-level functions
from storage.medical_history_db import (
    init_history_database, 
    get_report_scenario, 
    save_patient_trend_data
)

def generate_file_hash(file_path):
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()

def process_single_upload(file_path):
    """
    Simulates a REAL WORLD single-file upload process.
    """
    init_history_database()
    agent = TrendAgent()
    
    # 1. Physical Extraction
    file_hash = generate_file_hash(file_path)
    text = read_pdf(file_path)
    current_report = llm_doctor_extractor(text, file_path=file_path)

    # 2. Database Intelligence: Determine the Scenario
    scenario, history_list = get_report_scenario(file_hash, current_report)

    print(f"\n" + "="*60)
    print(f"📄 FILE: {os.path.basename(file_path)}")
    print(f"🔍 SCENARIO DETECTED: {scenario}")
    print("="*60)

    # SCENARIO 1: New Patient (Saves report and stops)
    if scenario == "NEW_PATIENT":
        print("🆕 Message: No history found. This is a new patient.")
        save_patient_trend_data(file_hash, current_report, {"llm_insight": "Baseline established."})
        print(f"✅ Action: {current_report.get('patient_name')} has been registered in the history database.")

    # SCENARIO 2: Trend Analysis (Fetches DB data and compares)
    elif scenario == "HISTORY_AVAILABLE":
        print("📊 Message: Previous reports found! Generating Trend Analysis...")
        result = agent.analyze(current_report, history_list)
        
        if result["status"] == "success":
            save_patient_trend_data(file_hash, current_report, result)
            print(f"✅ Patient: {result['patient_name']}")
            print(f"📈 Match found: {len(result['trends'])} tests compared.")
            for t in result["trends"]:
                print(f"   - {t['test']}: {t['previous']} -> {t['current']} ({t['change_pct']}%)")
            print(f"\n💡 AI CLINICAL INSIGHT: {result.get('llm_insight')}")

    # SCENARIO 3: Duplicate Protection
    elif scenario == "EXISTS_IN_DB" or scenario == "SAME_DATE_REPORT":
        print("⚠️ Message: This report (or a report from this date) is already in the system.")
        print("✅ Action: Skipped duplicate processing.")

if __name__ == "__main__":
    # --- SIMULATION START ---
    
    # RUN 1: Upload the older glucose report (The "History")
    process_single_upload("sample_data/Glucose_report.pdf")
    
    # RUN 2: Upload the newer generated report (The "Current")
    process_single_upload("sample_data/generated_medical_report.pdf")