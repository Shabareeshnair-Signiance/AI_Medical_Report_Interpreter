from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from llm.llm_provider import get_llm
from logger_config import logger

# used only for testing
# from processing.pdf_reader import read_pdf
# from processing.report_parser import parse_medical_report
# from rag.retriever import search_medical_knowledge


def report_agent(state: dict):
    """
    LangGraph node for generating short medical result summary.
    """

    try:

        logger.info("Running Report Agent")

        medical_data = state.get("medical_data", {})
        llm = get_llm()

        if llm is None:
            logger.error("LLM initialization failed")
            state["analysis"] = "LLM initialization failed"
            return state

        # convert medical data to readable format
        formatted_data = "\n".join(
            [f"{key}: {value}" for key, value in medical_data.items()]
        )

        # prompt to generate only short statement
        prompt = ChatPromptTemplate.from_template(
            """
You are a medical AI assistant.

Given the following medical result, generate ONLY one short statement
summarizing the value compared to the normal range.

Clearly state whether the value is:
- within the normal range
- above the normal range
- below the normal range

Example:
"Your HDL cholesterol is 37 mg/dL, which is below the normal range of 40–59 mg/dL."

Medical Result:
{medical_data}

Rules:
- Produce only ONE short statement
- Do not provide explanations
- Do not add extra text
"""
        )

        # create chain
        chain = prompt | llm | StrOutputParser()

        result = chain.invoke({
            "medical_data": formatted_data
        })

        state["analysis"] = result

        logger.info("Report Agent completed")

        return state

    except Exception as e:

        logger.error(f"Report Agent Error: {str(e)}")

        state["analysis"] = "Analysis failed"

        return state


# Testing the agent using Sample Report

# if __name__ == "__main__":

#     report_path = "sample_data/Glucose_report.pdf"
      #report_path = "sample_data/Sample Report.pdf"

#     print("\nReading Medical Report...\n")

#     # read pdf
#     report_text = read_pdf(report_path)

#     if not report_text:
#         print("Failed to read report")
#         exit()

#     print("Parsing report...\n")

#     # parse medical values
#     parsed_data = parse_medical_report(report_text)

#     if not parsed_data:
#         print("No medical values found")
#         exit()

#     lab_results = parsed_data.get("lab_results", [])

#     medical_data = {}

#     # prepare medical data with value + reference range
#     for item in lab_results:

#         test_name = item["test"]
#         value = item["value"]
#         unit = item["unit"]
#         ref_range = item.get("reference_range", "unknown")

#         medical_data[test_name] = f"{value} {unit} (normal range {ref_range})"

#     # retrieve knowledge (for later agents)
#     knowledge_context = []

#     for item in lab_results:

#         test_name = item["test"]
#         value = item["value"]
#         unit = item["unit"]

#         query = f"{test_name} {value} {unit}"

#         results = search_medical_knowledge(query, test_name)

#         knowledge_context.extend(results)

#     # create LangGraph state
#     state = {
#         "medical_data": medical_data,
#         "knowledge": knowledge_context
#     }

#     print("\nRunning Report Analysis Agent...\n")

#     output_state = report_agent(state)

#     print("\n===== Analysis Result =====\n")

#     print(output_state["analysis"])