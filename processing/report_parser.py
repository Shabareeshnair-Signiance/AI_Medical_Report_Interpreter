import re
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


def clean_line(line):
    line = re.sub(r"\.{2,}", " ", line)
    line = re.sub(r"\s+", " ", line)
    return line.strip()


def is_valid_test(line):
    line_lower = line.lower()

    if any(word in line_lower for word in NON_TEST_KEYWORDS):
        return False

    if not re.search(r"\d", line):
        return False

    return True


def extract_numbers(text):
    nums = re.findall(r"\d+(?:,\d{3})*(?:\.\d+)?", text)
    return [float(n.replace(",", "")) for n in nums]


def detect_unit(text):
    for unit in UNITS:
        if unit.lower() in text.lower():
            return unit
    return ""


def parse_medical_report(report_text):

    try:
        logger.info("Starting medical report parsing")

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

            unit = detect_unit(line)
            value = numbers[0]

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

            # improved test name extraction
            test_name_match = re.match(r"([A-Za-z0-9\s\(\)\-]+)", line)
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

        logger.info("Medical report parsing completed")

        return {"lab_results": medical_data}

    except Exception as e:
        logger.error(f"Parsing error: {str(e)}")
        return {}


# ---------------- TEST ----------------
# from processing.pdf_reader import read_pdf

# if __name__ == "__main__":

#     file_path = "sample_data/Glucose_report.pdf"

#     extracted_text = read_pdf(file_path)

#     print("\n=== EXTRACTED TEXT ===\n")
#     print(extracted_text[:1000])

#     result = parse_medical_report(extracted_text)

#     print("\n=== PARSED OUTPUT ===\n")
#     for item in result["lab_results"]:
#         print(item)