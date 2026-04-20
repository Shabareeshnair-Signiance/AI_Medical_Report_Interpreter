import os
import re
import hashlib
import json

from logger_config import logger
from storage.database import check_existing_report, get_validation_cache
from processing.pdf_reader import read_pdf
from ocr_service.ocr_engine import extract_text
from processing.llm_validation_extractor import llm_extract_identity, vision_llm_extract_identity


class ValidationAgent:

    def __init__(self, allowed_extensions=None, max_file_size_mb=10):
        self.allowed_extensions = allowed_extensions or [".pdf"]
        self.max_file_size_mb = max_file_size_mb

    # TEXT NORMALIZATION
    def normalize_text(self, text: str) -> str:
        text = re.sub(r'\s+', ' ', text)
        text = text.replace(" - ", ": ")
        text = text.replace("–", ":")
        text = text.replace("—", ":")
        text = re.sub(r'P\s*I\s*D', 'PID', text, flags=re.IGNORECASE)
        return text.strip()
    
    # OCR TEXT EXTRACTION
    def get_text_with_fallback(self, file_path: str) -> str:
        # Step 1: Try normal PDF text
        text = read_pdf(file_path)

        # Safe String Added
        # if not isinstance(text, str):
        #     text = ""

        # OCR fallback (only if text extraction fails)
        if not text or len(text.strip()) < 50:
            logger.warning("PDF text extraction weak -> switching to OCR Engine")
            ocr_result = extract_text(file_path)

            # --- GUARDRAIL: Safely handle new dictionary output ---
            if isinstance(ocr_result, dict):
                if ocr_result.get("mode") == "vision":
                    # Flag this as a vision document so validate() knows to bypass text regex
                    return "__VISION_DOCUMENT__"
                else:
                    ocr_text = ocr_result.get("content", "")
            else:
                ocr_text = ocr_result

            # Only replace if OCR gives better content
            if ocr_text and len(ocr_text.strip()) > len(text.strip()):
                text = ocr_text

        # Step 2: If text is too small → use OCR
        # if not text or len(text.strip()) < 50:
        #     logger.warning("Text PDF failed -> switching to OCR for validation")
        #     text = extract_text(file_path)

        return text

    # CHECK IF MEDICAL REPORT
    def is_medical_report(self, text: str) -> bool:
        keywords = [
            "hemoglobin", "platelet", "blood", "urine",
            "test", "lab", "report", "glucose", "wbc",
            "rbc", "thyroid", "vitamin", "serum"
        ]

        text_lower = text.lower()
        matches = sum(1 for word in keywords if word in text_lower)

        return matches >= 2  # simple threshold

    # EXTRACT USER DETAILS (REGEX)
    def extract_user_details(self, text: str) -> dict:
        data = {
            "user_name": None,
            "reg_no": None,
            "lab_no": None,
            "pid": None,
            "patient_id": None,
            "accession_no": None,
            "visit_no": None
        }

        text = self.normalize_text(text)

        # try to get proper name
        match = re.search(
            r'\b([A-Z][a-z]+(?:\s[A-Z]\.)?\s[A-Z][a-z]+)\b',
            text
        )

        if match:
            data["user_name"] = match.group(1)

        # FILTER OUT LAB NAMES (DO NOT REMOVE EXISTING LOGIC)
        invalid_name_keywords = [
            "lab", "laboratory", "diagnostics", "centre", "center", "clinic", "hospital"
        ]

        name = data.get("user_name", "")
        if name and any(word in name.lower() for word in invalid_name_keywords):
            data["user_name"] = None

        # identifiers
        patterns = {
            "reg_no": r'(?:Reg\s*No|Registration\s*No)\s*[:\-]?\s*(\w+)',
            "lab_no": r'(?:Lab\s*No)\s*[:\-]?\s*(\w+)',
            "pid": r'(?:PID)\s*[:\-]?\s*(\d+)',
            "patient_id": r'(?:Patient\s*ID)\s*[:\-]?\s*(\w+)',
            "accession_no": r'(?:Accession\s*No?)\s*[:\-]?\s*([\w\-]+)',
            "visit_no": r'(?:Visit\s*No|Visit\s*Number)\s*[:\-]?\s*([\w\-]+)'
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data[key] = match.group(1).strip()
        
        # FIX: Avoid Reg No picking Lab No value
        if data.get("reg_no") and data.get("lab_no"):

            reg_clean = re.sub(r'\D', '', data["reg_no"])   # keep only numbers
            lab_clean = re.sub(r'\D', '', data["lab_no"])

            if reg_clean == lab_clean or "lab" in data["reg_no"].lower():
                data["reg_no"] = None

        return data

    # HASH
    def generate_file_hash(self, file_path: str) -> str:
        try:
            sha256 = hashlib.sha256()

            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256.update(chunk)

            return sha256.hexdigest()

        except Exception as e:
            logger.error(f"Hash generation failed: {str(e)}")
            return None

    # MAIN VALIDATION
    def validate(self, file_path: str, file_hash: str = None) -> dict:

        logger.info("Starting validation process")

        result = {
            "is_valid": True,
            "errors": [],
            "file_hash": None,
            "is_duplicate": False,
            "existing_result": None,
            "extracted_data": {},
            "identifier_used": None
        }

        # FILE CHECK
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.allowed_extensions:
            result["is_valid"] = False
            result["errors"].append("Invalid file type.")

        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            result["is_valid"] = False
            result["errors"].append("File is empty.")

        # stop if file itself invalid
        if not result["is_valid"]:
            return result

        # READ TEXT
        text = read_pdf(file_path)

        # Safe string enforcer
        if not isinstance(text, str):
            text = ""

        # Dictionary Safety Net
        if isinstance(text, dict):
            text = text.get("text", "") or ""

        # # NEW CODE ADDED: ISOLATED CACHE BYPASS FOR SCANNED ONLY
        # is_scanned = not text or len(text.strip()) < 50
        
        # if is_scanned:
        #     if not file_hash:
        #         file_hash = self.generate_file_hash(file_path)
            
        #     existing = check_existing_report(file_hash)
        #     if existing:
        #         val_cache = get_validation_cache(file_hash)
        #         if val_cache:
        #             result["extracted_data"] = val_cache.get("extracted_data", {})
        #             result["identifier_used"] = val_cache.get("identifier_used")
                
        #         result["is_duplicate"] = True
        #         result["file_hash"] = file_hash
        #         result["existing_result"] = existing
        #         logger.info("Scanned report early cache hit! Skipping slow OCR validation.")
        #         return result

        # NEW CODE ADDED: ISOLATED CACHE BYPASS FOR SCANNED ONLY
        is_scanned = not text or len(text.strip()) < 50
        
        if is_scanned:
            if not file_hash:
                file_hash = self.generate_file_hash(file_path)
            
            existing = check_existing_report(file_hash)
            if existing:
                # --- FAST LOCAL IDENTITY CACHE ---
                cache_file = os.path.join("data", "val_cache.json")
                val_cache = {}
                if os.path.exists(cache_file):
                    try:
                        with open(cache_file, "r") as f:
                            val_cache = json.load(f).get(file_hash, {})
                    except: pass
                
                # Check if we actually found the cached identity
                if val_cache and val_cache.get("extracted_data"):
                    result["extracted_data"] = val_cache.get("extracted_data", {})
                    result["identifier_used"] = val_cache.get("identifier_used")
                    result["is_duplicate"] = True
                    result["file_hash"] = file_hash
                    result["existing_result"] = existing
                    logger.info("Scanned report early cache hit! Identity loaded from local cache.")
                    return result
                else:
                    logger.info("Report cached, but identity missing. Falling through to extract identity once.")

        # OCR fallback for validation
        if not text or len(text.strip()) < 50:
            logger.warning("Validation: weak PDF text -> using OCR fallback")
            text = self.get_text_with_fallback(file_path)

        # -------- ADDITIVE VISION AI GUARDRAIL --------
        if text == "__VISION_DOCUMENT__":
            logger.info("Vision Document detected. Bypassing text regex for validation.")
            
            # Get the images
            extraction_data = extract_text(file_path)
            base64_images = extraction_data.get("images", [])
            
            # Use Vision AI to get identity
            
            vision_identity = vision_llm_extract_identity(base64_images)
            
            result["extracted_data"] = {
                "user_name": vision_identity.get("name"),
                "reg_no": vision_identity.get("identifier"),
                "lab_no": None, "pid": None, "patient_id": None, "accession_no": None, "visit_no": None
            }
            
            if not result["extracted_data"]["user_name"]:
                result["errors"].append("User name not found in scanned report.")
            if not result["extracted_data"]["reg_no"]:
                result["errors"].append("No valid identifier found in scanned report.")
                
            if result["errors"]:
                result["is_valid"] = False
                return result
                
            result["identifier_used"] = f"Vision_Extracted_ID: {result['extracted_data']['reg_no']}"
            
            # NEW: Saving Identity to local cache for milliseconds retrieval
            try:
                import json
                cache_file = os.path.join("data", "val_cache.json")
                full_cache = {}
                if os.path.exists(cache_file):
                    with open(cache_file, "r") as f:
                        full_cache = json.load(f)
                
                if not file_hash:
                    file_hash = self.generate_file_hash(file_path)
                    
                full_cache[file_hash] = {
                    "extracted_data": result["extracted_data"],
                    "identifier_used": result["identifier_used"]
                }
                with open(cache_file, "w") as f:
                    json.dump(full_cache, f)
            except Exception as e:
                pass

            # Duplicate Check (Preserving existing logic)
            if not file_hash:
                file_hash = self.generate_file_hash(file_path)
            result["file_hash"] = file_hash
            existing = check_existing_report(file_hash)
            
            if existing:
                result["is_duplicate"] = True
                result["existing_result"] = existing
                
            return result

        # CHECK MEDICAL REPORT
        if not self.is_medical_report(text):
            result["is_valid"] = False
            result["errors"].append("Uploaded file is not a valid medical report.")
            return result

        # REGEX EXTRACTION
        extracted = self.extract_user_details(text)

        # CHECK IF NEED LLM
        use_llm = False

        # bad name cases
        name = extracted.get("user_name", "")

        if (
            not name or
            any(word in name.lower() for word in ["report", "blood", "test", "profile", "comprehensive"])
        ):
            use_llm = True

        identifiers = [
            extracted.get("reg_no"),
            extracted.get("lab_no"),
            extracted.get("pid"),
            extracted.get("patient_id"),
            extracted.get("accession_no"),
            extracted.get("visit_no"),
        ]

        if not any(identifiers):
            use_llm = True

        # LLM FALLBACK
        if use_llm:
            logger.warning("Regex failed, switching to LLM extractor")

            llm_data = llm_extract_identity(text)

            if llm_data.get("name"):
                extracted["user_name"] = llm_data["name"]

            if llm_data.get("identifier"):
                extracted["reg_no"] = llm_data["identifier"]

        result["extracted_data"] = extracted

        # FINAL VALIDATION
        if not extracted.get("user_name"):
            result["errors"].append("User name not found.")

        if not any(identifiers):
            result["errors"].append("No valid identifier found.")

        # choose identifier
        for key in ["reg_no", "lab_no", "pid", "patient_id", "accession_no", "visit_no"]:
            if extracted.get(key):
                result["identifier_used"] = f"{key}: {extracted.get(key)}"
                break

        if result["errors"]:
            result["is_valid"] = False
            return result

        # DUPLICATE CHECK
        if not file_hash:
            file_hash = self.generate_file_hash(file_path)

        result["file_hash"] = file_hash

        existing = check_existing_report(file_hash)

        if existing:
            result["is_duplicate"] = True
            result["existing_result"] = existing

        logger.info(f"Validation result: {result}")

        return result