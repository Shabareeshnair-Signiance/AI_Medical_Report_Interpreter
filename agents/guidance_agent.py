from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from llm.llm_provider import get_llm
from logger_config import logger


def guidance_agent(state: dict):
    """
    LangGraph node for generating simple general guidance.
    - Always returns 2 points + doctor advice
    """

    try:
        logger.info("Starting Health Guidance Agent")

        llm = get_llm()

        lab_results = state.get("lab_results", [])

        if not lab_results:
            state["guidance"] = "No lab results available for guidance."
            return state

        if llm is None:
            logger.error("LLM initialization failed")
            state["guidance"] = "LLM initialization failed"
            return state
        
        # converting to string for prompt
        lab_results_text = str(lab_results)

        # UPDATED PROMPT (NO TEST DATA)
        prompt = ChatPromptTemplate.from_template(
            """
You are a medical wellness assistant.

Your task is to provide personalized health guidance based on the patient's medical report.

Patient Test Details:
{lab_results}

STRICT RULES:
- Generate guidance for EACH test separately
- DO NOT combine multiple tests into one answer
- DO NOT skip any test
- DO NOT give generic advice
- DO NOT mention medical values or numbers
- DO NOT suggest any medicines or treatments
- ONLY give lifestyle guidance (diet + exercise)

FOR EACH TEST:
- Clearly identify the condition (High / Low / Abnormal)

DIET RULES (STRICT)
- MUST split into:
    What to Eat
    What to Avoid
- Be specific (e.g., vegetables, fruits, grains, avoid sugar, fried food, etc.)

EXERCISE RULES:
- Suggest safe and relevant activity (walking, yoga, light exercise)
- Keep it practical

OUTPUT FORMAT (STRICT):

Test: <test name> (<status>)

Diet:
What to Eat:
- <food items>

What to Avoid:
- <food items>

Exercise:
- <activity>

Diet:
What to Eat:
- ...

What to Avoid:
- ...

Exercise:
- ...

FINAL LINE:
Consult a doctor if needed.
"""
        )

        chain = prompt | llm | StrOutputParser()

        # NO INPUT NEEDED
        result = chain.invoke({"lab_results": lab_results_text})

        logger.info("Health Guidance Agent completed")

        state["guidance"] = result
        return state

    except Exception as e:
        logger.error(f"Guidance Agent failed: {str(e)}")
        state["guidance"] = "Health guidance generation failed"
        return state
    

# testing the guidance agent
# if __name__ == "__main__":
#     from processing.pdf_reader import read_pdf
#     from processing.report_parser import parse_medical_report
#     from processing.llm_extractor import llm_extract_medical_data
#     from agents.report_agent import report_agent
#     from agents.explanation_agent import explanation_agent

#     print("\n=== Running Full Pipeline Test with PDF ===\n")

#     #file_path = "sample_data/Glucose_report.pdf"
#     file_path = "sample_data/Sample Report.pdf"

#     try:
#         # Step 1: Read PDF (digital)
#         text = read_pdf(file_path)

#         # Step 2: Parse report (rule-based)
#         parsed_data = parse_medical_report(text)

#         # Step 3: Fallback to LLM extractor if parser fails
#         if (
#             not parsed_data
#             or not isinstance(parsed_data, dict)
#             or "tests" not in parsed_data
#             or len(parsed_data.get("tests", [])) == 0
#         ):
#             print("⚠️ Parser failed, switching to LLM extractor...")
#             parsed_data = llm_extract_medical_data(text)

#         print("\n=== PARSED DATA ===\n", parsed_data)

#         # ADD THIS BLOCK
#         if "tests" not in parsed_data and "lab_results" in parsed_data:
#             parsed_data["tests"] = parsed_data["lab_results"]

#         # Step 4: Prepare state
#         state: dict = {
#             "report_data": parsed_data
#         }

#         lab_results = parsed_data.get("tests", [])
#         state["lab_results"] = lab_results
#         state["report_data"]["lab_results"] = lab_results

#         # Step 5: Run Report Agent
#         state = report_agent(state)

#         # Step 6: Run Explanation Agent
#         state = explanation_agent(state)

#         # Step 7: Guidance Agent (now uses lab_results)
#         state = guidance_agent(state)

#         print("\nSTATE KEYS:", state.keys())

#         print("\n=== FINAL OUTPUT ===\n")
#         print("Report Summary:\n", state.get("analysis", ""))
#         print("\nExplanation:\n", state.get("explanation", ""))
#         print("\nGuidance:\n", state.get("guidance", ""))

#     except Exception as e:
#         print(f"Test failed: {str(e)}")