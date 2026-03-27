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

        conditions = state.get("conditions", [])
        conditions_text = ", ".join(conditions) if conditions else "general health"

        if not conditions:
            conditions_text = "No specific condition detected, focus on overall health"

        if llm is None:
            logger.error("LLM initialization failed")
            state["guidance"] = "LLM initialization failed"
            return state

        # UPDATED PROMPT (NO TEST DATA)
        prompt = ChatPromptTemplate.from_template(
            """
You are a medical wellness assistant.

Provide simple general health guidance.

Rules:
- Give ONLY 2 points
- Keep it very short and simple
- Focus only on:
  1. Healthy diet
  2. Regular exercise
- DO NOT mention any medical tests
- DO NOT mention values
- DO NOT add extra points

The patient has the following conditions:
{conditions}
Tailor the advice based on these conditions if present.

Also add one final line:
"Consult a doctor if needed."

Output Format:
- <point 1>
- <point 2>

Consult a doctor if needed.
"""
        )

        chain = prompt | llm | StrOutputParser()

        # NO INPUT NEEDED
        result = chain.invoke({"conditions": conditions_text})

        logger.info("Health Guidance Agent completed")

        state["guidance"] = result
        return state

    except Exception as e:
        logger.error(f"Guidance Agent failed: {str(e)}")
        state["guidance"] = "Health guidance generation failed"
        return state
    

# testing the guidance agent
if __name__ == "__main__":
    from processing.pdf_reader import read_pdf
    from processing.report_parser import parse_medical_report
    from processing.llm_extractor import llm_extract_medical_data
    from agents.report_agent import report_agent
    from agents.explanation_agent import explanation_agent

    print("\n=== Running Full Pipeline Test with PDF ===\n")

    file_path = "sample_data/Glucose_report.pdf"

    try:
        # Step 1: Read PDF (digital)
        text = read_pdf(file_path)

        # Step 2: Parse report (rule-based)
        parsed_data = parse_medical_report(text)

        # Step 3: Fallback to LLM extractor if parser fails
        if (
            not parsed_data
            or not isinstance(parsed_data, dict)
            or "tests" not in parsed_data
            or len(parsed_data.get("tests", [])) == 0
        ):
            print("⚠️ Parser failed, switching to LLM extractor...")
            parsed_data = llm_extract_medical_data(text)

        print("\n=== PARSED DATA ===\n", parsed_data)

        # Step 4: Prepare state
        state = {
            "report_data": parsed_data
        }

        # Step 5: Run Report Agent
        state = report_agent(state)

        # Step 6: Run Explanation Agent
        state = explanation_agent(state)

        # Step 7: General condition detection (for all tests)
        conditions = []

        for test in parsed_data.get("tests", []):
            name = test.get("test", "").lower()
            status = test.get("status", "").lower()

            if "high" in status or "low" in status:

                if "glucose" in name or "sugar" in name:
                    conditions.append("Blood Sugar Issue")

                elif "bp" in name or "blood pressure" in name:
                    conditions.append("Blood Pressure Issue")

                elif "thyroid" in name or "tsh" in name:
                    conditions.append("Thyroid Imbalance")

                elif "cholesterol" in name:
                    conditions.append("Cholesterol Issue")

                elif "hemoglobin" in name:
                    conditions.append("Hemoglobin Issue")

                elif "vitamin" in name:
                    conditions.append("Vitamin Deficiency")

                elif "calcium" in name:
                    conditions.append("Calcium Imbalance")

                else:
                    conditions.append(f"Issue in {test.get('test', 'unknown test')}")

        # Remove duplicates
        conditions = list(set(conditions))

        state["conditions"] = conditions

        # Step 8: Run Guidance Agent
        state = guidance_agent(state)

        print("\n=== FINAL OUTPUT ===\n")
        print("Report Summary:\n", state.get("report", ""))
        print("\nExplanation:\n", state.get("explanation", ""))
        print("\nGuidance:\n", state.get("guidance", ""))

    except Exception as e:
        print(f"Test failed: {str(e)}")