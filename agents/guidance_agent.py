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
        result = chain.invoke({})

        logger.info("Health Guidance Agent completed")

        state["guidance"] = result
        return state

    except Exception as e:
        logger.error(f"Guidance Agent failed: {str(e)}")
        state["guidance"] = "Health guidance generation failed"
        return state