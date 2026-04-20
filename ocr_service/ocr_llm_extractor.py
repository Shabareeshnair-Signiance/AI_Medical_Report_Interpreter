import json
import os
import re
from dotenv import load_dotenv
from logger_config import logger
from ocr_service.ocr_engine import extract_text
from .ocr_parser import parse_ocr_medical_report
from openai import OpenAI

# loading environment variables
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("OPENAI_API_KEY not found in .env file")

client = OpenAI(api_key=api_key)

def clean_ocr_text(text):
    text = re.sub(r'\s+', ' ', text)
    text = text.replace(" .", ".")
    return text.strip()

# prompt for text fast lane
def build_prompt(ocr_text):
    return f"""
You are a medical data extraction assistant.

Extract ONLY lab test results from the given OCR text.

STRICT RULES:
- Extract ONLY medical test entries (Creatinine, Urea, FBS, etc.)
- Ignore comments, notes, patient info
- Extract MULTIPLE tests if present

IMPORTANT:
- Extract value even if unit is missing
- Extract reference range if available, else leave empty
- Accept values like "Positive 2+", "Nil", "10-15", etc.
- DO NOT calculate status

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

# Safe JSON Parser
def safe_json_load(text):
    try:
        text = text.strip()
        text = re.sub(r"```json|```", "", text).strip()
        return json.loads(text)
    except Exception as e:
        logger.error(f"JSON parsing failed: {str(e)}")
        return {"lab_results": []}
    
# LLM for text fast lane fallback
def extract_with_llm(ocr_text):
    try:
        logger.info("Switching to LLM text extraction...")

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages = [
                {"role": "system", "content": "You extract structured medical data."},
                {"role": "user", "content": build_prompt(ocr_text)}
            ],
            temperature=0
        )

        output = response.choices[0].message.content.strip()
        data = safe_json_load(output)

        logger.info("LLM text extraction successful")

        return data
    
    except Exception as e:
        logger.error(f"LLM Extraction failed: {str(e)}")
        return {"lab_results": []}
    

# New Vision AI Extractor a Smart Lane
def extract_with_vision(base64_images):
    try:
        logger.info("Starting Vision AI extraction for scanned reports...")

        vision_prompt = """
You are a meticulous medical data extraction assistant.

Extract EVERY SINGLE lab test result from the provided images of a medical report. 

STRICT RULES:
1. EXTRACT EXHAUSTIVELY: Do not skip any rows.
2. STRICT ROW ALIGNMENT (CRITICAL): You must read the table strictly horizontally, row by row. NEVER assign a value or reference range from one row to the "Test Name" of another row. Pay special attention to short test names like "pH" so you do not skip them and shift the data.
3. URINALYSIS ALERT: Pay close attention to qualitative tests (Color, Appearance, etc.). Their reference ranges are words (e.g., "Yellowish", "Clear", "Negative"). You MUST extract these text-based reference ranges.
4. EXACT EXTRACTION: Extract the "Test Name", "Value", and "Reference Range" EXACTLY as they appear.
5. DETERMINE THE STATUS: 
    - For numbers: Compare value to range -> Output "High", "Low", or "Normal".
    - For text: Compare value to range -> Output "Abnormal" or "Normal".

Return ONLY JSON matching this schema exactly:
{
  "lab_results": [
    {
      "test": "",
      "value": "",
      "reference_range": "",
      "status": ""
    }
  ]
}
"""

        # constructing the multi modal payload
        content_payload = [{"type": "text", "text": vision_prompt}]
        for b64 in base64_images:
            content_payload.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
            })

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a clinical data parser. You extract complete tables with perfect horizontal row alignment. You never shift or misalign data."},
                {"role": "user", "content": content_payload}
            ],
            temperature=0
        )

        output = response.choices[0].message.content.strip()
        data = safe_json_load(output)

        logger.info("Vision AI extraction successful")
        return data

    except Exception as e:
        logger.error(f"Vision AI extraction failed: {str(e)}")
        return {"lab_results": []}
    
# Helper to extract numbers
def extract_number(text):
    match = re.search(r"\d+\.?\d*", text)
    return float(match.group()) if match else None

# Status calculation
def calculate_status(value_text, reference_range):
    try:
        # 1. QUALITATIVE TEXT COMPARISON FIRST
        val_str = str(value_text).strip().lower()
        ref_str = str(reference_range).strip().lower()

        if val_str and ref_str:
            # Exact text match or close substring (e.g., "negative" == "negative", "yellow" in "yellowish")
            if val_str == ref_str or val_str in ref_str or ref_str in val_str:
                return "Normal"
            
            # Abnormal text flags (If reference is Negative/Nil, but value is Positive/Trace/1+)
            if ref_str in ["negative", "nil", "absent", "none"]:
                if any(flag in val_str for flag in ["positive", "trace", "+", "present"]):
                    return "Abnormal"

        # 2. QUANTITATIVE NUMERIC COMPARISON
        value = extract_number(value_text)

        if value is None:
            return "Unknown"  # If it's text but didn't match the qualitative rules above

        ref = reference_range.replace(" ", "")

        # Case 1: Range (e.g., 0.6-1.2)
        if "-" in ref:
            nums = re.findall(r"\d+\.?\d*", ref)
            if len(nums) >= 2:
                low, high = float(nums[0]), float(nums[1])
                if value < low:
                    return "Low"
                elif value > high:
                    return "High"
                else:
                    return "Normal"

        # Case 2: <100
        elif "<" in ref:
            limit = extract_number(ref)
            if limit is not None:
                return "Normal" if value < limit else "High"

        # Case 3: >126
        elif ">" in ref:
            limit = extract_number(ref)
            if limit is not None:
                return "Normal" if value > limit else "Low"

    except Exception as e:
        logger.error(f"Status calculation error: {str(e)}")

    return "Unknown"

# Helper function for Qualitative status resolver
def resolve_qualitative_status(value, reference):
    """Safety net function specifically for text-based medical results (Urinalysis)."""
    if not value or not reference:
        return "Unknown"
        
    val_str = str(value).strip().lower()
    ref_str = str(reference).strip().lower()

    # 1. Direct or partial match (e.g., "yellow" in "yellowish")
    if val_str == ref_str or val_str in ref_str or ref_str in val_str:
        return "Normal"
        
    # 2. Known abnormal flags against a healthy baseline
    healthy_baselines = ["clear", "negative", "nil", "absent", "none", "normal"]
    if ref_str in healthy_baselines:
        # If the reference is healthy, but the value isn't, it's abnormal.
        if val_str not in healthy_baselines:
            return "Abnormal"
            
    return "Unknown"

# post processing stage
def post_process(data):
    """
    Passes data through, but catches any 'Unknown' statuses left by the LLM 
    and applies our strict qualitative helper logic.
    """
    for item in data.get("lab_results", []):
        status = item.get("status", "")
        val = item.get("value", "")
        ref = item.get("reference_range", "")

        # If the LLM failed to calculate status, or left it blank
        if not status or status.lower() == "unknown":
            # Fire the helper function!
            item["status"] = resolve_qualitative_status(val, ref)
            
    return data

# validation processing stage
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

# Main Pipeline were every functions is connected
def run_ocr_pipeline(file_path):
    try:
        logger.info("Starting Medical Document Pipeline")

        extracted_data = extract_text(file_path)

        if not extracted_data or extracted_data.get("mode") == "error":
            logger.warning(f"Extraction failed: {extracted_data.get('message', 'Unknown error')}")
            return {"lab_results": []}
        
        # Route 1: Fast Lane (digital text)
        if extracted_data.get("mode") == "text":
            logger.info("Processing via Digital Text Pipeline")
            ocr_text = extracted_data.get("content", "")

            # Step 1: Regex
            parsed_data = parse_ocr_medical_report(ocr_text)

            if is_valid_lab_results(parsed_data):
                logger.info("Regex parsing successful")
                return post_process(parsed_data)
            
            # Step 2: LLM Fallback for text
            logger.warning("Regex failed -> switching to LLM Fallback")
            llm_result = extract_with_llm(ocr_text)
            return post_process(llm_result)
        
        # Rooute 2: Smart Lane (Scanned PDFs or Image Reports)
        elif extracted_data.get("mode") == "vision":
            logger.info("Processing via Vision AI Pipeline (Scanned Report)")
            base64_images = extracted_data.get("images", [])
            vison_result = extract_with_vision(base64_images)
            return post_process(vison_result)
        
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}")
        return {"lab_results": []}
    
# testing the vision llm extractor
# if __name__ == "__main__":

#     # Testing explicitly with the Scanned report as requested
#     #file_path = "sample_data/Medical_report.pdf"
#     #file_path = "sample_data/Scanned_report.pdf"
#     file_path = "sample_data/bp_report_scanned.pdf"
#     #file_path = "sample_data/scan_report.pdf"

#     print("\n==== MEDICAL REPORT PIPELINE TEST ====\n")

#     result = run_ocr_pipeline(file_path)

#     print("\n==== FINAL OUTPUT ====\n")

#     if result.get("lab_results"):
#         for item in result["lab_results"]:
#             print(json.dumps(item, indent=2))
#     else:
#         print("No lab results extracted")