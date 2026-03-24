from paddleocr import PaddleOCR
from pdf2image import convert_from_path
import os
from logger_config import logger

# initializing OCR model (load once)
ocr = PaddleOCR(use_angle_cls = True, lang="en")

def extract_text_from_image(image_path):
    try:
        logger.info(f"Processing image: {image_path}")

        result = ocr.ocr(image_path)

        extracted_text = []
        for line in result[0]:
            extracted_text.append(line[1][0])

        text = "\n".join(extracted_text)
        logger.info("Image OCR completed successfully")

        return text
    
    except Exception as e:
        logger.error(f"Error Processing Image: {str(e)}")
        return ""
    

def extract_text_from_pdf(pdf_path):
    try:
        logger.info(f"Processing PDF: {pdf_path}")

        pages = convert_from_path(pdf_path)
        full_text = []

        for i, page in enumerate(pages):
            temp_image = f"temp_page_{i}.png"
            page.save(temp_image, "PNG")

            logger.info(f"Processing page: {i + 1}")

            text = extract_text_from_image(temp_image)
            full_text.append(text)

            os.remove(temp_image)

        logger.info("PDF OCR completed successfully")
        return "\n\n".join(full_text)
    
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        return ""
    

def extract_text(file_path):
    logger.info(f"Starting OCR for file: {file_path}")

    if file_path.lower().endswith(".pdf"):
        return extract_text_from_pdf(file_path)
    else:
        return extract_text_from_image(file_path)
    

# Testing the OCR model
if __name__ == "__main__":
    file_path = "sample_data/Medical_report.pdf"
    text = extract_text(file_path)
    print(text)