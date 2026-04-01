import os
import json
# Importing from your specified paths
from processing.llm_doctor_extractor import llm_doctor_extractor 
from doctors.trend_agent import TrendAgent
from processing.pdf_reader import read_pdf

def test_real_files_pipeline():
    agent = TrendAgent()
    
    print("🚀 Starting Real PDF Pipeline Test...\n")

    # 1. PROCESS THE PREVIOUS REPORT (History)
    # Using the file you mentioned: CBC Mutiple Test.pdf
    #path_old = "sample_data/CBC Mutiple Test.pdf"
    path_old = "sample_data/Glucose_report.pdf"
    print(f"--- Processing History: {os.path.basename(path_old)} ---")
    
    if not os.path.exists(path_old):
        print(f"❌ Error: File {path_old} not found.")
        return

    text_old = read_pdf(path_old)
    # Pass path to allow the date fallback logic in your extractor to work
    history_report = llm_doctor_extractor(text_old, file_path=path_old) 
    
    # Wrap in a list because TrendAgent expects a history list
    history_list = [history_report] 

    # 2. PROCESS THE CURRENT REPORT
    # Using the file you mentioned: sample_blood_report.pdf
    path_new = "sample_data/generated_medical_report.pdf"
    print(f"\n--- Processing Current: {os.path.basename(path_new)} ---")
    
    if not os.path.exists(path_new):
        print(f"❌ Error: File {path_new} not found.")
        return

    text_new = read_pdf(path_new)
    current_report = llm_doctor_extractor(text_new, file_path=path_new)

    # 3. RUN TREND ANALYSIS
    print("\n--- Running Trend Analysis ---")
    # This now performs the Unbreakable Identity check (PID/LabNo/Name+DOB)
    result = agent.analyze(current_report, history_list)

    # 4. DISPLAY RESULTS
    if result["status"] == "success":
        print(f"✅ Patient: {result['patient_name']}")
        print(f"📊 Found {len(result['trends'])} matching tests between reports.\n")
        
        for trend in result["trends"]:
            print(f"Test: {trend['test']}")
            print(f"  Old Value: {trend['previous']}")
            print(f"  New Value: {trend['current']}")
            # Note: We show the raw percentage; the LLM explains if it's good/bad
            print(f"  Change: {trend['change_pct']}%")
            print("-" * 30)
        
        print("\n" + "="*50)
        print("💡 CLINICAL INSIGHT (AI ANALYSIS):")
        print("="*50)
        print(result.get("llm_insight", "No insight generated."))
        print("="*50 + "\n")

    else:
        print(f"⚠️ Analysis Stopped")
        print(f"Status: {result['status']}")
        print(f"Message: {result['message']}")

if __name__ == "__main__":
    test_real_files_pipeline()