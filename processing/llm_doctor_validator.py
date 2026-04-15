import re
import json
import os
from openai import OpenAI
from doctors_ocr.ocr_doctor import ocr_engine
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from llm.llm_provider import get_llm
from logger_config import logger

def llm_extract_doctor_identity(text:str) -> dict:
    """Specilized identity extraction for the Doctor Dashboard."""
    try:
        logger.info("Starting Doctor-Specific LLM Extraction")
        llm = get_llm()
        if not llm: return {"name": None, "identifier": None, "date": None}

        prompt = ChatPromptTemplate.from_template(
            """
You are a Medical data specialist. Extract the patient's identity and the report date.

Format your response EXACTLY like this:
Name: <patient name>
Identifier: <ID/Reg No/PID>
Date: <Report Date in YYYY-MM-DD or DD-MM-YYYY>

Rules:
- If a value is missing, write None.
- Do not include extra text.
- Prioritie Patient ID or Reg No for the Identifier.

Input:
{text}
"""
        )

        chain = prompt | llm | StrOutputParser()
        result = chain.invoke({"text": text}).strip()

        # Simple parsing logic
        name = re.search(r"Name:\s*(.*)", result, re.IGNORECASE)
        id_val = re.search(r"Identifier:\s*(.*)", result, re.IGNORECASE)
        date_val = re.search(r"Date:\s*(.*)", result, re.IGNORECASE)
        
        return {
            "name": name.group(1).strip() if name and "none" not in name.group(1).lower() else None,
            "identifier": id_val.group(1).strip() if id_val and "none" not in id_val.group(1).lower() else None,
            "date": date_val.group(1).strip() if date_val and "none" not in date_val.group(1).lower() else None
        }
    except Exception as e:
        logger.error(f"Doctor LLM Extractor failed: {e}")
        return {"name": None, "identifier": None, "date": None}
    

# NEW: Vision AI Validation Integration 
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def vision_extract_doctor_identity(file_path: str) -> dict:
    """
    Multi-modal Gatekeeper for the Doctor Dashboard. 
    Uses the Fast Lane (text) if available, otherwise uses the Smart Lane (Vision).
    """
    try:
        logger.info(f"Vision Gatekeeper: Checking file {file_path}")
        
        # 1. Route the document using our new engine
        doc_data = ocr_engine.extract_document(file_path)
        
        # 2. FAST LANE: Native Text Detected
        if doc_data.get("mode") == "text":
            logger.info("Vision Gatekeeper: Native text found, routing to original extractor.")
            # Safely calls your existing, untouched function above!
            return llm_extract_doctor_identity(doc_data.get("content"))
            
        # 3. SMART LANE: Scanned Image/PDF Detected
        elif doc_data.get("mode") == "vision":
            logger.info("Vision Gatekeeper: Scanned document detected, using Vision Lane.")
            base64_images = doc_data.get("images", [])
            
            if not base64_images:
                return {"name": None, "identifier": None, "date": None}
                
            # We only need the FIRST page to find the patient's name and date
            first_page_b64 = base64_images[0]
            
            # Focused prompt just for validation (saves tokens/time)
            messages = [
                {"role": "system", "content": """You are a Medical Data Validator. Look at the medical report image.
Extract the patient's identity and the report date. 
CRITICAL DATE RULE: You must format the date STRICTLY as YYYY-MM-DD. Strip out all time signatures (hours, minutes, AM/PM). If the date is 10/7/2025 8:35 AM, output 2025-10-07.
Return ONLY a valid JSON object. No markdown.
Format:
{
  "name": "patient name or null",
  "identifier": "ID, Reg No, or PID or null",
  "date": "YYYY-MM-DD or null"
}"""},
                {"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{first_page_b64}"}}
                ]}
            ]
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0,
                max_tokens=200
            )
            
            output = response.choices[0].message.content.strip()
            output = re.sub(r"```json|```", "", output).strip()
            data = json.loads(output)
            
            return {
                "name": data.get("name"),
                "identifier": data.get("identifier"),
                "date": data.get("date")
            }
            
        return {"name": None, "identifier": None, "date": None}

    except Exception as e:
        logger.error(f"Vision Gatekeeper failed: {e}")
        return {"name": None, "identifier": None, "date": None}