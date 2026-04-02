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
        You are a Clinical Assistant helping a Doctor. Analyze the results for {patient_name}.
        
        IMPORTANT: 
        - Speak about the patient in the third person (e.g., Use "{patient_name}'s" or "The patient's"). 
        - DO NOT use "You" or "Your" to refer to the doctor.
        - Keep the language simple but professional.

        DATA:
        - Results: {lab_json}
        - Changes: {trends_json}

        TASK (STRICT BREVITY):
        1. THE CONNECTION: What is the main link between these results for {patient_name}?
        2. MAIN GUESS: What is the most likely clinical reason?
        3. OTHER POSSIBILITIES: List 2 other things to consider.
        4. WHAT TO DO NEXT: List 2-3 simple follow-up steps for the doctor.

        Keep the total response under 150 words.
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

if __name__ == "__main__":
    import os
    from processing.pdf_reader import read_pdf
    from processing.llm_doctor_extractor import llm_doctor_extractor
    from doctors.trend_agent import TrendAgent
    from storage.medical_history_db import get_history_for_patient, init_history_database

    print("🧪 Running Symlink Agent: Deep Report Analysis...")
    init_history_database()

    #current_pdf_path = "sample_data/sample_blood_report.pdf"
    #current_pdf_path = "sample_data/CBC Mutiple Test.pdf"
    current_pdf_path = "sample_data/platelet_report.pdf"

    if not os.path.exists(current_pdf_path):
        print(f"❌ Error: {current_pdf_path} not found.")
    else:
        # 1. Extract
        text = read_pdf(current_pdf_path)
        current_report = llm_doctor_extractor(text, file_path=current_pdf_path)

        # 2. Get History & Trends
        pid = current_report.get("pid") or current_report.get("lab_no")
        name = current_report.get("patient_name")
        history_list = get_history_for_patient(pid=pid, name=name)

        trend_agent = TrendAgent()
        trend_result = trend_agent.analyze({
            "current_report": current_report,
            "history": history_list
        })

        # 3. Create State (NO mock symptoms needed anymore)
        state = {
            "current_report": current_report,
            "trends": trend_result.get("trends", [])
        }

        # 4. Run Diagnostic Logic
        symlink_agent = SymlinkAgent()
        final_result = symlink_agent.analyze(state)

        print("\n" + "="*60)
        print(f"📋 CLINICAL SUGGESTION FOR PATIENT: {name}")
        print("="*60)
        print(final_result["clinical_diagnosis_suggestion"])
        print("="*60 + "\n")