from langgraph.graph import StateGraph, END

from agents.report_agent import report_agent
from agents.explanation_agent import explanation_agent
from agents.guidance_agent import guidance_agent

from processing.report_parser import parse_medical_report
from processing.llm_extractor import llm_extract_medical_data
from processing.pdf_reader import read_pdf

from logger_config import logger


def build_medical_graph():
    """
    Build the LangGraph workflow connecting all agents.
    """

    try:
        logger.info("Building LangGraph Workflow")

        # creating graph with dictionary state
        workflow = StateGraph(dict)

        # Adding agent nodes
        workflow.add_node("report_agent", report_agent)
        workflow.add_node("explanation_agent", explanation_agent)
        workflow.add_node("guidance_agent", guidance_agent)

        # defining execution order
        workflow.set_entry_point("report_agent")

        workflow.add_edge("report_agent", "explanation_agent")
        workflow.add_edge("explanation_agent", "guidance_agent")

        workflow.add_edge("guidance_agent", END)

        # compiling the graph
        graph = workflow.compile()

        logger.info("LangGraph workflow created successfully")

        return graph
    
    except Exception as e:
        logger.error(f"Error building LangGraph: {str(e)}")
        return None
    
# Hybrid Pipeline function
def run_medical_pipeline(file_path: str):
    """
    Complete pipeline:
    PDF -> Parser -> (if fail) -> LLM -> LangGraph Agents
    """
    
    try:
        logger.info("Starting full medical pipeline")

        # Reading pdf
        text = read_pdf(file_path)

        # Trying parser
        parsed_data = parse_medical_report(text)

        # Hybrid fallback
        lab_results = parsed_data.get("lab_results", [])

        # Check for bad parsing (missing names or weird names)
        bad_data = any(
            len(item.get("test", "").split()) < 2 or any(char.isdigit() for char in item.get("test", ""))
            for item in lab_results
        )

        if len(lab_results) == 0 or bad_data:
            logger.warning("Parser unreliable, switching to LLM extractor")
            parsed_data = llm_extract_medical_data(text)

        # running the LangGraph
        graph = build_medical_graph()

        if graph is None:
            return {"error": "Graph not built"}
        
        result = graph.invoke(parsed_data)
        logger.info("Pipeline execution completed")
        return result
    
    except Exception as e:
        logger.error(f"Pipeline error: {str(e)}")
        return {"error": str(e)}

# testing the entire agent with sample report
if __name__ == "__main__":

    file_path = "sample_data/sample_blood_report.pdf"
    result = run_medical_pipeline(file_path)
    print("\n--- Final Output ---\n")
    print(result)