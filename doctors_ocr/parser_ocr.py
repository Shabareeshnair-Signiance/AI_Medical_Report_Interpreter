import re
from logger_config import logger

# 1. Enhanced Clinical Units
UNITS = [
    "mg/dL", "g/dL", "mmol/L", "IU/L", "U/L", "g/L",
    "cells/mcL", "/mcL", "/µL", "/uL", "%", "ng/mL",
    "pg/mL", "mEq/L", "µg/dL", "/cumm", "µIU/mL", "uIU/mL"
]

# 2. Key Biomarker Normalization (Ensures Trend Analysis works)
# If OCR sees "S. Glucose", it maps to "Glucose" for the Chart.js logic.
BIOMARKER_MAP = {
    "S. GLUCOSE": "Glucose",
    "GLUCOSE (FASTING)": "Glucose",
    "HB1AC": "HbA1c",
    "HEMOGLOBIN": "Hemoglobin",
    "S. CREATININE": "Creatinine",
    "SERUM CHOLESTEROL": "Cholesterol"
}

def extract_reference_range(line):
    """
    Finds patterns like '70 - 110', '< 200', '> 40'.
    Crucial for the Chart.js 'Normal Zones'.
    """
    range_match = re.search(r"(\d+(?:\.\d+)?\s*[-–]\s*\d+(?:\.\d+)?|(?><|>=|<=|>)\s*\d+(?:\.\d+)?)", line)
    return range_match.group(1) if range_match else "N/A"

def parse_line_horizontal(line):
    """
    The 'Doctor-Grade' logic: Extracts everything from a single horizontal line.
    Example: 'Glucose Fasting ... 110 mg/dL ... 70-100'
    """
    # 1. Extract Unit
    unit_found = ""
    for u in UNITS:
        if u.lower() in line.lower():
            unit_found = u
            break

    # 2. Extract Numbers (Result and potentially Range)
    nums = re.findall(r"(\d+(?:\.\d+)?)", line)
    if not nums:
        return None
    
    # The first number is usually the result
    value = nums[0]

    # 3. Reference Range
    ref_range = extract_reference_range(line)

    # 4. Extract test name (Clean everything else out)
    name_part = line
    # Remove unit, vallue, and range from the string to leave just the name
    name_part = re.sub(unit_found, "", name_part, flags = re.I)
    name_part = re.sub(ref_range, "", name_part)
    name_part = re.sub(value, "", name_part, count = 1)
    # clean noise symbols
    name_part = re.sub(r"[^a-zA-Z\s\(\)]", "", name_part).strip().title()

    # Standardize name for the Trend Analysis
    final_name = BIOMARKER_MAP.get(name_part.upper(), name_part)

    if len(final_name) < 3: return None

    return {
        "test": final_name,
        "value": value,
        "unit": unit_found,
        "reference_range": ref_range
    }

def parse_ocr_medical_report(report_text):
    """Main entry point for the Doctor Dashboard OCR Parser"""
    try:
        logger.info("Starting Doctor-level Horizontal Parsing")
        lines = [l.strip() for l in report_text.split("\n") if l.strip()]
        medical_data = []

        # Section keywords to trigger parsing
        start_keywords = ["test_name", "biochemistry", "result", "report", "hematology"]
        stop_keywords = ["comment", "note", "clinical", "disclaimer", "authorized"]

        in_table = False

        for line in lines:
            ll = line.lower()

            if any(k in ll for k in start_keywords):
                in_table = True
                continue

            if any(k in ll for k in stop_keywords):
                in_table = False
                continue

            if in_table:
                # try to parse the line as a single horizontal data row
                extracted = parse_line_horizontal(line)
                if extracted:
                    medical_data.append(extracted)
                    logger.info(f"Extracted: {extracted['test']} = {extracted['value']}")

        return {"lab_results": medical_data}
    
    except Exception as e:
        logger.error(f"Doctor Parser Error: {str(e)}")
        return {"lab_results": [], "error": str(e)}