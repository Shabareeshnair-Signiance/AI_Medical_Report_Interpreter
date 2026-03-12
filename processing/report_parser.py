import re
from logger_config import logger
from processing.pdf_reader import read_pdf


def parse_medical_report(report_text: str) -> dict:
    """
    Parses extracted medical report text and identifies
    test names with their corresponding values and units.

    Args:
        report_text (str): Raw text extracted from PDF.

    Returns:
        dict: Structured medical data
    """

    try:
        logger.info("Starting to parse the medical report")

        medical_data = {}

        # Splitting text into lines
        lines = report_text.split("\n")

        logger.info(f"Total lines found in report: {len(lines)}")

        # Regex pattern for lab results
        pattern = r"([A-Za-z\s]+)\s+([\d.]+)\s*(mg/dL|g/dL|cells/mcL|/mcL|%)?"

        for line in lines:

            line = line.strip()

            if not line:
                continue

            match = re.search(pattern, line)

            if match:

                test_name = match.group(1).strip()
                value = match.group(2)
                unit = match.group(3) if match.group(3) else ""

                full_value = f"{value} {unit}".strip()

                medical_data[test_name] = full_value

                logger.info(f"Extracted: {test_name} -> {full_value}")

        logger.info("Medical report parsing completed")

        return medical_data

    except Exception as e:
        logger.error(f"Error parsing medical report: {str(e)}")
        return {}

# Test block (Runs parser using the real PDF)

if __name__ == "__main__":

    pdf_path = "data/uploads/Sample Report.pdf"

    logger.info("Reading medical report PDF")

    report_text = read_pdf(pdf_path)

    if report_text:

        print("\n===== EXTRACTED TEXT =====\n")
        print(report_text)

        parsed_data = parse_medical_report(report_text)

        print("\n===== PARSED MEDICAL DATA =====\n")
        print(parsed_data)

    else:
        print("Failed to extract text from PDF.")