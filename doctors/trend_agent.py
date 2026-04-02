import re
import json
from datetime import datetime
from thefuzz import process
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from llm.llm_provider import get_llm

class TrendAgent:
    def __init__(self):
        # Maps common lab variations to a standard name
        self.aliases = {
            "fbs": "glucose fasting",
            "glucose, fasting": "glucose fasting",
            "fasting blood sugar": "glucose fasting",
            "platelet count": "platelets",
            "hba1c": "hemoglobin a1c",
            "cbc": "complete blood count"
        }
        self.llm = get_llm()

    def _get_float_value(self, value_str):
        """Extracts numerical value from strings like '150 mg/dL' or '450,000'"""
        if not value_str: return None
        clean_str = str(value_str).replace(',', '')
        match = re.search(r"(\d+(\.\d+)?)", clean_str)
        return float(match.group(1)) if match else None

    def _normalize(self, name):
        """Standardizes test names for better matching."""
        name = name.lower().strip()
        return self.aliases.get(name, name)

    def _generate_llm_insight(self, patient_name, trends, is_baseline=False):
        """Uses LLM to interpret trends or summarize a baseline."""
        
        if is_baseline:
            prompt_template = """
            You are a senior medical consultant. This is the FIRST report for {patient_name}.
            Current Results: {trends_json}
            
            Task: Provide a "Baseline Summary". 
            1. Identify if any values are outside the reference ranges (High or Low).
            2. State that these values are now saved as the starting point for future tracking.
            3. Keep it professional, reassuring, and very brief.
            """
        else:
            prompt_template = """
            You are a senior medical consultant. Analyze these lab trends for {patient_name}:
            {trends_json}
            
            Task: Provide a concise clinical interpretation. 
            Note: Some decreases are good (e.g., Glucose) and some are bad (e.g., Hemoglobin).
            Be professional and brief.
            """
            
        prompt = PromptTemplate(input_variables=["patient_name", "trends_json"], template=prompt_template)
        chain = prompt | self.llm | StrOutputParser()
        return chain.invoke({"patient_name": patient_name, "trends_json": json.dumps(trends)})

    def analyze(self, state: dict):
        """
        LANGGRAPH NODE: Analyzes trends or establishes a baseline.
        """
        current_report = state.get("current_report")
        history = state.get("history", [])
        patient_name = current_report.get('patient_name', 'Patient')

        # --- 1. BASELINE LOGIC (If no history exists) ---
        if not history:
            # We treat the current report as the "trends" list for the LLM to summarize
            current_results = current_report.get('lab_results', [])
            insight = self._generate_llm_insight(patient_name, current_results, is_baseline=True)
            
            return {
                "status": "success", 
                "trend_insight": insight, 
                "trends": [], # No historical changes yet
                "history": []
            }

        # --- 2. HISTORY PREPARATION ---
        try:
            history = sorted(history, key=lambda x: datetime.strptime(x.get('report_date', '1900-01-01'), "%Y-%m-%d"))
        except: pass 
        
        last_report = history[-1]

        # --- 3. IDENTITY CHECK ---
        curr_ids = {current_report.get(k) for k in ['pid', 'lab_no', 'reg_no', 'uhid'] if current_report.get(k)}
        prev_ids = {last_report.get(k) for k in ['pid', 'lab_no', 'reg_no', 'uhid'] if last_report.get(k)}
        
        id_confirmed = False
        if curr_ids and prev_ids and not curr_ids.isdisjoint(prev_ids):
            id_confirmed = True

        if not id_confirmed:
            curr_name_low = patient_name.lower().strip()
            prev_name_low = last_report.get('patient_name', '').lower().strip()
            if curr_name_low != prev_name_low:
                return {"status": "identity_mismatch", "trend_insight": "Error: Patient name mismatch."}

        # --- 4. MATCHING & TREND CALCULATION ---
        old_data = {self._normalize(t['test']): t['value'] for t in last_report['lab_results']}
        trends = []

        for item in current_report['lab_results']:
            curr_norm_name = self._normalize(item['test'])
            match_name = None
            
            if curr_norm_name in old_data:
                match_name = curr_norm_name
            else:
                existing_tests = list(old_data.keys())
                if existing_tests:
                    best_match, score = process.extractOne(curr_norm_name, existing_tests)
                    if score > 80: match_name = best_match

            if match_name:
                v_new = self._get_float_value(item['value'])
                v_old = self._get_float_value(old_data[match_name])

                if v_new is not None and v_old is not None and v_old != 0:
                    change = ((v_new - v_old) / v_old) * 100
                    trends.append({
                        "test": item['test'],
                        "current": item['value'],
                        "previous": old_data[match_name],
                        "change_pct": round(change, 2)
                    })

        # --- 5. GENERATE FINAL INSIGHT ---
        if not trends:
            # If we have history but no matching tests, we still summarize the current state
            insight = self._generate_llm_insight(patient_name, current_report['lab_results'], is_baseline=True)
            return {"status": "success", "trend_insight": insight, "trends": []}

        insight = self._generate_llm_insight(patient_name, trends, is_baseline=False)

        return {
            "status": "success",
            "trends": trends,
            "trend_insight": insight
        }