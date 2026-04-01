import re
from datetime import datetime
from logger_config import logger

UNITS = [
    "mg/dL","g/dL","mmol/L","IU/L","U/L",
    "cells/mcL","/mcL","/µL","/uL","%","ng/mL",
    "pg/mL","mEq/L","µg/dL","/cumm", "µIU/mL", "uIU/mL"
]

NON_TEST_KEYWORDS = [
    "age", "gender", "lab no", "registration", "reg no",
    "patient", "doctor", "hospital", "report", "date",
    "collection", "visit", "id", "number"
]


# ---------------- CLEANING ----------------

def clean_line(line):
    line = re.sub(r"\.{2,}", " ", line)
    line = re.sub(r"\s+", " ", line)
    return line.strip()


def is_valid_test(line):
    line_lower = line.lower()

    # skip unwanted keywords
    if any(word in line_lower for word in NON_TEST_KEYWORDS):
        return False

    # skip descriptive sentences
    if len(line.split()) > 6:
        return False

    if any(word in line_lower for word in [
        "available", "control", "additional", "test"
    ]):
        return False

    # must contain unit OR range
    if not any(unit.lower() in line_lower for unit in UNITS) and "-" not in line:
        return False

    # must contain both text + number
    if not re.search(r"[a-zA-Z]", line):
        return False

    if not re.search(r"\d", line):
        return False

    return True


# ---------------- EXTRACTION ----------------

def extract_numbers(text):
    nums = re.findall(r"\d+(?:,\d{3})*(?:\.\d+)?", text)
    return [float(n.replace(",", "")) for n in nums]


def detect_unit(text):
    for unit in UNITS:
        if unit.lower() in text.lower():
            return unit
    return ""


# ---------------- METADATA ----------------
def extract_patient_name(text):
    lines = text.split("\n")

    for line in lines:
        line = line.strip()

        # skip unwanted lines
        if any(x in line.lower() for x in [
            "generated", "reported", "collected",
            "page", "lab", "dr", "pathology"
        ]):
            continue

        # detect name (2–3 words, alphabets only)
        words = line.split()
        if 2 <= len(words) <= 4:
            if all(w.replace('.', '').isalpha() for w in words):
                return " ".join(words)

    return "Unknown"


def extract_report_date(text):
    matches = re.findall(r"\d{2} [A-Za-z]{3}, \d{4}", text)
    if matches:
        return matches[0]
    return None


# ---------------- MAIN PARSER ----------------

def parse_doctor_report(report_text):

    try:
        logger.info("Starting Doctor Report Parsing")

        medical_data = []

        lines = re.split(r'\n+', report_text)

        for line in lines:

            line = clean_line(line)

            if not line:
                continue

            if not is_valid_test(line):
                continue

            numbers = extract_numbers(line)
            if not numbers:
                continue

            value = numbers[0]
            unit = detect_unit(line)

            reference_range = "N/A"
            status = "Unknown"

            # range detection
            range_match = re.search(
                r"(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)",
                line
            )

            if range_match:
                low = float(range_match.group(1))
                high = float(range_match.group(2))

                reference_range = f"{low}-{high}"

                if value < low:
                    status = "Low"
                elif value > high:
                    status = "High"
                else:
                    status = "Normal"

            elif len(numbers) >= 3:
                low = numbers[1]
                high = numbers[2]

                reference_range = f"{low}-{high}"

                if value < low:
                    status = "Low"
                elif value > high:
                    status = "High"
                else:
                    status = "Normal"

            # test name extraction
            test_name_match = re.match(r"([A-Za-z\s\(\)\-]+)", line)
            if not test_name_match:
                continue

            test_name = test_name_match.group(1).strip()
            test_name = test_name.title().replace(",", "").strip()

            formatted_value = f"{value} {unit}".strip()

            medical_data.append({
                "test": test_name,
                "value": formatted_value,
                "reference_range": reference_range,
                "status": status
            })

            logger.info(f"Extracted {test_name}: {formatted_value} ({status})")

        # -------- Metadata --------
        patient_name = extract_patient_name(report_text)
        report_date = extract_report_date(report_text)

        logger.info(f"Patient Name: {patient_name}")
        logger.info(f"Report Date: {report_date}")

        logger.info("Doctor Report Parsing Completed")

        return {
            "patient_name": patient_name,
            "report_date": str(report_date) if report_date else None,
            "lab_results": medical_data
        }

    except Exception as e:
        logger.error(f"Doctor Parsing error: {str(e)}")
        return {}
    

# ----------------- Test ------------------------

if __name__ == "__main__":
    from processing.pdf_reader import read_pdf
    file_path = "sample_data/Glucose_report.pdf"
    print("\n==== Running Doctor Parser Text ====\n")

    text = read_pdf(file_path)

    print("\n==== Extracted Text ====\n")
    print(text[:500])

    # Parse report
    result = parse_doctor_report(text)
    print("\n==== Parsed Output ====\n")
    print(f"Patient Name: {result.get('patient_name')}")
    print(f"Report Date: {result.get('report_date')}\n")

    if result.get("lab_results"):
        for item in result["lab_results"]:
            print(item)
    else:
        print("No lab results extracted")