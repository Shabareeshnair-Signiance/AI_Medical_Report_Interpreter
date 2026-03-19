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
    PDF -> Parser -> (if fail) -> LLM -> Per-test LangGraph execution
    """

    try:
        logger.info("Starting full medical pipeline")

        # Read PDF
        text = read_pdf(file_path)

        # Try parser
        parsed_data = parse_medical_report(text)
        lab_results = parsed_data.get("lab_results", [])

        # Validate parser output
        bad_data = any(
            len(item.get("test", "").split()) < 2 or any(char.isdigit() for char in item.get("test", ""))
            for item in lab_results
        )

        if len(lab_results) == 0 or bad_data:
            logger.warning("Parser unreliable, switching to LLM extractor")
            parsed_data = llm_extract_medical_data(text)
            lab_results = parsed_data.get("lab_results", [])

        # Build graph
        graph = build_medical_graph()

        if graph is None:
            return {"error": "Graph not built"}

        # LOOP PER TEST
        final_output = []

        for test in lab_results:

            # ORIGINAL SAFE STATE (DO NOT OVERWRITE)
            state = {
                "test": test.get("test", "Unknown"),
                "value": test.get("value", "Unknown"),
                "reference_range": test.get("reference_range", "Unknown"),
                "status": test.get("status", "Unknown")
            }

            result = graph.invoke(state)
            print("\nDEBUG RESULT:", result)

            # SAFETY CHECK
            if not isinstance(result, dict):
                result = {}

            # NEVER TRUST GRAPH FOR TEST NAME
            final_output.append({
                "test": state.get("test", "Unknown"), 
                "analysis": result.get("analysis", ""),
                "explanation": result.get("explanation", ""),
                "guidance": result.get("guidance", "")
            })

        logger.info("Pipeline execution completed")

        return {"results": final_output}

    except Exception as e:
        logger.error(f"Pipeline error: {str(e)}")
        return {"error": str(e)}

# testing the entire agent with sample report
if __name__ == "__main__":

    file_path = "sample_data/sample_blood_report.pdf"

    result = run_medical_pipeline(file_path)

    print("\n--- Final Output ---\n")

    if "results" in result:
        for item in result["results"]:
            print(f"\n===== {item['test']} =====\n")

            print("Analysis:")
            print(item["analysis"])

            print("\nExplanation:")
            print(item["explanation"])

            print("\nGuidance:")
            print(item["guidance"])

            print("\n" + "-" * 50)

    else:
        print(result)