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
    get_existing_analysis
)
from logger_config import logger

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

# --- 4. Testing Code (Keep as requested) ---
if __name__ == "__main__":
    init_history_database()

    # Replace with a real PDF path in your project to test
    input_state = {
        "file_path": "data/uploads/platelet_report.pdf" 
    }

    logger.info("Starting LangGraph Medical Workflow")
    try:
        final_output = app.invoke(input_state)

        print("\n" + "=".center(60, "="))
        print(f"FINAL REPORT FOR: {final_output.get('current_report', {}).get('patient_name', 'Unknown')}")
        print(f"PATIENT ID: {final_output.get('current_report', {}).get('pid', 'N/A')}")
        print("=".center(60, "="))
        
        suggestion = final_output.get('clinical_suggestion', 'No suggestion available.')
        insight = final_output.get('trend_insight', 'No trend insight available.')

        print(f"\n[CLINICAL SUGGESTION]\n{suggestion}")
        print(f"\n[TREND ANALYSIS]\n{insight}")
        print("=".center(60, "="))
        
    except Exception as e:
        logger.error(f"Test Execution Failed: {e}")