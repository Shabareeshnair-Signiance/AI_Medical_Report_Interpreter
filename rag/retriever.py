from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

from processing.pdf_reader import read_pdf
from processing.report_parser import parse_medical_report

from logger_config import logger


# path where FAISS vector store is saved
VECTOR_DB_PATH = "data/vector_store"


def get_retriever():
    """
    Load FAISS vector database and convert it to retriever.
    """

    try:

        logger.info("Loading embedding model")

        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-l6-v2"
        )

        logger.info("Loading FAISS vector database")

        vector_store = FAISS.load_local(
            VECTOR_DB_PATH,
            embeddings,
            allow_dangerous_deserialization=True
        )

        # create retriever
        retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 3}
        )

        logger.info("Retriever created successfully")

        return retriever

    except Exception as e:

        logger.error(f"Error creating retriever: {str(e)}")
        return None


def search_medical_knowledge(query: str):
    """
    Search vector store using a query.
    """

    try:

        retriever = get_retriever()

        if retriever is None:
            return []

        logger.info(f"Searching vector store for: {query}")

        results = retriever.invoke(query)

        knowledge = [doc.page_content for doc in results]

        logger.info(f"{len(knowledge)} knowledge results retrieved")

        return knowledge

    except Exception as e:

        logger.error(f"Error retrieving medical knowledge: {str(e)}")
        return []



# Testing retriever using medical report

if __name__ == "__main__":

    report_path = "data/uploads/Sample Report.pdf"

    print("\n=================================")
    print("Reading Medical Report...")

    report_text = read_pdf(report_path)

    if not report_text:
        print("Failed to read report")
        exit()

    print("Report Successfully Read\n")

    # parse the report to extract lab values
    print("Parsing medical report...\n")

    parsed_data = parse_medical_report(report_text)

    if not parsed_data:
        print("No medical values found")
        exit()

    # lab results extracted by parser
    lab_results = parsed_data.get("lab_results", [])

    print("Extracted Lab Results:\n")

    for item in lab_results:

        test_name = item["test"]
        value = item["value"]
        unit = item["unit"]
        status = item["status"]

        # create query for retriever
        query = f"{test_name} {value} {unit}"

        print("---------------------------------")
        print(f"Query: {query}")
        print(f"Status: {status}\n")

        results = search_medical_knowledge(query)

        print("Retrieved Knowledge:\n")

        for r in results:
            print("•", r)

        print()