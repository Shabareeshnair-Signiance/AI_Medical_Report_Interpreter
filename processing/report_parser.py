import re
from logger_config import logger
from processing.pdf_reader import read_pdf


# common medical units
UNITS = [
    "mg/dL","g/dL","mmol/L","IU/L","U/L",
    "cells/mcL","/mcL","/µL","%","ng/mL",
    "pg/mL","mEq/L","µg/dL"
]


# words indicating interpretation text
IGNORE_WORDS = [
    "less than",
    "greater than",
    "risk",
    "information",
    "performed",
    "page",
    "accession",
    "doctor",
    "patient",
    "report"
]


def clean_line(line):

    line = re.sub(r"\.{2,}", " ", line)
    line = re.sub(r"\s+", " ", line)

    return line.strip()


def contains_unit(line):

    for unit in UNITS:
        if unit in line:
            return unit
    return None


def is_interpretation(line):

    for word in IGNORE_WORDS:
        if word in line.lower():
            return True
    return False


def parse_medical_report(report_text):

    try:

        logger.info("Starting medical report parsing")

        medical_data = {}

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

            # extract reference range
            range_match = re.search(r"(\d+\.?\d*)\s*-\s*(\d+\.?\d*)", line)

            reference_range = None
            status = "Unknown"

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

            # detect test name
            test_name = line.split(value_match.group())[0].strip()

            if len(test_name) < 3:
                continue

            if not any(char.isalpha() for char in test_name):
                continue

            medical_data[test_name] = {
                "value": value,
                "unit": unit,
                "reference_range": reference_range,
                "status": status
            }

            logger.info(f"Extracted {test_name}: {value} {unit} ({status})")

        logger.info("Medical report parsing completed")

        return medical_data

    except Exception as e:

        logger.error(f"Parsing error: {str(e)}")

        return {}


if __name__ == "__main__":
    pdf_path = "data/uploads/Sample Report.pdf"
    text = read_pdf(pdf_path)
    parsed = parse_medical_report(text)
    print("\nParsed Medical Data:\n")
    print(parsed)