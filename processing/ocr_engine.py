import easyocr
from pdf2image import convert_from_path
from PIL import Image
import numpy as np
import cv2
import os
from logger_config import logger


# Load OCR model once
reader = easyocr.Reader(['en'], gpu=False)


# Generate multiple preprocessing variants
def generate_variants(image):
    image = np.array(image)

    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    variants = []

    # Variant 1: Original grayscale
    variants.append(gray)

    # Variant 2: Adaptive Threshold
    th1 = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )
    variants.append(th1)

    # Variant 3: Otsu Threshold
    _, th2 = cv2.threshold(
        gray, 0, 255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    variants.append(th2)

    # Variant 4: Contrast Enhanced
    eq = cv2.equalizeHist(gray)
    variants.append(eq)

    return variants


# Score OCR output
def score_ocr(result):
    if not result:
        return 0
    total_conf = sum([conf for (_, _, conf) in result])
    return total_conf / len(result)


# Run OCR on multiple variants and select best
def run_best_ocr(image):
    variants = generate_variants(image)

    all_results = []

    for var in variants:
        try:
            result = reader.readtext(var, detail=1)
            all_results.append(result)
        except:
            continue

    if not all_results:
        return []

    # Select best result
    best_result = max(all_results, key=score_ocr)

    # Filter low-confidence text
    clean_lines = [
        text.strip()
        for (_, text, conf) in best_result
        if conf > 0.5 and len(text.strip()) > 2
    ]

    return clean_lines


# Image OCR
def extract_text_from_image(image_path):
    try:
        logger.info(f"Processing image: {image_path}")

        image = Image.open(image_path)

        clean_lines = run_best_ocr(image)

        # Keep structure (IMPORTANT)
        text = "\n".join(clean_lines)

        return text.strip()

    except Exception as e:
        logger.error(f"Image OCR failed: {str(e)}")
        return ""


# PDF OCR
def extract_text_from_pdf(pdf_path):
    try:
        logger.info(f"Processing PDF: {pdf_path}")

        pages = convert_from_path(pdf_path, dpi=300)

        full_text = ""

        for i, page in enumerate(pages):
            logger.info(f"Processing page {i+1}")

            clean_lines = run_best_ocr(page)

            page_text = "\n".join(clean_lines)

            full_text += f"\n--- page {i+1} ---\n{page_text}\n"

        return full_text.strip()

    except Exception as e:
        logger.error(f"PDF OCR failed: {str(e)}")
        return ""


# Main function
def extract_text(file_path):
    ext = os.path.splitext(file_path)[1].lower()

    if ext in ['.jpg', '.jpeg', '.png']:
        return extract_text_from_image(file_path)

    elif ext == '.pdf':
        return extract_text_from_pdf(file_path)

    else:
        logger.warning(f"Unsupported file format: {ext}")
        return ""