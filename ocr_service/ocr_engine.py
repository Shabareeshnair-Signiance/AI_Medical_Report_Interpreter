import os
import base64
import io
from pdf2image import convert_from_path
from PIL import Image
from logger_config import logger

try:
    import fitz
except ImportError:
    fitz = None
    logger.warning("PyMuPDF (fitz) not installed. 'Fast Lane' digital PDF extraction will fall back to Vision.")


class PatientVisionEngine:
    def __init__(self):
        pass

    def pil_to_base64(self, image):
        """Converts a PIL Image to a base64 string for the OpenAI Vision API."""
        buffer = io.BytesIO()

        # converting to RGB to ensure JPEG compatibility (drops alpha channel if any)
        image = image.convert('RGB')

        # quality 85 reduces API payload size while keeping text crystal clear
        image.save(buffer, format='JPEG', qulaity = 85)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    def extract_digital_text(self, pdf_path):
        """Attempts to extract native text from a digital PDF."""
        if not fitz:
            return None
        try:
            doc = fitz.open(pdf_path)
            text = ""
            for page in doc:
                text += page.get_text() + "\n"

            # suppose PDF is a scan, text length will be near 0
            # if its a digital it will easily be > 100 characters.
            if len(text.strip()) > 100:
                return text.strip()
            return None
        except Exception as e:
            logger.error(f"PyMuPDF Extraction Error: {str(e)}")
            return None
        
    def extract_document(self, file_path):
        """
        Master function: Routes to Fast Lane (Text) or Smart Lane (Vision).
        Return a dictionary indicating the extraction mode and content.
        """
        ext = os.path.splitext(file_path)[1].lower()

        try:
            if ext == '.pdf':
                # 1. trying fast Lane
                digital_text = self.extract_digital_text(file_path)
                if digital_text:
                    logger.info(f"[{os.path.basename(file_path)}] Native text detected. Routing to fast Lane.")
                    return {"mode": "text", "content": digital_text}
                
                # 2. Smart Lane (Vision Conversion)
                logger.info(f"[{os.path.basename(file_path)}] Scanned PDF detected. Converting to Vision Base64...")
                # DPI 200 is perfect for OpenAI Vision. high enough to read
                pages = convert_from_path(file_path, dpi=200)
                base64_images = []

                for i, page in enumerate(pages):
                    b64 = self.pil_to_base64(page)
                    base64_images.append(b64)
                    logger.info(f"Page {i+1} converted for Vision AI.")

                return {"mode": "vision", "images": base64_images}
            
            elif ext in ['.jpg', '.jpeg', '.png']:
                # Direct Image to Smart Lane
                logger.info(f"[{os.path.basename(file_path)}] Image file detected. Routing to Vision Base64..")
                image = Image.open(file_path)
                b64 = self.pil_to_base64(image)
                return {"mode": "vision", "images": [b64]}
            
            else:
                logger.error(f"Unsupported file format: {ext}")
                return {"mode": "error", "message": f"Unsupported format: {ext}"}
            
        except Exception as e:
            logger.error(f"Document processing failed: {str(e)}")
            return {"mode": "error", "message": str(e)}
        
# Initializing the Engine globally
patient_ocr_engine = PatientVisionEngine()

# Preserved original function name to prevent breaking downstream
def extract_text(file_path):
    return patient_ocr_engine.extract_document(file_path)

if __name__ == "__main__":
    TEST_FILE = "sample_data/Medical_report.pdf"

    print(f"\n{'='*60}")
    print(f"PATIENT VISION ENGINE ROUTER: TERMINAL TEST")
    print(f"\n{'='*60}")

    if not os.path.exists(TEST_FILE):
        print(f"Error: File not Found at {TEST_FILE}. Please check your sample_data directory.")
    else:
        result = extract_text(TEST_FILE)

        print(f"\n Processing Complete....")
        print(f"[*] chosen mode: {result.get('mode').upper()}")

        if result.get("mode") == "text":
            print(f"[*] Text Length: {len(result.get('content'))} characters.")
            print(f"[*] Preview: {result.get('content')[:200]}...")
        elif result.get("mode") == "vision":
            print(f"[*] Total Images Generated: {len(result.get('images'))}")
            print(f"[*] Base64 String Preview: {result.get('images')[0][:50]}...")

    print(f"\n{'='*60}")