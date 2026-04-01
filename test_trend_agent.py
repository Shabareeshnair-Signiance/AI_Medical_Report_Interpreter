import os
import json
import hashlib
from processing.llm_doctor_extractor import llm_doctor_extractor 
from doctors.trend_agent import TrendAgent
from processing.pdf_reader import read_pdf
# Import your new database functions
from storage.medical_history_db import init_history_database, get_history_for_patient, save_patient_trend_data

def generate_file_hash(file_path):
    """Generates a unique hash for the file to prevent re-processing the same PDF."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()

def test_database_pipeline():
    # Initialize the Doctor's History Database
    init_history_database()
    agent = TrendAgent()
    
    print("🚀 Starting Database & Trend Pipeline Test...\n")

    # --- STEP 1: PROCESS HISTORY FILE ---
    path_old = "sample_data/Glucose_report.pdf"
    if not os.path.exists(path_old):
        print(f"❌ Error: File {path_old} not found.")
        return

    print(f"📦 Step 1: Extracting and Saving History ({os.path.basename(path_old)})...")
    text_old = read_pdf(path_old)
    history_data = llm_doctor_extractor(text_old, file_path=path_old)
    hash_old = generate_file_hash(path_old)
    
    # Save this first file so it exists in our "History"
    save_patient_trend_data(hash_old, history_data, {"llm_insight": "Initial report."})

    # --- STEP 2: PROCESS CURRENT FILE ---
    path_new = "sample_data/generated_medical_report.pdf"
    if not os.path.exists(path_new):
        print(f"❌ Error: File {path_new} not found.")
        return

    print(f"📄 Step 2: Extracting Current Report ({os.path.basename(path_new)})...")
    text_new = read_pdf(path_new)
    current_report = llm_doctor_extractor(text_new, file_path=path_new)
    hash_new = generate_file_hash(path_new)

    # --- STEP 3: DATABASE LOOKUP ---
    # Instead of a manual list, we fetch from the DB using our 'Unbreakable' IDs
    pid = current_report.get("pid") or current_report.get("lab_no")
    name = current_report.get("patient_name")
    
    print(f"🔍 Step 3: Searching Database for history (ID: {pid}, Name: {name})...")
    history_list = get_history_for_patient(pid=pid, name=name)
    print(f"✅ Found {len(history_list)} previous reports in database.")

    # --- STEP 4: RUN TREND ANALYSIS ---
    print("\n📈 Step 4: Running Trend Analysis...")
    result = agent.analyze(current_report, history_list)

    # --- STEP 5: SAVE & DISPLAY ---
    if result["status"] == "success":
        # Save the result so the NEXT time you run it, this is also in the history
        save_patient_trend_data(hash_new, current_report, result)
        
        print(f"✅ Patient: {result['patient_name']}")
        print(f"📊 Trends Found: {len(result['trends'])}\n")
        
        for trend in result["trends"]:
            print(f"Test: {trend['test']} | {trend['previous']} -> {trend['current']} ({trend['change_pct']}%)")
        
        print("\n" + "="*50)
        print("💡 CLINICAL INSIGHT STORED IN DATABASE:")
        print("="*50)
        print(result.get("llm_insight"))
        print("="*50 + "\n")
    else:
        print(f"⚠️ Analysis Stopped: {result['status']} - {result['message']}")

if __name__ == "__main__":
    test_database_pipeline()