import os
# Replace 'your_extractor_file' with the actual filename where these functions live
# Example: from extraction_layer import read_pdf, llm_doctor_extractor
from processing.llm_doctor_extractor import llm_doctor_extractor 
from doctors.trend_agent import TrendAgent
from processing.pdf_reader import read_pdf

def test_real_files_pipeline():
    agent = TrendAgent()
    
    print("🚀 Starting Real PDF Pipeline Test...\n")

    # 1. PROCESS THE PREVIOUS REPORT (History)
    print("--- Processing History: CBC Mutiple Test.pdf ---")
    path_old = "sample_data/CBC Mutiple Test.pdf"
    if not os.path.exists(path_old):
        print(f"❌ Error: File {path_old} not found.")
        return

    text_old = read_pdf(path_old)
    history_report = llm_doctor_extractor(text_old) # This returns a JSON object
    
    # Wrap in a list because TrendAgent expects a history list
    history_list = [history_report] 

    # 2. PROCESS THE CURRENT REPORT
    print("\n--- Processing Current: Sample Blood Report.pdf ---")
    path_new = "sample_data/sample_blood_report.pdf"
    if not os.path.exists(path_new):
        print(f"❌ Error: File {path_new} not found.")
        return

    text_new = read_pdf(path_new)
    current_report = llm_doctor_extractor(text_new)

    # 3. RUN TREND ANALYSIS
    print("\n--- Running Trend Analysis ---")
    result = agent.analyze(current_report, history_list)

    # 4. DISPLAY RESULTS
    if result["status"] == "success":
        print(f"✅ Patient: {result['patient_name']}")
        print(f"Found {len(result['trends'])} matching tests between reports.\n")
        
        for trend in result["trends"]:
            print(f"Test: {trend['test']}")
            print(f"  Old Value: {trend['previous']}")
            print(f"  New Value: {trend['current']}")
            print(f"  Change: {trend['change_pct']}% ({trend['status']})")
            print("-" * 30)
    else:
        print(f"⚠️ Status: {result['status']}")
        print(f"Message: {result['message']}")

if __name__ == "__main__":
    test_real_files_pipeline()