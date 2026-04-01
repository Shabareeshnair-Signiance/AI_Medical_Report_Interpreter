import re
from thefuzz import process

class TrendAgent:
    def __init__(self):
        # Add common aliases to help the matcher
        self.aliases = {
            "fbs": "glucose fasting",
            "hba1c": "hemoglobin a1c",
            "cbc": "complete blood count"
        }

    def _get_float_value(self, value_str):
        """Extracts number from strings like '12.5 g/dL'"""
        if not value_str: return None
        clean_str = str(value_str).replace(',', '')
        match = re.search(r"(\d+(\.\d+)?)", clean_str)
        return float(match.group(1)) if match else None

    def analyze(self, current_report, history):
        # SCENARIO 1 & 2: New User or No History
        if not history:
            return {
                "status": "new_patient",
                "message": "This is a new patient or no previous reports found. Trend analysis unavailable.",
                "trends": []
            }

        # Get the most recent report from history
        last_report = history[-1]
        
        # SCENARIO 4 Check: Prevent comparing a report against itself
        if current_report.get('report_date') == last_report.get('report_date'):
            return {"status": "duplicate", "message": "This report date matches an existing entry."}

        # SCENARIO 3: Matching Logic
        trends = []
        # Map old tests for quick lookup: { "test_name": "value" }
        old_data = {t['test'].lower().strip(): t['value'] for t in last_report['lab_results']}

        for item in current_report['lab_results']:
            curr_name = item['test'].lower().strip()
            
            # Find match in old data
            match_name = None
            if curr_name in old_data:
                match_name = curr_name
            else:
                # Fuzzy match (catch 'Platelets' vs 'Platelet Count')
                best_match, score = process.extractOne(curr_name, list(old_data.keys()))
                if score > 85:
                    match_name = best_match

            if match_name:
                v_new = self._get_float_value(item['value'])
                v_old = self._get_float_value(old_data[match_name])

                if v_new is not None and v_old is not None and v_old != 0:
                    change = ((v_new - v_old) / v_old) * 100
                    trends.append({
                        "test": item['test'],
                        "current": item['value'],
                        "previous": old_data[match_name],
                        "change_pct": round(change, 2),
                        "status": "stable" if abs(change) < 5 else ("improving" if change < 0 else "worsening") 
                        # Note: 'improving' vs 'worsening' depends on the specific test!
                    })

        if not trends:
            return {"status": "no_matches", "message": "No comparable tests found in history."}

        return {
            "status": "success",
            "patient_name": current_report.get('patient_name'),
            "trends": trends
        }