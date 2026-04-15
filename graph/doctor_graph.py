import os
import hashlib
from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END

# Importing your existing tools
from processing.pdf_reader import read_pdf
from processing.llm_doctor_extractor import llm_doctor_extractor
from doctors.trend_agent import TrendAgent
from doctors.symlink_agent import SymlinkAgent
from storage.medical_history_db import (
    init_history_database,
    get_history_for_patient,
    save_patient_trend_data,
    get_existing_analysis,
    save_doctor_vision_report
)

from doctors_ocr.doctor_llm_ocr_extractor import run_doctor_ocr_pipeline
from logger_config import logger
from datetime import datetime

def standardize_date(date_str):
    """Converts messy OCR dates into strict YYYY-MM-DD for accurate sorting."""
    if not date_str:
        return "Unknown"
    
    # Common formats labs use
    formats_to_try = ["%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y"]
    
    clean_str = str(date_str).strip()
    for fmt in formats_to_try:
        try:
            # Try to parse it
            parsed_date = datetime.strptime(clean_str, fmt)
            # If successful, spit it out in standard ISO format
            return parsed_date.strftime("%Y-%m-%d")
        except ValueError:
            continue
            
    # If it fails all formats, return the original so it doesn't crash
    return clean_str


# 1. Defining the State
class AgentState(TypedDict):
    file_path: str
    file_hash: str
    current_report: dict
    history: List[dict]
    trends: List[dict]
    trend_insight: str
    clinical_suggestion: str
    status: str

# --- 2. Define the Nodes ---

def extract_node(state: AgentState):
    logger.info(f"NODE: Extracting PDF")
    path = state["file_path"]

    # Generate hash to check if we've seen this file
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192): 
            sha256.update(chunk)
    file_hash = sha256.hexdigest()

    # Checking Cache first
    existing = get_existing_analysis(file_hash)

    # FIX: If valid cache exists, retrieve REAL patient data from the DB tuple
    # Tuple mapping: (insight, suggestion, name, pid, date)
    if existing and existing[1] and existing[1] != "None":
        logger.info(f"Valid analysis found for {existing[2]}. Skipping AI.")
        return {
            "file_hash": file_hash, 
            "status": "CACHED", 
            "trend_insight": existing[0] if existing[0] else "Initial report.", 
            "clinical_suggestion": existing[1],
            "current_report": {
                "patient_name": existing[2],
                "pid": existing[3],
                "report_date": existing[4]
            }
        }
    
    # If no valid cache, run the full extraction automatically
    logger.info("No valid cache found. Running AI Extraction Pipeline...")
    text = read_pdf(path)
    report_data = llm_doctor_extractor(text) # Automatically extracts name, pid, results
    
    return {
        "current_report": report_data, 
        "file_hash": file_hash, 
        "status": "NEW"
    }

def trend_node(state: AgentState):
    # If cached, we already have the insight, so just pass through
    if state.get("status") == "CACHED": 
        return state
        
    logger.info(f"NODE: Analyzing Trends")
    report = state["current_report"]
    pid = report.get("pid") or report.get("lab_no")
    name = report.get("patient_name")

    # Fetch history based on the automatically extracted data
    history = get_history_for_patient(pid=pid, name=name)
    
    agent = TrendAgent()
    result = agent.analyze({"current_report": report, "history": history})

    insight = result.get("trend_insight", "No previous history found for comparison.")

    return {
        "trends": result.get("trends", []),
        "trend_insight": insight,
        "history": history
    }

def symlink_node(state: AgentState):
    # If cached, we already have the suggestion, so just pass through
    if state.get("status") == "CACHED": 
        return state
        
    logger.info(f"NODE: Symlink Diagnostics")
    agent = SymlinkAgent()
    
    result = agent.analyze({
        "current_report": state["current_report"],
        "trends": state.get("trends", [])
    })

    return {"clinical_suggestion": result.get("clinical_diagnosis_suggestion", "Consult specialist.")}

def save_node(state: AgentState):
    # Only save if this is a fresh analysis
    if state.get("status") == "NEW":
        logger.info(f"NODE: Saving New Results to Database")
        
        combined_analysis = {
            "trend_insight": state.get("trend_insight", "Initial report."),
            "clinical_suggestion": state.get("clinical_suggestion", "No diagnosis generated."),
            "trends": state.get("trends", [])
        }
        
        save_patient_trend_data(
            state["file_hash"], 
            state["current_report"], 
            combined_analysis
        )
        logger.info("Successfully saved to Database.")
        
    return state

# --- 3. Building the Graph ---
workflow = StateGraph(AgentState)

workflow.add_node("extractor", extract_node)
workflow.add_node("trend_analyzer", trend_node)
workflow.add_node("symlink_detective", symlink_node)
workflow.add_node("db_saver", save_node)

workflow.set_entry_point("extractor")
workflow.add_edge("extractor", "trend_analyzer")
workflow.add_edge("trend_analyzer", "symlink_detective")
workflow.add_edge("symlink_detective", "db_saver")
workflow.add_edge("db_saver", END)

app = workflow.compile()


# 4.  New Vision AI Integration
def vision_extract_node(state: AgentState):
    """Replaces the text extractor with our new Vision-First Document Router."""
    logger.info(f"NODE: Vision Extracting PDF/Image")
    path = state["file_path"]

    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192): 
            sha256.update(chunk)
    file_hash = sha256.hexdigest()

    existing = get_existing_analysis(file_hash)
    if existing and existing[1] and existing[1] != "None":
        logger.info(f"Valid analysis found in cache. Skipping Vision AI.")
        return {
            "file_hash": file_hash, 
            "status": "CACHED", 
            "trend_insight": existing[0] if existing[0] else "Initial report.", 
            "clinical_suggestion": existing[1],
            "current_report": {
                "patient_name": existing[2],
                "pid": existing[3],
                "report_date": existing[4]
            }
        }
    
    logger.info("Running Multi-Modal Vision Pipeline...")
    
    # Run the new pipeline to get lab results
    vision_data = run_doctor_ocr_pipeline(path)
    
    # Merge the extracted lab results with any metadata passed from the UI
    current_report = state.get("current_report", {})
    current_report.update(vision_data)

    # Normalizing the date for sorting
    if current_report.get("report_date"):
        current_report["report_date"] = standardize_date(current_report["report_date"])

    return {
        "current_report": current_report, 
        "file_hash": file_hash, 
        "status": "NEW"
    }

def vision_save_node(state: AgentState):
    """Replaces the save node to use our new safe database wrapper."""
    if state.get("status") == "NEW":
        logger.info(f"NODE: Saving Vision Results to Database")
        
        combined_analysis = {
            "trend_insight": state.get("trend_insight", "Initial report."),
            "clinical_suggestion": state.get("clinical_suggestion", "No diagnosis generated.")
        }
        
        # Calling the new safe wrapper we added to medical_history_db.py
        save_doctor_vision_report(
            state["file_hash"], 
            state["current_report"], # Contains metadata
            state["current_report"], # Contains lab_results
            combined_analysis
        )
        logger.info("Successfully saved Vision data to Database.")
        
    return state

# 5. Building the Vision Graph
vision_workflow = StateGraph(AgentState)

vision_workflow.add_node("vision_extractor", vision_extract_node)
vision_workflow.add_node("trend_analyzer", trend_node) # Reusing existing agent!
vision_workflow.add_node("symlink_detective", symlink_node) # Reusing existing agent!
vision_workflow.add_node("vision_db_saver", vision_save_node)

vision_workflow.set_entry_point("vision_extractor")
vision_workflow.add_edge("vision_extractor", "trend_analyzer")
vision_workflow.add_edge("trend_analyzer", "symlink_detective")
vision_workflow.add_edge("symlink_detective", "vision_db_saver")
vision_workflow.add_edge("vision_db_saver", END)

# This is the new app we will call from Flask for Doctor Uploads
vision_app = vision_workflow.compile()

# # --- 4. Testing Code ---
# if __name__ == "__main__":
#     import os
    
#     # Initialize DB just in case it's the first time running on a new machine
#     init_history_database()

#     # Using the scanned report we tested earlier
#     test_file = "sample_data/Scanned_report.pdf"
#     #test_file = "sample_data/Medical_report.pdf"

#     if not os.path.exists(test_file):
#         print(f"\n[X] Error: Could not find {test_file}. Please check the path.")
#     else:
#         input_state = {
#             "file_path": test_file 
#         }

#         logger.info("Starting VISION LangGraph Medical Workflow")
#         try:
#             # CRITICAL: We are invoking the NEW vision_app, not the old app!
#             final_output = vision_app.invoke(input_state)

#             report_data = final_output.get('current_report', {})
            
#             print("\n" + "=".center(70, "="))
#             print(" DOCTOR VISION PIPELINE: END-TO-END TEST ".center(70))
#             print("=".center(70, "="))
#             print(f"PATIENT NAME : {report_data.get('patient_name', 'Unknown')}")
#             print(f"PATIENT ID   : {report_data.get('pid', 'N/A')}")
#             print(f"TOTAL RESULTS: {len(report_data.get('lab_results', []))} tests extracted via Vision AI")
#             print("=".center(70, "="))
            
#             suggestion = final_output.get('clinical_suggestion', 'No suggestion available.')
#             insight = final_output.get('trend_insight', 'No trend insight available.')

#             print(f"\n[TREND ANALYSIS (From Trend Agent)]\n{insight}")
#             print(f"\n[CLINICAL SUGGESTION (From Symlink Agent)]\n{suggestion}")
#             print("\n" + "=".center(70, "="))
            
#         except Exception as e:
#             logger.error(f"Test Execution Failed: {e}")