from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from llm.llm_provider import get_llm
from rag.retriever import search_medical_knowledge
from logger_config import logger


def explanation_agent(state: dict):
    """
    LangGraph node for generating explanation.
    - <= 2 tests → detailed explanation
    - > 2 tests → compressed summary
    """

    try:
        logger.info("Starting Explanation Agent")

        lab_results = state.get("lab_results", [])

        if not lab_results:
            logger.error("No lab results for explanation")
            state["explanation"] = ""
            return state

        num_tests = len(lab_results)

        # MULTIPLE TESTS (COMPRESSED)
        if num_tests > 2:
            logger.info("Using compressed explanation mode")

            low = []
            high = []
            normal = []

            for item in lab_results:
                test = item.get("test")
                value = item.get("value")
                status = item.get("status", "").lower()

                if not test or not value:
                    continue

                entry = f"{test}: {value}"

                if "low" in status:
                    low.append(entry)
                elif "high" in status:
                    high.append(entry)
                else:
                    normal.append(entry)

            explanation = "SUMMARY OF RESULTS:\n\n"

            if low:
                explanation += "Low Values:\n- " + "\n- ".join(low) + "\n\n"

            if high:
                explanation += "High Values:\n- " + "\n- ".join(high) + "\n\n"

            if normal:
                explanation += "Normal Values:\n- " + "\n- ".join(normal) + "\n\n"

            explanation += "Overall:\n"
            explanation += "Multiple test results observed. Some values are outside normal range. Clinical correlation is recommended."

            state["explanation"] = explanation
            return state

        # FEW TESTS (DETAILED)
        logger.info("Using detailed explanation mode")

        llm = get_llm()

        if llm is None:
            logger.error("LLM initialization failed")
            state["explanation"] = "Explanation generation failed"
            return state

        prompt = ChatPromptTemplate.from_template(
            """
You are a helpful medical assistant.

You will be given ONLY ONE test.

Rules:
- Explain ONLY this test
- DO NOT mention any other tests
- DO NOT add new medical parameters
- Keep language very simple
- Do not generate unrelated information

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

        explanations = []

        for item in lab_results:
            test = item.get("test")
            value = item.get("value")
            status = item.get("status", "Unknown")

            if not test or not value:
                continue

            query = f"{test} {value}"
            knowledge_results = search_medical_knowledge(query, test)
            knowledge_text = "\n".join(knowledge_results)

            result = chain.invoke({
                "test": test,
                "value": value,
                "status": status,
                "analysis": state.get("analysis", ""),
                "knowledge": knowledge_text
            })

            explanations.append(result)

        logger.info("Explanation Agent completed")

        state["explanation"] = "\n\n".join(explanations)
        return state

    except Exception as e:
        logger.error(f"Explanation Agent failed: {str(e)}")
        state["explanation"] = "Explanation generation failed"
        return state