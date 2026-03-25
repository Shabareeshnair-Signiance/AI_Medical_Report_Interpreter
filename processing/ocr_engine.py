import easyocr
from pdf2image import convert_from_path
from PIL import Image
import numpy as np
import cv2
import os
from logger_config import logger


# OCR reader initiating by loading once
reader = easyocr.Reader(['en'], gpu=False)

# Image preprocessing
def preprocess_image(image):
    """Converting image to grayscale for better OCR"""
    image = np.array(image)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Improving contrast
    gray = cv2.equalizeHist(gray)

    # reducing noise
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    # Threshold
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

    return thresh   

# Image OCR
def extract_text_from_image(image_path):
    """Extracting text from image file"""
    try:
        logger.info(f"Processing image: {image_path}")

        image = Image.open(image_path)
        image = preprocess_image(image)

        results = reader.readtext(image, detail=0, paragraph=True)
        text = " ".join(results)

        # cleaning + normalizing
        text = " ".join(text.split())
        text = text.lower()

        return text
    
    except Exception as e:
        logger.error(f"Image OCR failed: {str(e)}")
        return ""
    
# PDF OCR
def extract_text_from_pdf(pdf_path):
    """Extracting text from scanned PDF"""
    try:
        logger.info(f"Processing PDF: {pdf_path}")

        pages = convert_from_path(pdf_path)

        full_text = ""

        for i, page in enumerate(pages):
            logger.info(f"Processing page {i+1}")

            image = preprocess_image(page)
            results = reader.readtext(image, detail=0)

            full_text += " ".join(results) + "\n"
        return full_text.strip()
    
    except Exception as e:
        logger.error(f"PDF OCR failed: {str(e)}")
        return ""
    
# Building Main OCR Function
def extract_text(file_path):
    """Handling both image and PDF"""
    ext = os.path.splitext(file_path)[1].lower()

    if ext in ['.jpg', '.jpeg', '.png']:
        return extract_text_from_image(file_path)
    
    elif ext == '.pdf':
        return extract_text_from_pdf(file_path)
    
    else:
        logger.warning(f"Unsupported fiile format: {ext}")
        return ""
    

# Testing the OCR service
if __name__ == "__main__":
    test_file = "sample_data/Medical_report.pdf"

    logger.info("Starting OCR Test...")

    text = extract_text(test_file)

    print("\n---- OCR Output ----\n")
    print(text[:1000])