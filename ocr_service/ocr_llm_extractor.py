import json
import os
import re
from dotenv import load_dotenv
from logger_config import logger
from ocr_service.ocr_engine import extract_text
from ocr_service.ocr_parser import parse_ocr_medical_report
from openai import OpenAI

# Load environment variables
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("OPENAI_API_KEY not found in .env file")

client = OpenAI(api_key=api_key)


# -------- PROMPT --------
def build_prompt(ocr_text):
    return f"""
You are a medical data extraction assistant.

Extract ONLY lab test results from the given OCR text.

STRICT RULES:
- Extract ONLY medical test entries (Creatinine, Urea, FBS, etc.)
- Ignore comments, notes, patient info
- Extract MULTIPLE tests if present

IMPORTANT:
- ALWAYS include unit in value (e.g., "0.87 mg/dL")
- Extract reference range exactly as shown
- DO NOT guess status unless clearly mentioned

Return ONLY JSON:
{{
  "lab_results": [
    {{
      "test": "",
      "value": "",
      "reference_range": "",
      "status": ""
    }}
  ]
}}

OCR TEXT:
{ocr_text}
"""


# -------- SAFE JSON PARSER --------
def safe_json_load(text):
    try:
        text = text.strip()

        # remove ```json blocks if present
        text = re.sub(r"```json|```", "", text).strip()

        return json.loads(text)

    except Exception as e:
        logger.error(f"JSON parsing failed: {str(e)}")
        return {"lab_results": []}


# -------- LLM --------
def extract_with_llm(ocr_text):
    try:
        logger.info("Switching to LLM extraction...")

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You extract structured medical data."},
                {"role": "user", "content": build_prompt(ocr_text)}
            ],
            temperature=0
        )

        output = response.choices[0].message.content.strip()

        data = safe_json_load(output)

        logger.info("LLM extraction successful")

        return data

    except Exception as e:
        logger.error(f"LLM extraction failed: {str(e)}")
        return {"lab_results": []}


# -------- STATUS CALCULATION --------
def calculate_status(value, reference_range):
    try:
        value = float(value)

        # Case 1: range like 10 - 20
        if "-" in reference_range:
            low, high = reference_range.split("-")
            low = float(low.strip())
            high = float(high.strip())

            if value < low:
                return "Low"
            elif value > high:
                return "High"
            else:
                return "Normal"

        # Case 2: <100
        if "<" in reference_range:
            limit = float(reference_range.replace("<", "").strip())
            return "High" if value >= limit else "Normal"

        # Case 3: >126
        if ">" in reference_range:
            limit = float(reference_range.replace(">", "").strip())
            return "High" if value > limit else "Normal"

    except:
        pass

    return "Unknown"


# -------- POST PROCESS --------
def post_process(data):
    for item in data.get("lab_results", []):
        try:
            val = item["value"].split()[0]
            ref = item["reference_range"]

            item["status"] = calculate_status(val, ref)

        except:
            item["status"] = "Unknown"

    return data


# -------- VALIDATION --------
def is_valid_lab_results(data):
    results = data.get("lab_results", [])

    if not results:
        return False

    for item in results:
        test = item.get("test", "").lower()

        if any(word in test for word in [
            "comment", "clinical", "note", "correlate",
            "infection", "disease", "overdose"
        ]):
            return False

    return True


# -------- MAIN PIPELINE --------
def run_ocr_pipeline(file_path):
    try:
        logger.info("Starting OCR pipeline")

        ocr_text = extract_text(file_path)

        if not ocr_text:
            logger.warning("OCR returned empty text")
            return {"lab_results": []}

        # Step 1: Regex
        parsed_data = parse_ocr_medical_report(ocr_text)

        if is_valid_lab_results(parsed_data):
            logger.info("Regex parsing successful")
            return post_process(parsed_data)  # ✅ FIXED

        # Step 2: LLM fallback
        logger.warning("Regex failed → switching to LLM")

        llm_result = extract_with_llm(ocr_text)
        llm_result = post_process(llm_result)

        return llm_result

    except Exception as e:
        logger.error(f"OCR pipeline failed: {str(e)}")
        return {"lab_results": []}


# -------- TEST --------
if __name__ == "__main__":

    file_path = "sample_data/Medical_report.pdf"

    print("\n==== OCR PIPELINE TEST ====\n")

    result = run_ocr_pipeline(file_path)

    print("\n==== FINAL OUTPUT ====\n")

    if result.get("lab_results"):
        for item in result["lab_results"]:
            print(item)
    else:
        print("No lab results extracted")