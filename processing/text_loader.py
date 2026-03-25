from processing.pdf_reader import read_pdf
from processing.ocr_engine import extract_text

def get_text(file_path):
    try:
        text = read_pdf(file_path)

        # suppose text is good then will use this logic
        if text and len(text.strip()) > 100:
            return text
        
        # fallback to OCR
        return extract_text(file_path)
    
    except:
        return extract_text(file_path)