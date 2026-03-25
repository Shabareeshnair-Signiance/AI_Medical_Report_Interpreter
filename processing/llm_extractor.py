import json
from logger_config import logger
from utils.test_line_extractor import extract_test_lines
from utils.range_extractor import extract_reference_ranges
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def llm_extract_medical_data(report_text: str):

    try:
        logger.info("Starting LLM Extraction")

        filtered_text = extract_test_lines(report_text)

        ranges = extract_reference_ranges(report_text)
        range_text = "\n".join(ranges)
#Extract ALL lab test results from the report below.
        prompt = f"""
You are a medical data extraction assistant.

Extract ONLY clearly visible lab test results from OCR text.

Return ONLY valid JSON.
Do NOT add explanations, comments, or markdown.
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

IMPORTANT RULES:

1. VALID TEST IDENTIFICATION
- A valid test must contain:
  • Test name
  • Numeric value
- Ignore incomplete or unclear entries
- Ignore comments, paragraphs, patient details

2. OCR HANDLING (STRICT)
- Text may be broken across lines
- Combine related parts logically:
  Example:
    "0.87" + "mg/dl" + "Creatinine"
    -> Creatinine | 0.87 | mg/dl

- Fix only obvious OCR mistakes
- If not confident → skip

3. VALUE EXTRACTION
- Extract only the numeric value (e.g., 0.87, 178)
- Do NOT include unit inside value

4. UNIT EXTRACTION
- Extract unit separately (mg/dl, g/dl, %, etc.)
- If missing -> ""

5. REFERENCE RANGE (VERY IMPORTANT)
- Extract ONLY if clearly present NEAR the test
- It may appear as:
    • "Reference Range"
    • "Biological Reference Range"
    • "Normal Range"
    • Inline values like "0.6 - 1.2" or "<100"

- DO NOT take random numbers from other parts
- If not clearly linked to the test -> "N/A"

6. STATUS CALCULATION (STRICT)
- If reference range is present:
    -> Compare numeric value:

    Cases:
    - "X - Y" -> Normal if X ≤ value ≤ Y
    - "<X" -> High if value > X
    - ">X" -> Low if value < X

- If report explicitly shows High/Low/Normal for that test:
    -> Use it ONLY if clearly aligned with that test

- If no valid range -> "Unknown"

7. STRICT ANTI-HALLUCINATION
- DO NOT guess reference ranges
- DO NOT reuse range from another test
- DO NOT invent missing values
- If anything is unclear -> skip or mark "N/A"

8. Rule:
- Use reference ranges ONLY from "Possible Reference Ranges" section if not directly linked
- Match the most relevant range to each test based on context

9. OUTPUT
- Each test must be a separate JSON object
- Keep output clean and structured

Report:
{filtered_text}

Possible Reference Ranges (from report):
{range_text}
"""
        #Do not skip tests
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
#from processing.ocr_engine import extract_text
from processing.text_loader import get_text

if __name__ == "__main__":
    #file_path = "sample_data/sample_blood_report.pdf"
    #file_path = "sample_data/sample_medical_report_text.pdf"
    #file_path = "sample_data/Sample Report.pdf"
    file_path = "sample_data/Medical_report.pdf"

    print("\n--- OCR TEXT ---\n")

    text = get_text(file_path)
    #text = extract_text(file_path)
    print(text[:1000])

    result = llm_extract_medical_data(text)

    print("\n--- LLM Output ---\n")
    for item in result["lab_results"]:
        print(item)