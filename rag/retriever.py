from rag.vector_store import load_vector_store

#from processing.pdf_reader import read_pdf
#from processing.report_parser import parse_medical_report

from logger_config import logger


def get_retriever():
    """
    Load vector store and convert it into a retriever.
    """

    try:

        logger.info("Loading vector store")

        vector_store = load_vector_store()

        if vector_store is None:
            logger.error("Vector store not found or empty")
            return None

        retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 3}
        )

        logger.info("Retriever created successfully")

        return retriever

    except Exception as e:

        logger.error(f"Error creating retriever: {str(e)}")
        return None


def clean_query(query):
    """
    Ensure the query is a clean string and not a large object.
    """

    if not isinstance(query, str):
        query = str(query)

    query = query.strip()

    # prevent extremely long logs
    if len(query) > 200:
        query = query[:200] + "..."

    return query


def search_medical_knowledge(query: str, test_name: str):
    """
    Search medical knowledge using retriever.
    Filter results so only relevant lab test knowledge is returned.
    """

    try:

        retriever = get_retriever()

        if retriever is None:
            return []

        # clean the query before logging
        safe_query = clean_query(query)

        logger.info(f"Searching vector store for: {safe_query}")

        # retrieve top results
        results = retriever.invoke(query)

        filtered_results = []

        for doc in results:

            content = doc.page_content

            # filter by test name
            if test_name.lower() in content.lower():
                filtered_results.append(content)

        # fallback if filtering removes everything
        if not filtered_results:
            filtered_results = [doc.page_content for doc in results]

        logger.info(f"{len(filtered_results)} knowledge results retrieved")

        return filtered_results

    except Exception as e:

        logger.error(f"Error retrieving medical knowledge: {str(e)}")

        return []



# Testing retriever using sample medical report
# if __name__ == "__main__":

#     report_path = "data/uploads/Sample Report.pdf"

#     print("\n=================================")
#     print("Reading Medical Report...")

#     report_text = read_pdf(report_path)

#     if not report_text:
#         print("Failed to read report")
#         exit()

#     print("Report Successfully Read\n")

#     # parse report to extract lab values
#     print("Parsing medical report...\n")

#     parsed_data = parse_medical_report(report_text)

#     if not parsed_data:
#         print("No medical values found")
#         exit()

#     # extracted lab results
#     lab_results = parsed_data.get("lab_results", [])

#     print("Extracted Lab Results:\n")

#     for item in lab_results:

#         test_name = item["test"]
#         value = item["value"]
#         unit = item["unit"]
#         status = item["status"]

#         # create search query
#         query = f"{test_name} {value} {unit}"

#         print("---------------------------------")
#         print(f"Query: {query}")
#         print(f"Status: {status}\n")

#         # search knowledge
#         results = search_medical_knowledge(query, test_name)

#         print("Retrieved Knowledge:\n")

#         for r in results:
#             print("•", r)

#         print()