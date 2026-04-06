from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from llm.llm_provider import get_llm
from logger_config import logger
import json
import re
import os
from datetime import datetime
from dateutil import parser


# -------- NEW: Date Normalization (The Safety Net) --------
def normalize_date(date_str):
    """
    Converts messy dates like '03-Apr-2026' or '04/03/26' into '2026-04-03'.
    If parsing fails, it uses the current system date.
    """
    if not date_str or str(date_str).strip() in ["", "None", "Not Available"]:
        return datetime.now().strftime("%Y-%m-%d")
    
    try:
        # fuzzy=True helps ignore extra text around the date
        parsed_dt = parser.parse(str(date_str), fuzzy=True)
        return parsed_dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        logger.warning(f"Date parsing failed for: {date_str}. Falling back to today.")
        return datetime.now().strftime("%Y-%m-%d")

# -------- Clean LLM Output --------
def clean_llm_output(response):
    response = re.sub(r"```json|```", "", response).strip()

    match = re.search(r"\{.*\}", response, re.DOTALL)
    if match:
        return match.group(0)

    return response


# -------- Load Prompt --------
def load_prompt():
    with open("prompts/doctor_extractor.txt", "r", encoding="utf-8") as f:
        return f.read()


# -------- File Date Fallback --------
def get_file_date(file_path):
    try:
        timestamp = os.path.getctime(file_path)
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
    except Exception as e:
        logger.warning(f"File date extraction failed: {str(e)}")
        return None


# -------- LLM Extractor --------
def llm_doctor_extractor(report_text, file_path=None):
    try:
        logger.info("LLM Doctor Extractor Started")

        prompt_text = load_prompt()
        curr_date_str = datetime.now().strftime("%Y-%m-%d")

        prompt = PromptTemplate(
            input_variables=["report_text", "current_date"],
            template=prompt_text
        )

        llm = get_llm()
        chain = prompt | llm | StrOutputParser()

        # Inject current_date so the LLM has a default reference
        response = chain.invoke({
            "report_text": report_text,
            "current_date": curr_date_str
        })

        cleaned = clean_llm_output(response)

        try:
            data = json.loads(cleaned)
        except Exception as e:
            logger.error(f"JSON Parsing Failed: {str(e)}")
            return {
                "patient_name": "Unknown",
                "report_date": curr_date_str,
                "lab_results": []
            }

        # -------- APPLY NORMALIZATION HERE --------
        # This fixes the 'Sorting Error' in TrendAgent
        # ensuring all required keys exist so app doesn't crash with a Keyerror
        required_keys = ["patient_name", "age", "dob", "pid", "lab_results"]
        for key in required_keys:
            if key not in data:
                data[key] = "Not Available" if key != "lab_results" else []

        # 2. Adding the PID cleaning logic below
        if isinstance(data.get("pid"), str):
            data["pid"] = data["pid"].replace("PID:", "").replace("ID:", "").strip()

        # 3. Adding the Age Normalization logic here
        if data.get("age"):
            age_match = re.search(r"(\d+)", str(data["age"]))
            if age_match:
                data["age"] = age_match.group(1)

        # 4. Existing date normalization
        raw_date = data.get("report_date")
        data["report_date"] = normalize_date(raw_date)
       
        logger.info(f"Final Normalized Date: {data['report_date']}")

        # 5. Hybrid Table or Value Normalization (Tier 3)
        # This fixes the "Result: 185.00 mg/dL" splitting issue and ensures numeric values
        if "lab_results" in data and isinstance(data["lab_results"], list):
            for item in data["lab_results"]:
                # Ensure every sub-key exists to prevent Error 4 in the UI
                for sub_key in ["test", "value", "unit", "reference_range", "status"]:
                    if sub_key not in item:
                        item[sub_key] = "Not Available"

                # TIER 2 & 3: Clean numeric values and separate units
                # If 'value' contains '185.00 mg/dL', this splits them properly
                raw_val = str(item.get("value", ""))
                # Regex to find the first number (float or int)
                val_match = re.search(r"(\d+\.?\d*)", raw_val)
                
                if val_match:
                    numeric_val = val_match.group(1)
                    # If the unit was accidentally included in 'value', try to move it to 'unit'
                    if "mg/dL" in raw_val.lower() and item["unit"] == "Not Available":
                        item["unit"] = "mg/dL"
                    
                    item["value"] = numeric_val # Force value to be just the number
                
                # Cleanup Test Names (Removes extra colons or 'Investigation' labels)
                item["test"] = item["test"].replace("Investigation:", "").strip()

        logger.info("LLM Extraction Successful")

        return data

    except Exception as e:
        logger.error(f"LLM Extractor Error: {str(e)}")
        return {
            "patient_name": "Unknown",
            "report_date": datetime.now().strftime("%Y-%m-%d"),
            "lab_results": []
        }


# -------- Testing --------
# if __name__ == "__main__":

#     from processing.pdf_reader import read_pdf

#     #file_path = "sample_data/Glucose_report.pdf"
#     #file_path = "sample_data/platelet_report.pdf"
#     file_path = "sample_data/Sample Report.pdf"

#     print("\n==== Running LLM Extractor Test ====\n")

#     text = read_pdf(file_path)

#     result = llm_doctor_extractor(text, file_path)

#     print("\n==== Output ====\n")
#     print(result)