import re
from logger_config import logger

# Units (expanded for OCR noise cases)
UNITS = [
    "mg/dL","g/dL","mmol/L","IU/L","U/L",
    "cells/mcL","/mcL","/µL","/uL","%","ng/mL",
    "pg/mL","mEq/L","µg/dL","/cumm", "µIU/mL", "uIU/mL",
    "mgdl","gdl"  # OCR mistakes
]

# Strict filtering (ONLY medical test lines allowed)
NON_TEST_KEYWORDS = [
    "age","gender","lab no","registration","reg no",
    "patient","doctor","hospital","report","date",
    "collection","visit","id","number","name",
    "address","phone","final","sample","bio","lab"
]


# Clean OCR noise
def clean_line(line):
    line = re.sub(r"\.{2,}", " ", line)
    line = re.sub(r"\s+", " ", line)
    return line.strip()


# Strict validation (important for OCR)
def is_valid_test(line):
    line_lower = line.lower()

    # remove non-medical lines
    if any(word in line_lower for word in NON_TEST_KEYWORDS):
        return False

    # must contain number
    if not re.search(r"\d", line):
        return False

    # must contain alphabet (test name)
    if not re.search(r"[a-zA-Z]", line):
        return False

    return True


# Extract numbers
def extract_numbers(text):
    nums = re.findall(r"\d+(?:,\d{3})*(?:\.\d+)?", text)
    return [float(n.replace(",", "")) for n in nums]


# Detect unit (robust for OCR mistakes)
def detect_unit(text):
    text_lower = text.lower().replace(" ", "")

    for unit in UNITS:
        if unit.lower().replace("/", "") in text_lower:
            return unit.replace("mgdl", "mg/dL").replace("gdl", "g/dL")

    return ""


# Extract test name smarter (OCR-safe)
def extract_test_name(line):
    # Remove numbers and units
    cleaned = re.sub(r"\d+(?:\.\d+)?", "", line)

    # Remove common noise words
    cleaned = re.sub(r"(range|result|value|test)", "", cleaned, flags=re.I)

    # Keep only alphabets + spaces
    cleaned = re.sub(r"[^a-zA-Z\s\(\)\-]", "", cleaned)

    cleaned = cleaned.strip().title()

    # Avoid very small/invalid names
    if len(cleaned) < 3:
        return None

    return cleaned


# Main OCR parser
def parse_ocr_medical_report(report_text):
    try:
        logger.info("Starting OCR parsing (multi-line aware)")

        lines = [clean_line(l) for l in report_text.split("\n") if l.strip()]
        medical_data = []

        i = 0
        while i < len(lines) - 2:

            line1 = lines[i]
            line2 = lines[i+1]
            line3 = lines[i+2]

            # Skip noise
            if any(word in line3.lower() for word in NON_TEST_KEYWORDS):
                i += 1
                continue

            nums = extract_numbers(line1)

            # Pattern: value → unit → test name
            if nums and len(nums) == 1:
                value = nums[0]
                unit = detect_unit(line2)
                test_name = line3

                if unit and len(test_name) > 3:

                    test_name = re.sub(r"[^a-zA-Z\s]", "", test_name).title()

                    medical_data.append({
                        "test": test_name,
                        "value": f"{value} {unit}",
                        "reference_range": "N/A",
                        "status": "Unknown"
                    })

                    logger.info(f"Extracted {test_name}: {value} {unit}")

                    i += 3
                    continue

            i += 1

        logger.info("OCR parsing completed")

        return {"lab_results": medical_data}

    except Exception as e:
        logger.error(f"OCR Parsing error: {str(e)}")
        return {}
    

# testing the ocr parser code
if __name__ == "__main__":
    from ocr_engine import extract_text

    file_path = "sample_data/Medical_report.pdf"

    print("\n=== OCR + PARSER TEST ===\n")

    # OCR
    ocr_text = extract_text(file_path)

    print("\n=== OCR TEXT (first 500 chars) ===\n")
    print(ocr_text[:500])

    # Parsing
    result = parse_ocr_medical_report(ocr_text)
    print("\n=== Parsed Output ===\n")

    if result.get("lab_results"):
        for item in result["lab_results"]:
            print(item)

    else:
        print("No lab results extracted")