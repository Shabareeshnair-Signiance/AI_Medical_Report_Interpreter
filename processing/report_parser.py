import re
from logger_config import logger
from processing.pdf_reader import read_pdf


# Known medical tests dictionary
KNOWN_TESTS = [
    "Hemoglobin",
    "WBC",
    "RBC",
    "Platelet",
    "Glucose",
    "Cholesterol",
    "HDL Cholesterol",
    "LDL Cholesterol",
    "Triglycerides",
    "Creatinine",
    "Urea",
    "Sodium",
    "Potassium",
    "Calcium",
    "Vitamin D",
    "TSH"
]


def is_known_test(line):
    for test in KNOWN_TESTS:
        if test.lower() in line.lower():
            return True
    return False


def parse_medical_report(report_text):

    try:

        logger.info("Starting medical report parsing")

        medical_data = {}

        lines = report_text.split("\n")

        for line in lines:

            line = line.strip()

            if not line:
                continue

            # Filter only lines containing known test names
            if not is_known_test(line):
                continue

            # Detect value + unit
            value_pattern = r"(\d+\.?\d*)\s*(mg/dL|g/dL|mmol/L|cells/mcL|/mcL|%)?"

            value_match = re.search(value_pattern, line)

            if not value_match:
                continue

            value = float(value_match.group(1))
            unit = value_match.group(2) if value_match.group(2) else ""

            # Detect reference range
            range_pattern = r"(\d+\.?\d*)\s*-\s*(\d+\.?\d*)"

            range_match = re.search(range_pattern, line)

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

            # Detect test name
            for test in KNOWN_TESTS:

                if test.lower() in line.lower():

                    medical_data[test] = {
                        "value": value,
                        "unit": unit,
                        "reference_range": reference_range,
                        "status": status
                    }

                    logger.info(f"Extracted {test}: {value} {unit} ({status})")

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