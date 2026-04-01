from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from llm.llm_provider import get_llm
from logger_config import logger
import json

# loading prompts
def load_prompt():
    with open("prompts/doctor_extractor.txt", "r", encoding = "utf-8") as f:
        return f.read()
    

# LLM Extractor
def llm_doctor_extractor(report_text):

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

        # Clean markdown if present
        if response.startswith("```"):
            response = response.split("```")[1]

        data = json.loads(response.strip())

        logger.info("LLM Extraction Successful")

        return data

    except Exception as e:
        logger.error(f"LLM Extractor Error: {str(e)}")
        return {
            "patient_name": "Unknown",
            "report_date": None,
            "lab_results": []
        }
    
# Testing 
if __name__ == "__main__":

    from processing.pdf_reader import read_pdf

    file_path = "sample_data/Glucose_report.pdf"

    print("\n==== Running LLM Extractor Test ====\n")

    text = read_pdf(file_path)

    result = llm_doctor_extractor(text)

    print("\n==== Output ====\n")
    print(result)