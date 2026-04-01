from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from llm.llm_provider import get_llm
from logger_config import logger
import json
import re
import os
from datetime import datetime


# -------- Clean LLM Output --------
def clean_llm_output(response):
    response = re.sub(r"```json|```", "", response).strip()

    match = re.search(r"\{.*\}", response, re.DOTALL)
    if match:
        return match.group(0)

    return response


# -------- Load Prompt --------
def load_prompt():
    with open("prompts/doctor_extractor.txt", "r", encoding="utf-8") as f:
        return f.read()


# -------- File Date Fallback --------
def get_file_date(file_path):
    try:
        timestamp = os.path.getctime(file_path)
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
    except Exception as e:
        logger.warning(f"File date extraction failed: {str(e)}")
        return None


# -------- LLM Extractor --------
def llm_doctor_extractor(report_text, file_path=None):

    try:
        logger.info("LLM Doctor Extractor Started")

        prompt_text = load_prompt()

        prompt = PromptTemplate(
            input_variables=["report_text"],
            template=prompt_text
        )

        llm = get_llm()

        # LCEL chain
        chain = prompt | llm | StrOutputParser()

        response = chain.invoke({
            "report_text": report_text
        })

        cleaned = clean_llm_output(response)

        try:
            data = json.loads(cleaned)
        except Exception as e:
            logger.error(f"JSON Parsing Failed: {str(e)}")
            logger.error(f"LLM Raw Output: {response}")
            return {
                "patient_name": "Unknown",
                "report_date": "Not Available",
                "lab_results": []
            }

        # -------- Date Fallback Logic --------
        if (
            not data.get("report_date") or
            len(str(data.get("report_date"))) < 8
        ):
            if file_path:
                fallback_date = get_file_date(file_path)
                if fallback_date:
                    data["report_date"] = fallback_date
                    data["date_source"] = "file_metadata"
                else:
                    data["report_date"] = "Not Available"
                    data["date_source"] = "unknown"
        else:
            data["date_source"] = "report"

        logger.info("LLM Extraction Successful")

        return data

    except Exception as e:
        logger.error(f"LLM Extractor Error: {str(e)}")
        return {
            "patient_name": "Unknown",
            "report_date": "Not Available",
            "lab_results": []
        }


# -------- Testing --------
if __name__ == "__main__":

    from processing.pdf_reader import read_pdf

    #file_path = "sample_data/Glucose_report.pdf"
    #file_path = "sample_data/platelet_report.pdf"
    file_path = "sample_data/Sample Report.pdf"

    print("\n==== Running LLM Extractor Test ====\n")

    text = read_pdf(file_path)

    result = llm_doctor_extractor(text, file_path)

    print("\n==== Output ====\n")
    print(result)