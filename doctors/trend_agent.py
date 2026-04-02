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

    def _generate_llm_insight(self, patient_name, trends):
        """Uses LLM to interpret if trends are clinically good or bad."""
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
        LANGGRAPH NODE: Analyzes trends based on the current state.
        Expects: state['current_report'], state['history']
        Updates: state['trends'], state['trend_insight'], state['status']
        """
        current_report = state.get("current_report")
        history = state.get("history", [])

        # 1. History Check
        if not history:
            return {
                "status": "new_patient", 
                "trend_message": "No history found.", 
                "trends": []
            }

        try:
            history = sorted(history, key=lambda x: datetime.strptime(x.get('report_date', '1900-01-01'), "%Y-%m-%d"))
        except: pass 
        
        last_report = history[-1]

        # 2. LAYERED IDENTITY CHECK
        curr_ids = {current_report.get(k) for k in ['pid', 'lab_no', 'reg_no', 'uhid'] if current_report.get(k)}
        prev_ids = {last_report.get(k) for k in ['pid', 'lab_no', 'reg_no', 'uhid'] if last_report.get(k)}
        
        id_confirmed = False
        if curr_ids and prev_ids and not curr_ids.isdisjoint(prev_ids):
            id_confirmed = True

        if not id_confirmed:
            curr_name = current_report.get('patient_name', '').lower().strip()
            prev_name = last_report.get('patient_name', '').lower().strip()
            curr_dob = current_report.get('dob')
            prev_dob = last_report.get('dob')

            if curr_name != prev_name:
                return {"status": "identity_mismatch", "trend_message": "Patient names do not match."}
            
            if curr_dob and prev_dob and curr_dob != prev_dob:
                return {"status": "identity_mismatch", "trend_message": "Date of Birth mismatch."}

        # 3. DUPLICATE CHECK
        if current_report.get('report_date') == last_report.get('report_date'):
            if current_report.get('report_time') == last_report.get('report_time'):
                return {"status": "duplicate", "trend_message": "Report already exists."}

        # 4. MATCHING & MATH
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

        if not trends:
            return {"status": "no_matches", "trend_message": "No matching tests for trend analysis."}

        # 5. GENERATE INSIGHT & RETURN STATE UPDATE
        insight = self._generate_llm_insight(current_report.get('patient_name'), trends)

        return {
            "status": "success",
            "trends": trends,
            "trend_insight": insight
        }