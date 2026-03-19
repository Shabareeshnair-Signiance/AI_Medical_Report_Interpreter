import re

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from llm.llm_provider import get_llm
from logger_config import logger


def llm_extract_identity(text: str) -> dict:
    """
    Extracts patient identity details using LLM.
    Returns:
        {
            "name": str,
            "identifier": str   # can be Reg No / PID / Lab No etc.
        }
    """

    try:
        logger.info("Starting LLM Validation Extractor")

        llm = get_llm()

        if llm is None:
            logger.error("LLM initialization failed")
            return {
                "name": None,
                "identifier": None
            }

        prompt = ChatPromptTemplate.from_template(
            """
You are a strict medical document parser.

Extract patient identity details from the report.

Important:
- Patient Name is mandatory (must try to extract correctly)
- Identifier can be ANY ONE of the following:
  - Registration Number (Reg No)
  - Patient ID (PID / UID)
  - Lab Number (Lab No / Sample ID)
- Not all reports will have all fields → extract whatever is available
- If multiple IDs exist → choose the most relevant primary identifier

Rules:
- Do NOT guess
- Do NOT hallucinate
- Ignore headings like "Blood Report", "Comprehensive Report"
- Only extract actual patient-related values

Return output in this EXACT format (no extra text):

Name: <patient name or None>
Identifier: <best available ID or None>

Input:
{text}
"""
        )

        chain = prompt | llm | StrOutputParser()

        result = chain.invoke({"text": text})

        cleaned = result.strip()

        # PARSE TEXT OUTPUT
        name = None
        identifier = None

        name_match = re.search(r"Name:\s*(.*)", cleaned, re.IGNORECASE)
        id_match = re.search(r"Identifier:\s*(.*)", cleaned, re.IGNORECASE)

        if name_match:
            value = name_match.group(1).strip()
            name = value if value.lower() != "none" else None

        if id_match:
            value = id_match.group(1).strip()
            identifier = value if value.lower() != "none" else None

        logger.info("LLM Validation Extraction completed")

        return {
            "name": name,
            "identifier": identifier
        }

    except Exception as e:
        logger.error(f"LLM Validation Extractor failed: {str(e)}")
        return {
            "name": None,
            "identifier": None
        }