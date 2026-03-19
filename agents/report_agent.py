from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from llm.llm_provider import get_llm
from logger_config import logger


def report_agent(state: dict):
    """
    LangGraph node for generating analysis for ONE test only.
    """

    try:
        logger.info("Running Report Agent")

        llm = get_llm()

        if llm is None:
            logger.error("LLM initialization failed")
            state["analysis"] = ""
            return state

        # ONLY SINGLE TEST DATA
        test = state.get("test")
        value = state.get("value")
        ref = state.get("reference_range")
        status = state.get("status")

        if not test or not value:
            logger.error("Missing test data")
            state["analysis"] = ""
            return state

        # HARD CONSTRAINT PROMPT
        prompt = ChatPromptTemplate.from_template(
            """
You are a strict medical analysis assistant.

You will be given ONLY ONE medical test.

Your job is to ALWAYS generate ONE clear Sentence.

Rules:
- You MUST generate output (do not return empty)
- Use the given value and reference range
- Clearly state if it is Low, Normal, or High
- DO NOT mention any other tests
- DO NOT add new medical terms
- DO NOT assume missing values

Input:
Test: {test}
Value: {value}
Reference Range: {reference_range}
Status: {status}

Output Example:
"Your hemoglobin is 11.2 g/dL, which is below the normal range of 13.0 - 17.0 g/dL."

Now generate the output:
"""
        )

        chain = prompt | llm | StrOutputParser()

        result = chain.invoke({
            "test": test,
            "value": value,
            "reference_range": ref or "Unknown",
            "status": status or "Unknown"
        })
        
        if not result or result.strip() == "":
            result = f"{test} value {value} is {status} compared to reference range {ref}."

        logger.info("Report Agent completed")

        state["analysis"] = result if result else ""
        return state

    except Exception as e:
        logger.error(f"Report Agent Error: {str(e)}")
        state["analysis"] = "Analysis failed"
        return state