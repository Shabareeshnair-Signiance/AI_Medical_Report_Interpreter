import cv2
import numpy as np

def generate_variants(gray_img):
    """Returns list of preprocessed images to improve OCR acuarcy"""
    if len(gray_img.shape) == 3:
        gray_img = cv2.cvtColor(gray_img, cv2.COLOR_BGR2GRAY)

    variants = []
    # Variant 1: Dilation (helps with thin/faded fonts)
    kernel = np.ones((2,2), np.uint8)
    variants.append(cv2.dilate(gray_img, kernel, iterations=1))

    # Variant 2: Sharpness enhancement
    sharpen_kernel = np.array([[-1,-1,-1], [-1, 9, -1], [-1, -1, -1]])
    variants.append(cv2.filter2D(gray_img, -1, sharpen_kernel))

    # Variant 3: Standard Thresholding
    _, th = cv2.threshold(gray_img, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants.append(th)

    return variants

def score_ocr(result):
    if not result: return 0
    return sum([conf for (_, _, conf) in result]) / len(result)