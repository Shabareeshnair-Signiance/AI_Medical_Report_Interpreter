from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from llm.llm_provider import get_llm
from rag.retriever import search_medical_knowledge
from logger_config import logger


def explanation_agent(state: dict):
    """
    LangGraph node for generating explanation for ONE test only.
    """

    try:
        logger.info("Starting Explanation Agent")

        # SINGLE TEST INPUT
        test = state.get("test", "Unknown")
        value = state.get("value", "Unknown")
        status = state.get("status", "Unknown")
        analysis = state.get("analysis", "")

        # RAG ONLY FOR THIS TEST
        query = f"{test} {value}"
        knowledge_results = search_medical_knowledge(query, test)

        knowledge_text = "\n".join(knowledge_results)

        logger.info("Medical knowledge retrieved")

        # Initialize LLM
        llm = get_llm()

        if llm is None:
            logger.error("LLM initialization failed")
            state["explanation"] = "Explanation generation failed"
            return state

        # STRICT PROMPT (NO MULTI-TEST)
        prompt = ChatPromptTemplate.from_template(
            """
You are a helpful medical assistant.

You will be given ONLY ONE test.

Rules:
- Explain ONLY this test
- DO NOT mention any other tests
- DO NOT add new medical parameters
- Keep language very simple

Input:
Test: {test}
Value: {value}
Status: {status}

Analysis:
{analysis}

Medical Knowledge:
{knowledge}

Output Format:

Test Name: {test}

What does this test measure?
<simple explanation>

Is this value normal, high, or low?
<clear meaning>

Why is this important for health?
<short explanation>
"""
        )

        chain = prompt | llm | StrOutputParser()

        result = chain.invoke({
            "test": test,
            "value": value,
            "status": status,
            "analysis": analysis,
            "knowledge": knowledge_text
        })
       # print("EXPLANATION RESULT:", result)

        logger.info("Explanation Agent completed")

        state["explanation"] = result
        return state

    except Exception as e:
        logger.error(f"Explanation Agent failed: {str(e)}")
        state["explanation"] = "LLM initialization failed"
        return state