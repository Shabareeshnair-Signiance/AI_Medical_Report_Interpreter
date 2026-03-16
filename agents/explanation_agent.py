from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from llm.llm_provider import get_llm
from rag.retriever import search_medical_knowledge
from logger_config import logger

# only used for testing this agent
from processing.pdf_reader import read_pdf
from processing.report_parser import parse_medical_report
from agents.report_agent import report_agent


def explanation_agent(state: dict):
    """
    LangGraph node for generating patient friendly explanation
    using report analysis and medical knowledge (RAG)
    """

    try:
        logger.info("Starting Explanation Agent")

        # Getting values from graph state
        medical_data = state.get("medical_data", {})
        analysis = state.get("analysis", "")

        # Converting dictionary into readable format
        formatted_data = "\n".join(
            [f"{key}: {value}" for key, value in medical_data.items()]
        )

        # Retrieving relevant medical knowledge from FAISS
        knowledge_context = []

        for key, value in medical_data.items():
            query = f"{key} {value}"
            results = search_medical_knowledge(query, key)
            knowledge_context.extend(results)

        # Combining retrieved knowledge
        knowledge_text = "\n".join(knowledge_context)

        logger.info("Medical knowledge retrieved from FAISS")

        # Initializing LLM
        llm = get_llm()

        if llm is None:
            logger.error("LLM initialization failed, try again...")
            state["explanation"] = "LLM initialization failed"
            return state
        
        # Prompt for patient friendly explanation
        prompt = ChatPromptTemplate.from_template(
            """
You are a helpful Medical AI Assistant.

Explain the following medical report results in simple language
so a normal patient can understand them.

Medical Report Values:
{medical_data}

Analysis:
{analysis}

Medical Knowledge:
{knowledge}

Rules:
- Use simple and clear language
- Explain what each medical value measures
- Clearly mention whether the value is normal, high, or low
- Explain why the test is important for health
- Do not give medical diagnosis or treatment
- Encourage the patient to discuss abnormal results with a doctor
- Keep the explanation short and easy to understand
"""
        )

        # Creating modern LangChain Pipeline
        chain = prompt | llm | StrOutputParser()

        logger.info("Sending explanation request to LLM")

        result = chain.invoke({
            "medical_data" : formatted_data,
            "analysis" : analysis,
            "knowledge" : knowledge_text
        })

        # Storing results in graph state
        state["explanation"] = result

        logger.info("Explanation Agent completed")

        return state
    
    except Exception as e:
        logger.error(f"Explanation Agent failed: {str(e)}")
        state["explanation"] = "Explanation generation failed"
        return state
    

# Testing the explanation agent whether it's working or not
if __name__ == "__main__":

    print("\nReading Medical Report...\n")
    #report_path = "data/uploads/Sample Report.pdf"
    report_path = "data/uploads/Glucose_report.pdf"

    # reading the pdf file
    report_text = read_pdf(report_path)

    if not report_text:
        print("Failed to read report")
        exit()

    print("Parsing Medical Report...\n")

    # Extracting the lab values from the report
    parsed_data = parse_medical_report(report_text)

    if not parsed_data:
        print("No medical values found.")
        exit()

    lab_results = parsed_data.get("lab_results", [])

    medical_data = {}

    # Preparing medical data dictionary
    for item in lab_results:
        test_name = item["test"]
        value = item["value"]
        unit = item["unit"]
        ref_range = item.get("reference_range", "unknown")

        medical_data[test_name] = f"{value} {unit} (normal range {ref_range})"

    # creating initial state for agents
    state = {
        "medical_data" : medical_data
    }
    print("\nRunning Report Agent..\n")

    # running the agent 1 to generate analysis
    state = report_agent(state)

    print("\nAnalysis Result:\n")
    print(state.get("analysis"))

    print("\nRunning Explanation Agent..\n")

    # running the explanation agent
    state = explanation_agent(state)
    print("\n---- Medical Explanation ----\n")
    print(state.get("explanation"))