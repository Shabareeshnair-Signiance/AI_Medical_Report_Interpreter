import re
import json
from datetime import datetime
from thefuzz import process
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from llm.llm_provider import get_llm
from logger_config import logger

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
            You are a Clinical Summary Assistant. This is the FIRST report for {patient_name}.
            Current Results: {trends_json}

            Write a clinical snapshot in exactly 3 lines. No markdown, no ** symbols, no bullet points.

            Line 1 - FINDINGS: State how many values are abnormal out of total and name the most critical one with its actual number and reference range.
            Line 2 - SIGNIFICANCE: In one sentence explain what the most abnormal value clinically means for the patient.
            Line 3 - BASELINE NOTE: State this is now saved as the starting point and what to watch on next visit.

            Use plain text only. Be specific with numbers. Keep under 60 words total.
            Important: Do NOT use any markdown formatting like ** or ## in your response. Plain text only.
            """
        else:
            prompt_template = """
            You are a Clinical Summary Assistant. Analyze these lab trends for {patient_name}:
            {trends_json}

            Write a clinical snapshot in exactly 3 lines. No markdown, no ** symbols, no bullet points.

            Line 1 - CHANGE: State the most significant change with exact numbers from previous to current and percentage change.
            Line 2 - DIRECTION: Is the patient improving, worsening or stable overall? Name the specific value driving this conclusion.
            Line 3 - ACTION: One specific thing the doctor should focus on at this visit based on the numbers.

            Use plain text only. Be specific with numbers. Keep under 60 words total.
            Important: Do NOT use any markdown formatting like ** or ## in your response. Plain text only.
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

        # --- 1. BASELINE LOGIC ---
        # If history is empty OR only contains the current report we just saved
        if not history:
            current_results = current_report.get('lab_results', [])
            insight = self._generate_llm_insight(patient_name, current_results, is_baseline=True)
            
            return {
                "status": "success", 
                "trend_insight": insight, 
                "trends": [], 
                "history": history
            }

        # --- 2. HISTORY PREPARATION ---
        try:
            # Sort by date: Oldest -> Newest
            history = sorted(history, key=lambda x: datetime.strptime(x.get('report_date', '1900-01-01'), "%Y-%m-%d"))
            
            # history[-1] is the report you just uploaded.
            # history[-2] is the TRUE previous report.
            last_report = history[-2] 
        except Exception as e:
            logger.error(f"Sorting error: {e}")
            # Fallback to the first item if sorting fails
            last_report = history[0]

        # REMOVED: last_report = history[-1] <--- This was the bug!

        # --- 3. IDENTITY CHECK ---
        # I trust the database logic. If 'history' contains these reports,
        # they have already been matched by Internal UID
        id_confirmed = True

        # curr_ids = {current_report.get(k) for k in ['pid', 'lab_no', 'reg_no', 'uhid'] if current_report.get(k)}
        # prev_ids = {last_report.get(k) for k in ['pid', 'lab_no', 'reg_no', 'uhid'] if last_report.get(k)}

        # Optional: Keep a simple name check just as a final safety barrier
        curr_name_low = patient_name.lower().strip()
        prev_name_low = last_report.get('patient_name', '').lower().strip()
        
        if curr_name_low not in prev_name_low and prev_name_low not in curr_name_low:
             # Only trigger mismatch if names are completely different (e.g., Rahul vs Amit)
             return {"status": "identity_mismatch", "trend_insight": "Error: Patient names do not match."}

        # id_confirmed = False
        # if curr_ids and prev_ids and not curr_ids.isdisjoint(prev_ids):
        #     id_confirmed = True

        # if not id_confirmed:
        #     curr_name_low = patient_name.lower().strip()
        #     prev_name_low = last_report.get('patient_name', '').lower().strip()
        #     if curr_name_low != prev_name_low:
        #         # If name and ID both fail to match, it's a different person
        #         return {"status": "identity_mismatch", "trend_insight": "Error: Patient identity could not be verified."}

        # --- 4. MATCHING & TREND CALCULATION ---
        # Use the lab_results from history[-2] (the old report)
        old_data = {self._normalize(t['test']): t['value'] for t in last_report.get('lab_results', [])}
        trends = []

        for item in current_report.get('lab_results', []):
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
            trends = [
                {"test": item['test'], "current": item['value'], "previous": "N/A", "change_pct": 0}
                for item in current_report.get('lab_results', [])
            ]

        has_comparison = any(t.get("previous") and t.get("previous") != "N/A" for t in trends)

        insight = self._generate_llm_insight(
            patient_name, 
            trends if has_comparison else current_report.get('lab_results', []), 
            is_baseline=not has_comparison
        )

        return {
            "status": "success",
            "trend_insight": insight,
             "trends": trends,
        }