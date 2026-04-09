import json
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from llm.llm_provider import get_llm

class SymlinkAgent:
    def __init__(self):
        self.llm = get_llm()

    def analyze(self, state: dict):
        current_report = state.get("current_report", {})
        patient_name = current_report.get("patient_name", "the patient")
        trends = state.get("trends", [])
        lab_results = current_report.get("lab_results", [])
        
        prompt_template = """
You are a Clinical Pattern Recognition Engine helping a doctor diagnose {patient_name}.
Your job is NOT to list findings — it is to CONNECT them and find the hidden pattern.

DATA:
- Lab Results: {lab_json}
- Trend Changes: {trends_json}

STRICT OUTPUT FORMAT — no markdown, no ** symbols, plain text only:

URGENCY: [URGENT / MONITOR / ROUTINE] - one sentence why

PATTERN DETECTED: First group ALL abnormal values by body system. 
Then describe the strongest connection across groups in one sentence.
If 5 or more values are abnormal group them like this:
  Group 1 - [System name]: [test1, test2] — possible link
  Group 2 - [System name]: [test3, test4] — possible link
  Cross-system connection: One sentence connecting the groups.
If only one test is abnormal write: "Single abnormal value — no cross-system pattern detected."

SYSTEM AFFECTED: List ALL affected systems separated by arrows like:
Endocrine -> Hematologic -> Hepatic

ROOT CAUSE HYPOTHESIS: Most likely single condition explaining ALL abnormal values together - confidence: High/Medium/Low
DIFFERENTIAL: Two alternative explanations if the root cause is wrong

MISSING TEST: The single most important test NOT in this report that would confirm or rule out the root cause

TREND IMPACT: [Only if trend data exists] Is the pattern getting better or worse and which value is driving it?

NEXT STEPS:
1. [Most urgent action]
2. [Second action]
3. [Referral or lifestyle action]

DOCTOR NOTE: One sentence the doctor should say to the patient today about the overall pattern.

RULES:
- Never treat each test in isolation — always look for the connection between them
- If only one test is abnormal say so clearly and don't force a connection
- Use actual numbers from the data
- Never use ** or ## or any markdown
- If more than 5 abnormal values exist, scale the response up to 300 words
- Always group by system before connecting — never list tests randomly
- Prioritize the most dangerous pattern over the most common one
"""

        prompt = PromptTemplate(
            input_variables=["patient_name", "lab_json", "trends_json"], 
            template=prompt_template
        )

        chain = prompt | self.llm | StrOutputParser()
        
        # Pass patient_name into the chain
        analysis = chain.invoke({
            "patient_name": patient_name,
            "lab_json": json.dumps(lab_results),
            "trends_json": json.dumps(trends)
        })

        return {
            "clinical_diagnosis_suggestion": analysis,
            "status": "success"
        }

# TESTING PART (Focused on Report Analysis)

# if __name__ == "__main__":
#     import os
#     import hashlib
#     import sqlite3
#     from processing.pdf_reader import read_pdf
#     from processing.llm_doctor_extractor import llm_doctor_extractor
#     from doctors.trend_agent import TrendAgent
#     from storage.medical_history_db import (
#         get_history_for_patient, 
#         init_history_database, 
#         save_patient_trend_data,
#         DB_PATH # Import path to query DB
#     )

#     def generate_file_hash(file_path):
#         sha256 = hashlib.sha256()
#         with open(file_path, "rb") as f:
#             while chunk := f.read(8192):
#                 sha256.update(chunk)
#         return sha256.hexdigest()

#     def get_existing_analysis(file_hash):
#         """Checks if we already have the analysis in the DB."""
#         try:
#             conn = sqlite3.connect(DB_PATH)
#             cursor = conn.cursor()
#             cursor.execute("""
#                 SELECT llm_insight, clinical_suggestion 
#                 FROM patient_reports WHERE file_hash = ?
#             """, (file_hash,))
#             row = cursor.fetchone()
#             conn.close()
#             return row if row else None
#         except:
#             return None

#     print("🧪 Running Symlink Agent: Analysis & DB Cache System...")
#     init_history_database()

#     current_pdf_path = "sample_data/platelet_report.pdf"

#     if not os.path.exists(current_pdf_path):
#         print(f"❌ Error: {current_pdf_path} not found.")
#     else:
#         # 1. Generate Hash
#         file_hash = generate_file_hash(current_pdf_path)
        
#         # 2. CHECK DATABASE FIRST
#         existing = get_existing_analysis(file_hash)

#         if existing:
#             trend_insight, clinical_suggestion = existing
#             print("\n" + "⚡" * 30)
#             print("✅ RETRIEVING STORED ANALYSIS FROM DATABASE")
#             print("⚡" * 30)
#             print(f"📋 CLINICAL SUGGESTION:\n{clinical_suggestion}")
#             print("-" * 60)
#             print(f"📈 TREND INSIGHT:\n{trend_insight}")
#             print("=" * 60 + "\n")
        
#         else:
#             print("🔍 New file detected. Starting AI Analysis pipeline...")
            
#             # A. Extract
#             text = read_pdf(current_pdf_path)
#             current_report = llm_doctor_extractor(text, file_path=current_pdf_path)

#             # B. Get History & Run Trend Agent
#             pid = current_report.get("pid") or current_report.get("lab_no")
#             name = current_report.get("patient_name")
#             history_list = get_history_for_patient(pid=pid, name=name)

#             trend_agent = TrendAgent()
#             trend_result = trend_agent.analyze({
#                 "current_report": current_report,
#                 "history": history_list
#             })

#             # C. Create State and Run Symlink Agent
#             state = {
#                 "current_report": current_report,
#                 "trends": trend_result.get("trends", [])
#             }

#             symlink_agent = SymlinkAgent()
#             symlink_result = symlink_agent.analyze(state)

#             # D. COMBINE AND SAVE
#             combined_analysis = {
#                 "trend_insight": trend_result.get("trend_insight"),
#                 "clinical_diagnosis_suggestion": symlink_result.get("clinical_diagnosis_suggestion"),
#                 "trends": trend_result.get("trends", [])
#             }

#             save_patient_trend_data(file_hash, current_report, combined_analysis)

#             # E. Output for New Analysis
#             print("\n" + "="*60)
#             print(f"📋 NEW CLINICAL SUGGESTION FOR: {name}")
#             print("="*60)
#             print(symlink_result["clinical_diagnosis_suggestion"])
#             print("-" * 60)
#             print(f"📈 NEW TREND INSIGHT: {trend_result.get('trend_insight')}")
#             print("="*60)
#             print("✅ New Analysis saved to Database successfully.\n")