from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from processing.pdf_reader import read_pdf
from logger_config import logger


VECTOR_DB_PATH = "data/vector_store"

def get_retriever():
    """
    Load FAISS vector store and create a retriever
    that can search relevant medical knowledge.
    """

    try:
        logger.info("Loading embedding model for retriever")

        embeddings = HuggingFaceEmbeddings(
            model_name = "sentence-transformers/all-MiniLM-l6-v2"
        )

        logger.info("Loading FAISS vector database")

        vector_store = FAISS.load_local(
            VECTOR_DB_PATH,
            embeddings,
            allow_dangerous_deserialization=True
        )

        # converting vector store into retriever
        retriever = vector_store.as_retriever(
            search_type = "similarity",
            search_kwargs = {"k": 3} # it will return top 3 similar results
        )

        logger.info("Retriever created successfully")

        return retriever
    
    except Exception as e:
        logger.error(f"Error creating retriever: {str(e)}")
        return None
    
def search_medical_knowledge(query: str):
    """
    Search FAISS vector database using query.

    Args:
        query (str): medical value or symptom

    Returns:
        list: relevant knowledge chunks
    """

    try:
        retriever = get_retriever()

        if retriever is None:
            logger.error("Retriever could not be initialized")
            return []
        
        logger.info(f"Searching vector store for: {query}")
        results = retriever.invoke(query)

        knowledge = [doc.page_content for doc in results]
        logger.info(f"{len(knowledge)} knowledge results retrieved")

        return knowledge
    
    except Exception as e:
        logger.error(f"Error retrieving medical knowledge: {str(e)}")
        return []
    

# Testing the Retriever process to analyze any bugs or errors
if __name__ == "__main__":

    # Simulating values extracted from medical report
    # sample_queries = [
    #     "Glucose 150 mg/dL",
    #     "Hemoglobin 11 g/dL",
    #     "Platelet count 100000"
    # ]

    # Testing with Sample Medical Report
    report_path = "data/uploads/Sample Report.pdf"

    print("\n=================================")
    print("Reading Medical Report...")

    report_text = read_pdf(report_path)

    if not report_text:
        print("Failed to read report")
        exit()

    print("Report Successfully read\n")

    # It can search the full report text
    print("Searching medical knowledge for report content...\n")
    results = search_medical_knowledge(report_text)

    print("\nRetrieved Knowledge:\n")

    for r in results:
        print(".", r)