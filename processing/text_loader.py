from processing.pdf_reader import read_pdf
from processing.ocr_engine import extract_text
import re


# Detect table type
def detect_table_type(text):
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    column_score = 0
    non_column_score = 0

    for line in lines:
        words = line.split()

        if len(words) >= 4:
            column_score += 1
        if len(words) <= 2:
            non_column_score += 1

    return "column" if column_score > non_column_score else "non_column"


# Reconstruct table from broken OCR
def reconstruct_table(text):
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    reconstructed = []
    buffer = []

    for line in lines:
        # If line has a number → start or continue a test row
        if re.search(r'\d', line):
            buffer.append(line)
        else:
            if buffer:
                buffer.append(line)

        # If buffer is big enough → finalize
        if len(buffer) >= 3:
            reconstructed.append(" ".join(buffer))
            buffer = []

    # Add remaining
    if buffer:
        reconstructed.append(" ".join(buffer))

    return "\n".join(reconstructed)


# Main function
def get_text(file_path):
    try:
        text = read_pdf(file_path)

        # If digital PDF works → return directly
        if text and len(text.strip()) > 100:
            return text

        # OCR fallback
        ocr_text = extract_text(file_path)

        # Detect type
        table_type = detect_table_type(ocr_text)

        # Process based on type
        if table_type == "column":
            processed_text = reconstruct_table(ocr_text)
        else:
            processed_text = ocr_text

        return processed_text

    except:
        return extract_text(file_path)