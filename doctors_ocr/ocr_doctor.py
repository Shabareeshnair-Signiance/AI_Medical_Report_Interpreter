import os
import base64
import io
from PIL import Image
from pdf2image import convert_from_path
from logger_config import logger

try:
    import fitz  # PyMuPDF for fast digital text extraction
except ImportError:
    fitz = None
    logger.warning("PyMuPDF (fitz) not installed. 'Fast Lane' digital PDF extraction will fall back to Vision.")

class ClinicalVisionEngine:
    def __init__(self):
        # EasyOCR has been removed. We are now 100% Vision & PyMuPDF powered.
        pass

    def pil_to_base64(self, image):
        """Converts a PIL Image to a base64 string for the OpenAI Vision API."""
        buffer = io.BytesIO()
        # Convert to RGB to ensure JPEG compatibility (drops alpha channel if any)
        image = image.convert('RGB')
        # Quality 85 reduces API payload size while keeping text crystal clear
        image.save(buffer, format="JPEG", quality=85)
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
            
            # If the PDF is a scan, text length will be near 0. 
            # If it's digital, it will easily be > 100 characters.
            if len(text.strip()) > 100:
                return text.strip()
            return None
        except Exception as e:
            logger.error(f"PyMuPDF Extraction Error: {str(e)}")
            return None

    def extract_document(self, file_path):
        """
        Master function: Routes to Fast Lane (Text) or Smart Lane (Vision).
        Returns a dictionary indicating the extraction mode and content.
        """
        ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if ext == '.pdf':
                # 1. Try Fast Lane (Digital Text)
                digital_text = self.extract_digital_text(file_path)
                if digital_text:
                    logger.info(f"[{os.path.basename(file_path)}] Native text detected. Routing to Fast Lane.")
                    return {"mode": "text", "content": digital_text}
                
                # 2. Smart Lane (Vision Conversion)
                logger.info(f"[{os.path.basename(file_path)}] Scanned PDF detected. Converting to Vision Base64...")
                # 200 DPI is perfect for OpenAI Vision. High enough to read, low enough to save tokens.
                pages = convert_from_path(file_path, dpi=200) 
                base64_images = []
                
                for i, page in enumerate(pages):
                    b64 = self.pil_to_base64(page)
                    base64_images.append(b64)
                    logger.info(f"Page {i+1} converted for Vision AI.")
                
                return {"mode": "vision", "images": base64_images}
            
            elif ext in ['.jpg', '.jpeg', '.png']:
                # Direct Image to Smart Lane
                logger.info(f"[{os.path.basename(file_path)}] Image file detected. Routing to Vision Base64.")
                image = Image.open(file_path)
                b64 = self.pil_to_base64(image)
                return {"mode": "vision", "images": [b64]}
                
            else:
                logger.error(f"Unsupported file format: {ext}")
                return {"mode": "error", "message": f"Unsupported format: {ext}"}
                
        except Exception as e:
            logger.error(f"Document processing failed: {str(e)}")
            return {"mode": "error", "message": str(e)}

# Initialize Engine globally
ocr_engine = ClinicalVisionEngine()


# if __name__ == "__main__":
#     # Test Block
#     TEST_FILE = "sample_data/Scanned_report.pdf" 
    
#     print(f"\n{'='*60}")
#     print(f"VISION ENGINE ROUTER: TERMINAL TEST")
#     print(f"{'='*60}\n")
    
#     if not os.path.exists(TEST_FILE):
#         print(f"Error: File not found at {TEST_FILE}")
#     else:
#         result = ocr_engine.extract_document(TEST_FILE)
        
#         print(f"\n[✓] Processing Complete!")
#         print(f"[*] Chosen Mode: {result.get('mode').upper()}")
        
#         if result.get("mode") == "text":
#             print(f"[*] Text Length: {len(result.get('content'))} characters.")
#             print(f"[*] Preview: {result.get('content')[:200]}...")
#         elif result.get("mode") == "vision":
#             print(f"[*] Total Images Generated: {len(result.get('images'))}")
#             print(f"[*] Base64 String Preview: {result.get('images')[0][:50]}...")
            
#     print(f"\n{'='*60}")