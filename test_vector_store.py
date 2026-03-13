from processing.pdf_reader import read_pdf
from processing.report_parser import parse_medical_report

from rag.vector_store import (
    create_vector_store,
    load_vector_store,
    generate_medical_documents
)

from logger_config import logger


try:

    logger.info("Starting medical report vector store test")


    # Generating medical knowledge
    logger.info("Generating medical knowledge dataset")

    documents = generate_medical_documents()

    logger.info(f"Total knowledge documents created: {len(documents)}")


    # Creating vector store
    logger.info("Creating FAISS vector store")

    create_vector_store(documents)


    # Load vector store
    logger.info("Loading FAISS vector store")

    vs = load_vector_store()

    if vs is None:
        logger.error("Vector store loading failed")
        exit()

    logger.info("Vector store loaded successfully")


    # Read medical report
    logger.info("Reading medical report PDF")

    text = read_pdf("data/uploads/Sample Report.pdf")

    if not text.strip():
        logger.warning("No text extracted from the PDF")
        exit()

    logger.info("Text extracted successfully")


    # Parsing the medical report
    logger.info("Parsing medical report")

    parsed_data = parse_medical_report(text)

    lab_results = parsed_data.get("lab_results", [])

    if not lab_results:
        logger.warning("No lab results found in report")
        exit()

    logger.info(f"Extracted {len(lab_results)} lab results")

    print("\n===================================")
    print("Testing similarity search using lab values\n")


    # Running similarity search
    for item in lab_results:

        test_name = item["test"]
        value = item["value"]
        unit = item["unit"]
        status = item["status"]

        query = f"{test_name} {value} {unit}"

        logger.info(f"Running similarity search for query: {query}")

        results = vs.similarity_search(query, k=2)

        logger.info(f"Retrieved {len(results)} relevant chunks")

        print("\n-----------------------------------")
        print(f"Query: {query}")
        print(f"Status: {status}\n")

        for i, doc in enumerate(results, start=1):

            print(f"Result {i}:")
            print(doc.page_content)
            print()

    logger.info("Vector store testing completed successfully")


except Exception as e:

    logger.error(f"Error during vector store testing: {str(e)}")