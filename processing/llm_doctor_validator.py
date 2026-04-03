import re
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