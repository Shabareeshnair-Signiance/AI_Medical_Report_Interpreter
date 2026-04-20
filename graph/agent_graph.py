from langgraph.graph import StateGraph, END

from agents.report_agent import report_agent
from agents.explanation_agent import explanation_agent
from agents.guidance_agent import guidance_agent

from processing.report_parser import parse_medical_report
from processing.llm_extractor import llm_extract_medical_data
from processing.pdf_reader import read_pdf

from ocr_service.ocr_llm_extractor import run_ocr_pipeline

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

        # Single state full report
        state = {
            "lab_results": lab_results
        }

        # ADD metadata (safe extension)
        state["source"] = "pdf"   # default
        state["confidence"] = "high"

        result = graph.invoke(state)

        logger.info("Pipeline execution completed")

        return {
            "analysis": result.get("analysis", ""),
            "explanation": result.get("explanation", ""),
            "guidance": result.get("guidance", "")
        }

    except Exception as e:
        logger.error(f"Pipeline error: {str(e)}")
        return {"error": str(e)}
    

# Vision AI Pipeline for scanned reports
def run_vision_medical_pipeline(file_path: str):
    """
    Parallel pipeline specifically for handling Scanned Reports/Images.
    Uses the robust Vision AI extraction engine instead of the legacy parser.
    """

    try:
        logger.info("Starting Vision AI Medical Pipeline (Scanned Reports)")

        # 1. Extracting data using our new, highly accurate Vision engine
        extracted_data = run_ocr_pipeline(file_path)
        lab_results = extracted_data.get("lab_results", [])

        if not lab_results:
            logger.warning("Vision AI could not extract any valid lab results.")
            return {"error": "Extraction failed or returned empty results."}
        
        # 2. Building the Langgraph workflow
        graph = build_medical_graph()

        if graph is None:
            return {"error": "Graph not built"}
        
        # 3. Initialize graph state
        state = {
            "lab_results": lab_results
        }

        # Add metadata expected by your downstream agents
        state["source"] = "scanned_image_vision_ai"
        state["confidence"] = "high"

        # 4. Execute the graph
        logger.info("Invoking Langgraph with Vision AI extracted data...")
        result = graph.invoke(state)

        logger.info("Vision AI Pipeline execution completed")

        return {
            "analysis": result.get("analysis", ""),
            "explanation": result.get("explanation", ""),
            "guidance": result.get("guidance", "")
        }
    
    except Exception as e:
        logger.error(f"Vision AI Pipeline error: {str(e)}")
        return {"error": {str(e)}}


# testing the entire agent with sample report
# if __name__ == "__main__":
    
#     # Testing the NEW Vision pipeline with a scanned report
#     #file_path = "sample_data/Scanned_report.pdf"
#     file_path = "sample_data/Medical_report.pdf"
    
#     print(f"\n{'='*60}")
#     print(f"LANGGRAPH VISION AI TEST: {file_path}")
#     print(f"{'='*60}\n")

#     result = run_vision_medical_pipeline(file_path)

#     if "error" in result:
#         print(f"\n[!] Pipeline Error: {result['error']}")
#     else:
#         print("\n=== ANALYSIS (From Report Agent) ===\n")
#         print(result.get("analysis", "No analysis generated."))

#         print("\n=== EXPLANATION (From Explanation Agent) ===\n")
#         print(result.get("explanation", "No explanation generated."))

#         print("\n=== GUIDANCE (From Guidance Agent) ===\n")
#         print(result.get("guidance", "No guidance generated."))

#     print("\n" + "=" * 60)
