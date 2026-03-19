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
            return {"analysis": "LLM initialization failed"}

        # ONLY SINGLE TEST DATA
        test = state.get("test", "Unknown")
        value = state.get("value", "Unknown")
        ref = state.get("reference_range", "Unknown")
        status = state.get("status", "Unknown")

        # HARD CONSTRAINT PROMPT
        prompt = ChatPromptTemplate.from_template(
            """
You are a strict medical analysis assistant.

You will be given ONLY ONE medical test.

Rules:
- Analyze ONLY this test
- DO NOT mention any other tests
- DO NOT add new medical terms
- DO NOT assume missing values

Input:
Test: {test}
Value: {value}
Reference Range: {reference_range}
Status: {status}

Output:
Write ONE short sentence comparing value with reference range.
"""
        )

        chain = prompt | llm | StrOutputParser()

        result = chain.invoke({
            "test": test,
            "value": value,
            "reference_range": ref,
            "status": status
        })
        #print("REPORT RESULT:", result)

        logger.info("Report Agent completed")

        state["analysis"] = result
        return state

    except Exception as e:
        logger.error(f"Report Agent Error: {str(e)}")
        state["analysis"] = "Analysis failed"
        return state