import re
from logger_config import logger
#from processing.pdf_reader import read_pdf
from transformers import pipeline

# Loading medical NER Model
logger.info("Loading biomedical NER model")

ner_pipeline = pipeline(
    "ner",
    model="d4data/biomedical-ner-all",
    aggregation_strategy="simple"
)

# common medical units
UNITS = [
    "mg/dL","g/dL","mmol/L","IU/L","U/L",
    "cells/mcL","/mcL","/µL","%","ng/mL",
    "pg/mL","mEq/L","µg/dL"
]

# words indicating interpretation text
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


# Extracting NER entities
def extract_entities(text):

    entities = ner_pipeline(text)

    ner_results = []

    for ent in entities:
        ner_results.append({
            "text": ent["word"],
            "type": ent["entity_group"],
            "score": float(ent["score"])
        })

    return ner_results


# Main parser
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

            medical_data.append({
                "test": test_name,
                "value": value,
                "unit": unit,
                "reference_range": reference_range,
                "status": status
            })

            logger.info(f"Extracted {test_name}: {value} {unit} ({status})")

        # Run NER but do not return full entities to avoid large logs
        ner_entities = extract_entities(report_text)

        logger.info(f"NER detected {len(ner_entities)} entities")

        logger.info("Medical report parsing completed")

        return {
            "lab_results": medical_data
        }

    except Exception as e:

        logger.error(f"Parsing error: {str(e)}")

        return {}


# Testing the parser
# if __name__ == "__main__":
#     report_path = "data/uploads/Sample Report.pdf"

#     print("\n============================")

#     report_text = read_pdf(report_path)

#     if not report_text:
#         print("Failed to read report")
#         exit()

#     print("Report loaded Successfully\n")
#     parsed_data = parse_medical_report(report_text)

#     print("\n================================")
#     print("Extracted Lab Results:\n")

#     for item in parsed_data["lab_results"]:

#         print(
#             f"{item['test']} → {item['value']} {item['unit']} | "
#             f"Range: {item['reference_range']} | Status: {item['status']}"
#         )

#     print("\n================================")
#     print("NER Detected Entities:\n")

#     for ent in parsed_data["entities"][:20]:

#         print(ent)