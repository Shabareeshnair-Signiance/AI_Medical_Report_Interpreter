import json
import os
import re
from dotenv import load_dotenv
from logger_config import logger

# Importing from the new doctors ocr module
from .ocr_doctor import ocr_engine
from .parser_ocr import parse_ocr_medical_report, BIOMARKER_MAP
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# 1. THE TEXT PROMPT (For Native PDFs)
def build_text_prompt(ocr_text):
    return f"""
You are a STRICT OCR PARSER. Your ONLY job is to copy data from the raw text into a JSON format. You have NO medical background. Do not guess or infer.

### THE ABSOLUTE LAWS:
1. **ZERO HALLUCINATION**: If a reference range or unit is not explicitly visible in the text, you MUST output an empty string "". 
2. **CAPTURE EVERYTHING**: Extract all medical tests, no matter how obscure.
3. **LITERAL COPY-PASTE**: Extract exactly what is written. Do not swap numbers.

### OUTPUT SCHEMA (STRICT JSON ONLY):
{{
  "patient_name": "Extract patient name if present, else ''",
  "pid": "Extract Patient ID, Reg No, or Lab No if present, else ''",
  "report_date": "Extract Date of Report if present, else ''",
  "age": "Extract age if present, else ''",
  "dob": "Extract DOB if present, else ''",
  "lab_results": [
    {{
      "test": "Exact name from text",
      "value": "Exact patient result string/number",
      "unit": "Exact unit or ''",
      "reference_range": "Exact range from text or ''",
      "status": "Normal/High/Low/Abnormal"
    }}
  ]
}}

### RAW TEXT:
{ocr_text}
"""

# 2. THE VISION PROMPT (For Scans & Images)
VISION_SYSTEM_PROMPT = """
You are a STRICT MEDICAL VISION PARSER. Look at the uploaded medical report images.
Your ONLY job is to extract tabular medical data into JSON. You have NO medical background. Do not guess or infer.

### THE ABSOLUTE LAWS:
1. **ZERO HALLUCINATION**: If a reference range or unit is not explicitly visible in the image, output an empty string "".
2. **CAPTURE EVERYTHING**: Extract every test, measurement, fluid, or biological term you see in the tables.
3. **LITERAL COPY-PASTE**: Extract exactly what is written in the image. Do not swap numbers.
4. **COMPOUND METRICS SPLIT**: If you see a combined test like "Blood Pressure" with a slashed value (e.g., 170/110), you MUST split it into two distinct JSON objects: "Blood Pressure - Systolic" (value: 170) and "Blood Pressure - Diastolic" (value: 110). Split the reference ranges accordingly (e.g., "130 / 80" becomes "< 130" and "< 80").

### HOW TO PARSE THE IMAGES:
- Read the tables row by row. Follow the column headers exactly.
- **Test Name**: Usually the alphabetic phrase in the first column.
- **Patient Result**: The specific value belonging to the patient.
- **Reference Range**: The "normal" boundary (e.g., "10 - 20", "< 50", "Negative").
- **Anti-Swap Protocol**: Read left-to-right. Do not mix up the Patient Result with the Reference Range.

### OUTPUT SCHEMA (STRICT JSON ONLY):
{
  "patient_name": "Extract patient name from header if present, else ''",
  "pid": "Extract Patient ID, Reg No, or Lab No if present, else ''",
  "report_date": "Extract Date of Report if present, else ''",
  "age": "Extract age if present, else ''",
  "dob": "Extract DOB if present, else ''",
  "lab_results": [
    {
      "test": "Standardize obvious abbreviations like 'FBS' -> 'Glucose'",
      "value": "Exact patient result string/number",
      "unit": "Exact unit or ''",
      "reference_range": "Exact range from text or ''",
      "status": "Normal/High/Low/Abnormal"
    }
  ]
}
"""


# 3. EXTRACTION ENGINES
def extract_with_text_llm(ocr_text):
    """Fallback for when regex fails on native digital text."""
    try:
        logger.info("Running LLM Text Extraction Fallback")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a medical informatics expert specializing in lab report synthesis."},
                {"role": "user", "content": build_text_prompt(ocr_text)}
            ],
            temperature=0
        )
        output = response.choices[0].message.content.strip()
        output = re.sub(r"```json|```", "", output).strip()
        return json.loads(output)
    except Exception as e:
        logger.error(f"LLM Text Extraction failed: {str(e)}")
        return {"lab_results": []}

def extract_with_vision_llm(base64_images):
    """The Smart Lane: Sends Base64 images directly to GPT-4o for visual parsing."""
    try:
        logger.info("Running LLM VISION Clinical Extraction")
        
        # Build the payload with the instruction text
        messages = [
            {"role": "system", "content": VISION_SYSTEM_PROMPT},
            {"role": "user", "content": [
                {"type": "text", "text": "Extract all lab results from these images into the requested JSON format."}
            ]}
        ]
        
        # Append every page of the PDF/Image to the user message
        for b64_img in base64_images:
            messages[1]["content"].append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{b64_img}"
                }
            })

        # Using gpt-4o-mini as it supports Vision and is cost-effective
        response = client.chat.completions.create(
            model="gpt-4o-mini", 
            messages=messages,
            temperature=0,
            max_tokens=2000
        )

        output = response.choices[0].message.content.strip()
        output = re.sub(r"```json|```", "", output).strip()
        data = json.loads(output)
        
        return data

    except Exception as e:
        logger.error(f"LLM Vision Extraction failed: {str(e)}")
        return {"lab_results": []}


# 4. DATA STANDARDIZATION
import logging
logger = logging.getLogger(__name__)

def calculate_clinical_status(item):
    val_str = str(item.get("value", ""))
    ref_raw = str(item.get("reference_range", "")).strip()
    
    val_match = re.search(r"(\d+(?:\.\d+)?)", val_str)
    if not val_match: return "Normal"
    value = float(val_match.group(1))

    try:
        # FIX 1: Support the word "to" alongside hyphens
        range_match = re.search(r"([\d.]+)\s*(?:[-–]|to)\s*([\d.]+)", ref_raw, re.IGNORECASE)
        if range_match:
            low, high = float(range_match.group(1)), float(range_match.group(2))
            if value < low: return "Low"
            if value > high: return "High"
            return "Normal"

        # FIX 2: Forgiving "Less Than" check
        less_match = re.search(r"[<≤]\s*([\d.]+)", ref_raw)
        if less_match:
            limit = float(less_match.group(1))
            return "Normal" if value <= limit else "High"

        # FIX 3: Forgiving "Greater Than" check
        greater_match = re.search(r"[>≥]\s*([\d.]+)", ref_raw)
        if greater_match:
            limit = float(greater_match.group(1))
            return "Normal" if value >= limit else "Low"

        # FIX 4: Support "Up to X"
        upto_match = re.search(r"up\s*to\s*([\d.]+)", ref_raw, re.IGNORECASE)
        if upto_match:
            limit = float(upto_match.group(1))
            return "Normal" if value <= limit else "High"
        
        # Fix 5: Standalone number fallback
        # it will catch the cases where the AI just outputs 130 instead of <130
        standalone_match = re.search(r"^([\d.]+)$", ref_raw.strip())
        if standalone_match:
            limit = float(standalone_match.group(1))
            return "Normal" if value <= limit else "High"

    except Exception as e:
        logger.error(f"Status Calculation Error: {e}")
    
    return "Normal"


def normalize_biomarkers(data):
    """Applies BIOMARKER_MAP to standardize names across labs."""
    for item in data.get("lab_results", []):
        name = item.get("test", "").upper()
        # Ensure BIOMARKER_MAP is imported or defined at the top of your file
        if name in BIOMARKER_MAP:
            item["test"] = BIOMARKER_MAP[name]
    return data


# 5. THE MAIN DOCTOR PIPELINE
def run_doctor_ocr_pipeline(file_path):
    """
    Master Router: Routes document to Fast Lane (Text) or Smart Lane (Vision).
    """
    logger.info(f"Processing File for Doctor Dashboard: {file_path}")

    # 1. Use the NEW Document Router
    doc_data = ocr_engine.extract_document(file_path)

    if doc_data.get("mode") == "error":
        return {"lab_results": [], "error": doc_data.get("message")}
    
    parsed_data = {"lab_results": []}

    # 2. FAST LANE (Native Digital Text from PyMuPDF)
    if doc_data.get("mode") == "text":
        raw_text = doc_data.get("content")
        parsed_data = parse_ocr_medical_report(raw_text)

        if len(parsed_data.get("lab_results", [])) < 2:
            logger.warning("Regex parser struggled with layout. Switching to LLM Text Fallback.")
            parsed_data = extract_with_text_llm(raw_text)

    # 3. SMART LANE (Vision AI for Scans/Images)
    elif doc_data.get("mode") == "vision":
        base64_images = doc_data.get("images", [])
        logger.info(f"Routing {len(base64_images)} pages to Vision AI...")
        parsed_data = extract_with_vision_llm(base64_images)

    # 4. Standardize Data & Calculate Status
    parsed_data = normalize_biomarkers(parsed_data)
    for item in parsed_data.get("lab_results", []):
        item["status"] = calculate_clinical_status(item)
        
    return parsed_data


# TESTING BLOCK

# if __name__ == "__main__":
#     import hashlib
#     import sys
#     import os
    
#     # Safely import your DB file from the parent directory
#     sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
#     from storage.medical_history_db import save_doctor_vision_report

#     # CHANGED: Pointing to the Biochemistry report
#     test_file = "sample_data/Medical_report.pdf"
    
#     print("\n" + "="*50)
#     print(" DOCTOR OCR PIPELINE & DATABASE TEST (BIOCHEMISTRY)")
#     print("="*50 + "\n")
    
#     # 1. Run the Vision Pipeline
#     final_json = run_doctor_ocr_pipeline(test_file)
#     print("\n[1] Vision OCR Complete. Extracted", len(final_json.get("lab_results", [])), "results.")
    
#     # 2. Mock Metadata (Matching Shankar Nair's Biochemistry report)
#     mock_metadata = {
#         "patient_name": "Shankar Nair",
#         "age": "66",
#         "dob": "05/01/1959",
#         "report_date": "10/07/2025", 
#         "pid": "5114470" # Updated Lab No for this specific report
#     }

#     # 3. Mock Agent Results (Updated to match Glucose/Creatinine context)
#     mock_agent_results = {
#         "trend_insight": "Elevated Fasting Blood Sugar (178 mg/dL) indicating hyperglycemia. Kidney function (Creatinine/Urea) remains normal.",
#         "clinical_suggestion": "Recommend HbA1c test and clinical correlation for diabetes management."
#     }

#     # 4. Generate a NEW fake file hash for the test so it saves as a separate entry
#     test_hash = hashlib.sha256(b"test_biochem_report_v1").hexdigest()

#     # 5. Save to the Database
#     print("\n[2] Attempting to save to medical_history.db...")
#     success = save_doctor_vision_report(test_hash, mock_metadata, final_json, mock_agent_results)

#     if success:
#         print("\n[✓] SUCCESS: Data securely saved to the database!")
#         print("    -> You can now pull this data for the Trend Analysis Graph.")
#     else:
#         print("\n[X] ERROR: Failed to save to the database.")