import re
from logger_config import logger

# common medical units
UNITS = [
    "mg/dL","g/dL","mmol/L","IU/L","U/L",
    "cells/mcL","/mcL","/µL","%","ng/mL",
    "pg/mL","mEq/L","µg/dL"
]

# words indicating non-lab text
IGNORE_WORDS = [
    "less than","greater than","risk","information","performed",
    "page","accession","doctor","patient","report","address",
    "hospital","printed","date","collection","visit"
]


def clean_line(line):
    line = re.sub(r"\.{2,}", " ", line)
    line = re.sub(r"\s+", " ", line)
    return line.strip()


def contains_unit(line):
    for unit in UNITS:
        if unit.lower() in line.lower():
            return unit
    return None


def is_interpretation(line):
    for word in IGNORE_WORDS:
        if word in line.lower():
            return True
    return False


# -------- MAIN PARSER --------
def parse_medical_report(report_text):

    try:

        logger.info("Starting medical report parsing")

        medical_data = []

        lines = report_text.split("\n")

        for line in lines:

            line = clean_line(line)

            if not line:
                continue

            if is_interpretation(line):
                continue

            unit = contains_unit(line)

            if not unit:
                continue

            # detect numeric value
            value_match = re.search(r"\b\d+\.?\d*\b", line)

            if not value_match:
                continue

            value = float(value_match.group())

            # detect reference range
            range_match = re.search(r"(\d+\.?\d*)\s*-\s*(\d+\.?\d*)", line)

            reference_range = None
            status = "Unknown"

            if range_match:

                low = float(range_match.group(1))
                high = float(range_match.group(2))

                reference_range = f"{low}–{high}"

                if value < low:
                    status = "Low"
                elif value > high:
                    status = "High"
                else:
                    status = "Normal"

            # detect test name
            test_name = line.split(value_match.group())[0].strip()

            if len(test_name) < 3:
                continue

            if not any(char.isalpha() for char in test_name):
                continue

            # CLEAN TEST NAME
            test_name = test_name.title().replace(",", "").strip()

            # FORMAT VALUE WITH UNIT
            formatted_value = f"{value} {unit}"

            medical_data.append({
                "test": test_name,
                "value": formatted_value,
                "reference_range": reference_range if reference_range else "N/A",
                "status": status
            })

            logger.info(f"Extracted {test_name}: {formatted_value} ({status})")

        logger.info("Medical report parsing completed")

        return {
            "lab_results": medical_data
        }

    except Exception as e:

        logger.error(f"Parsing error: {str(e)}")

        return {}