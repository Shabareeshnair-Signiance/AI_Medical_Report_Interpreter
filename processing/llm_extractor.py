import json
from logger_config import logger
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def llm_extract_medical_data(report_text: str):

    try:
        logger.info("Starting LLM Extraction")
#Extract ALL lab test results from the report below.
        prompt = f"""
You are a medical data extraction assistant.

Extract ONLY the lab tests that are clearly present in the report.

Return ONLY valid JSON.
Do NOT add explanations, comments, or markdown.
Do NOT wrap in ```json.
Output MUST be directly parseable using json.loads().

Format:
[
  {{
    "test": "",
    "value": "",
    "unit": "",
    "reference_range": "",
    "status": ""
  }}
]

OCR-SPECIFIC RULES (VERY IMPORTANT):
- The OCR text may be highly noisy and distorted
- Extract tests ONLY if BOTH test name AND numeric value are clearly present
- Ignore lines that look like headers, paragraphs, or random text
- If you are not confident a line represents a real lab test → SKIP it
- Prefer precision over recall (better to return fewer correct tests than many wrong ones)
- Do NOT return generic medical tests unless they are explicitly found in the text

Rules:
- Extract every test separately
- Do not summarize
- Do not skip tests
- If status not given, infer (Low/Normal/High) based on range
- If range missing, keep "N/A"
- If unit missing, keep ""
- OCR text may contain spelling mistakes, fix them logically (e.g., "crealinine" -> "creatinine")
- Ignore headers, hospital info, doctor names, IDs
- Only EXTRACT actual lab tests

Report:
{report_text}
"""
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        content = response.choices[0].message.content.strip()

        # cleaning JSON very important
        content = content.replace("```json", "").replace("```", "").strip()

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            logger.error("Invalid JSON from LLM")
            return {"lab_results": []}
        
        #data = json.loads(content)

        # converting to your existing format
        formatted = []
        for item in data:
            formatted.append({
                "test": item.get("test", ""),
                "value": f"{item.get('value', '')} {item.get('unit', '')}".strip(),
                "reference_range": item.get("reference_range", "N/A"),
                "status": item.get("status", "Unknown")
            })

        logger.info("LLM extraction completed")

        return {"lab_results": formatted}
    
    except Exception as e:
        logger.error(f"LLM extraction error: {str(e)}")
        return {"lab_results": []}
    

# testing the extraction to see if it's working or not
from processing.ocr_engine import extract_text

if __name__ == "__main__":
    #file_path = "sample_data/sample_blood_report.pdf"
    #file_path = "sample_data/sample_medical_report_text.pdf"
    #file_path = "sample_data/Sample Report.pdf"
    file_path = "sample_data/Medical_report.pdf"

    print("\n--- OCR TEXT ---\n")

    text = extract_text(file_path)
    print(text[:1000])

    result = llm_extract_medical_data(text)

    print("\n--- LLM Output ---\n")
    for item in result["lab_results"]:
        print(item)