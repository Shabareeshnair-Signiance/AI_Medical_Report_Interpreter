from langgraph.graph import StateGraph, END

from agents.report_agent import report_agent
from agents.explanation_agent import explanation_agent
from agents.guidance_agent import guidance_agent

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
    

# testing the entire agent with sample report
# if __name__ == "__main__":

#     from processing.pdf_reader import read_pdf
#     from processing.report_parser import parse_medical_report

#     print("\nStarting Medical Report AI Test...\n")

#     # loading langGraph
#     graph = build_medical_graph()

#     # sample report path
#     #sample_pdf = "data/uploads/Sample Report.pdf"
#     sample_pdf = "data/uploads/Glucose_report.pdf"

#     print("Reading PDF File...\n")

#     # reading pdf
#     report_text = read_pdf(sample_pdf)
#     print("Parsing report values..\n")

#     # extracting medical values
#     medical_data = parse_medical_report(report_text)
#     print("Running LangGraph Agents..\n")

#     # initialising the state
#     state = {
#         "medical_data" : medical_data
#     }

#     # running the graph
#     result = graph.invoke(state)

#     print("\n-------- Final Output -------\n")
#     print("Medical Data:\n", result["medical_data"])

#     print("\nReport Analysis:\n")
#     print(result["analysis"])

#     print("\nExplanation:\n")
#     print(result["explanation"])

#     print("\nHealth Guidance:\n")
#     print(result["guidance"])