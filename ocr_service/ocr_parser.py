import re
from logger_config import logger

# EXPANDED UNITS
# Added many standard hematology, biochemistry, and hormone units
UNITS = [
    "mg/dL", "g/dL", "mmol/L", "IU/L", "U/L", "cells/mcL", "/mcL", "/µL", "/uL", 
    "%", "ng/mL", "pg/mL", "mEq/L", "µg/dL", "/cumm", "µIU/mL", "uIU/mL",
    "fL", "pg", "g/L", "10^6/uL", "10^3/uL", "10*3/uL", "umol/L", "nmol/L", 
    "mOsm/kg", "mIU/mL", "ng/dL", "/hpf", "/lpf",
    "mgdl", "gdl"  # Common OCR/PDF extraction spacing mistakes
]

# STRICT KEYWORDS
NON_TEST_KEYWORDS = [
    "age", "gender", "lab no", "registration", "reg no",
    "patient", "doctor", "hospital", "report", "date",
    "collection", "visit", "id", "number", "name",
    "address", "phone", "final", "sample", "bio", "lab",
    "biochemistry", "hematology", "pathology", "test name",
    "result", "reference", "unit", "value"
]

def clean_line(line):
    line = re.sub(r"\.{2,}", " ", line)
    line = re.sub(r"\s+", " ", line)
    return line.strip()

def detect_unit(text):
    text_lower = text.lower().replace(" ", "")
    for unit in UNITS:
        # Check against cleaned text to avoid slash/space issues
        if unit.lower().replace("/", "") in text_lower:
            return unit.replace("mgdl", "mg/dL").replace("gdl", "g/dL")
    return ""

def extract_reference_range(text):
    """Attempts to find a range pattern like '10-20' or '<5.0' in the text chunk."""
    range_match = re.search(r"(\d+\.?\d*\s*-\s*\d+\.?\d*|<[ ]*\d+\.?\d*|>[ ]*\d+\.?\d*)", text)
    return range_match.group(1).strip() if range_match else ""

def is_valid_test_name(name):
    if len(name) < 3:
        return False
    if any(keyword in name.lower() for keyword in NON_TEST_KEYWORDS):
        return False
    # Must contain at least one letter
    if not re.search(r"[a-zA-Z]", name):
        return False
    return True

# SMARTER TEXT PARSER
def parse_ocr_medical_report(report_text):
    try:
        logger.info("Starting Native Text Parsing (Regex Fast Lane)")

        lines = [clean_line(l) for l in report_text.split("\n") if l.strip()]
        medical_data = []

        # We use a sliding window approach. 
        # We look at 3 lines at a time to catch data whether it's horizontal or vertical.
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Stop parsing if we hit the footer notes
            if any(word in line.lower() for word in ["comments", "clinical", "note", "end of report"]):
                break

            # Look for a number in the current line
            num_match = re.search(r"(\d+\.?\d*)", line)
            
            if num_match:
                # We found a potential value. Let's look around it (current line + next 2 lines)
                window_text = " ".join(lines[max(0, i-1):min(len(lines), i+2)])
                
                unit = detect_unit(window_text)
                ref_range = extract_reference_range(window_text)
                
                # If we have a number and a unit, we almost certainly have a medical result
                if unit:
                    value = num_match.group(1)
                    
                    # Try to extract the test name from the preceding line or the start of the current line
                    test_name_candidate = ""
                    if i > 0 and not re.search(r"\d", lines[i-1]):
                        test_name_candidate = lines[i-1]
                    else:
                        # Strip the numbers, units, and ranges from the text to leave just the name
                        clean_candidate = re.sub(r"(\d+\.?\d*|-|<|>)", "", line).strip()
                        for u in UNITS:
                            clean_candidate = re.sub(re.escape(u), "", clean_candidate, flags=re.IGNORECASE)
                        test_name_candidate = clean_candidate

                    test_name = re.sub(r"[^a-zA-Z\s\(\)\-]", "", test_name_candidate).strip().title()

                    if is_valid_test_name(test_name):
                        medical_data.append({
                            "test": test_name,
                            "value": f"{value}",
                            "reference_range": ref_range if ref_range else "N/A",
                            "status": "Unknown" # Status will be calculated downstream or left Unknown if regex
                        })
                        logger.info(f"Regex Extracted -> {test_name}: {value} {unit}")
                        
                        # Skip ahead to avoid double-counting the same cluster of lines
                        i += 1 

            i += 1

        logger.info(f"Regex parsing completed. Found {len(medical_data)} results.")
        
        # If the regex found nothing (or too little), it returns an empty array,
        # which safely triggers the LLM fallback in ocr_llm_extractor.py
        if len(medical_data) < 2:
            return {"lab_results": []}

        return {"lab_results": medical_data}

    except Exception as e:
        logger.error(f"Text Parsing error: {str(e)}")
        return {"lab_results": []}


# -------- TESTING BLOCK --------
# if __name__ == "__main__":
#     from ocr_service.ocr_engine import extract_text
#     import os

#     # Ensure you are pointing to a DIGITAL PDF to test this regex lane
#     file_path = "sample_data/Medical_report.pdf"

#     print("\n=== FAST LANE (TEXT) PARSER TEST ===\n")

#     if not os.path.exists(file_path):
#         print(f"Error: File not found at {file_path}")
#     else:
#         # Run through the router
#         extracted_data = extract_text(file_path)

#         # Check if the router actually put it in the Fast Lane
#         if extracted_data.get("mode") == "text":
#             native_text = extracted_data.get("content", "")
            
#             print("=== NATIVE TEXT DETECTED ===\n")
#             print(native_text[:300] + "...\n")

#             # Parsing
#             result = parse_ocr_medical_report(native_text)
#             print("=== PARSED OUTPUT ===\n")

#             if result.get("lab_results"):
#                 for item in result["lab_results"]:
#                     print(item)
#             else:
#                 print("[!] No lab results extracted. Regex criteria not met (Will trigger LLM fallback in production).")
                
#         else:
#             print(f"\n[!] Router sent this to {extracted_data.get('mode').upper()} mode.")
#             print("This parser is strictly for native text. Use ocr_llm_extractor.py to test the Vision AI lane.")