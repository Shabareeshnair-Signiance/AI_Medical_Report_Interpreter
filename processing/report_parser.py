import re
from logger_config import logger

# extended medical units
UNITS = [
    "mg/dL","g/dL","mmol/L","IU/L","U/L",
    "cells/mcL","/mcL","/µL","/uL","%","ng/mL",
    "pg/mL","mEq/L","µg/dL","/cumm"
]

IGNORE_WORDS = [
    "less than","greater than","risk","information","performed",
    "page","accession","doctor","patient","report","address",
    "hospital","printed","date","collection","visit"
]


def clean_line(line):
    line = re.sub(r"\.{2,}", " ", line)
    line = re.sub(r"\s+", " ", line)
    return line.strip()


# def contains_unit(line):
#     for unit in UNITS:
#         if unit.lower() in line.lower():
#             return unit
#     return None


def is_interpretation(line):
    return any(word in line.lower() for word in IGNORE_WORDS)


# -------- HELPER --------
def extract_numbers(text):
    """
    Extract numbers including comma values like 150,000
    """
    nums = re.findall(r"\d{1,3}(?:,\d{3})*(?:\.\d+)?", text)
    return [float(n.replace(",", "")) for n in nums]

def detect_unit(text):
    for unit in UNITS:
        if unit.lower() in text.lower():
            return unit
    return ""


# -------- MAIN PARSER --------
def parse_medical_report(report_text):

    try:
        logger.info("Starting medical report parsing")

        medical_data = []
        #lines = report_text.split("\n")

        # Merge broken lines (important for multi-page and tables)
        #report_text = report_text.replace("\n", " ")
        chunks = re.split(r'\n+', report_text)

        for chunk in chunks:

            line = clean_line(chunk)

            if not line or is_interpretation(line):
                continue

            numbers = extract_numbers(line)
            if not numbers:
                continue

            unit = detect_unit(line)

            # First number = result value
            value = numbers[0]

            reference_range = "N/A"
            status = "Unknown"

            # range detection
            range_match = re.search(
                r"(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*[-–]\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)",
                line
            )

            if range_match:
                low = float(range_match.group(1).replace(",", ""))
                high = float(range_match.group(2).replace(",", ""))

                reference_range = f"{int(low)}-{int(high)}"

                if value < low:
                    status = "Low"
                elif value > high:
                    status = "High"
                else:
                    status = "Normal"

            # If at least 3 numbers → assume value + range
            elif len(numbers) >= 3:
                low = numbers[1]
                high = numbers[2]

                reference_range = f"{int(low)}–{int(high)}"

                if value < low:
                    status = "Low"
                elif value > high:
                    status = "High"
                else:
                    status = "Normal"

            # fallback: try range pattern with commas
            else:
                range_match = re.search(
                    r"(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*-\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)",
                    line
                )

                if range_match:
                    low = float(range_match.group(1).replace(",", ""))
                    high = float(range_match.group(2).replace(",", ""))

                    reference_range = f"{int(low)}–{int(high)}"

                    if value < low:
                        status = "Low"
                    elif value > high:
                        status = "High"
                    else:
                        status = "Normal"

            # extract test name match safely
            test_name = re.split(r'\d', line)[0].strip()

            if len(test_name) < 3:
                continue

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