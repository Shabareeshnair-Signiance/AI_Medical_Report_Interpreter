from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from llm.llm_provider import get_llm
from logger_config import logger


def guidance_agent(state: dict):
    """
    LangGraph node for generating guidance for ONE test only.
    """

    try:
        logger.info("Starting Health Guidance Agent")

        # SINGLE TEST CONTEXT
        # test = state.get("test", "Unknown")
        # status = state.get("status", "Unknown")
        # explanation = state.get("explanation", "")

        llm = get_llm()

        if llm is None:
            logger.error("LLM initialization failed")
            return {"guidance": "LLM initialization failed"}

        # STRICT PROMPT
        prompt = ChatPromptTemplate.from_template(
            """
You are a medical wellness assistant.

Provide general healthy lifestyle guidance based on a medical test.

Rules:
- Focus ONLY on general health improvement
- DO NOT give test-specific medical advice
- DO NOT mention other tests
- DO NOT diagnose or suggest diseases
- DO NOT prescribe medicines

Input:
Test: {test}
Status: {status}

Output:
Provide 4–5 simple lifestyle suggestions.

Include:
- Healthy diet
- Physical activity
- Daily habits

Format:
- Each point on a new line
- Keep it short and practical

Safety:
- Encourage consulting a doctor if values are abnormal
"""
        )

        lab_results = state.get("lab_results", [])

        if not lab_results:
            logger.error("No lab results for guidance")
            state["guidance"] = ""
            return state

        chain = prompt | llm | StrOutputParser()

        guidance_list = []

        for item in lab_results:
            test = item.get("test", "Unknown")
            status = item.get("status", "Unknown")

            result = chain.invoke({
                "test": test,
                "status": status
            })

            guidance_list.append(f"{test}:\n{result}")

        logger.info("Health Guidance Agent completed")

        state["guidance"] = "\n\n".join(guidance_list)
        return state

    except Exception as e:
        logger.error(f"Guidance Agent failed: {str(e)}")
        return {"guidance": "Health guidance generation failed"}