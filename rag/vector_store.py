import os
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from logger_config import logger


# Folder where FAISS index will be stored
VECTOR_DB_PATH = "data/vector_store"

# Medical lab Knowldege dataset

LAB_TEST_KNOWLEDGE = {

    "Hemoglobin": {
        "range": "13-17 g/dL",
        "low": "Low hemoglobin may indicate anemia or blood loss",
        "high": "High hemoglobin may indicate dehydration or lung disease"
    },

    "Glucose": {
        "range": "70-99 mg/dL",
        "low": "Low glucose may cause dizziness, weakness, or hypoglycemia",
        "high": "High glucose may indicate diabetes or insulin resistance"
    },

    "Platelet Count": {
        "range": "150000-450000 /mcL",
        "low": "Low platelet count increases bleeding risk",
        "high": "High platelet count may indicate inflammation or infection"
    },

    "HDL Cholesterol": {
        "range": "40-60 mg/dL",
        "low": "Low HDL increases risk of heart disease",
        "high": "High HDL is protective for cardiovascular health"
    },

    "LDL Cholesterol": {
        "range": "0-100 mg/dL",
        "low": "Very low LDL may indicate malnutrition",
        "high": "High LDL increases risk of heart disease"
    },

    "White Blood Cell Count": {
        "range": "4000-11000 cells/mcL",
        "low": "Low WBC may indicate immune suppression",
        "high": "High WBC may indicate infection or inflammation"
    },

    "Triglycerides": {
        "range": "0-150 mg/dL",
        "low": "Low triglycerides are usually not harmful",
        "high": "High triglycerides increase cardiovascular risk"
    },

    "Creatinine": {
        "range": "0.6-1.3 mg/dL",
        "low": "Low creatinine may indicate muscle loss",
        "high": "High creatinine may indicate kidney dysfunction"
    },

    "Calcium": {
        "range": "8.6-10.2 mg/dL",
        "low": "Low calcium may cause muscle spasms",
        "high": "High calcium may indicate hyperparathyroidism"
    },

    "Sodium": {
        "range": "135-145 mEq/L",
        "low": "Low sodium may cause confusion or seizures",
        "high": "High sodium may indicate dehydration"
    }

}

# Generating knowledge documents
def generate_medical_documents():
    docs = []

    for test, info in LAB_TEST_KNOWLEDGE.items():

        text = (
            f"{test} normal range is {info['range']}. "
            f"If {test} is below normal: {info['low']}. "
            f"If {test} is above normal: {info['high']}."
        )

        docs.append(text)

    return docs

# creating vector store
def create_vector_store(documents):
    """
    Create FAISS vector database from documents.
    
    Args:
        documents (list): List of text chunks
        
    Returns:
        vector_store: FAISS vector store object
    """

    try:
        logger.info("Loading embedding model")

        # Loading sentence transformer embedding model
        embeddings = HuggingFaceEmbeddings(
            model_name = "sentence-transformers/all-MiniLM-L6-v2"
        )

        logger.info("Creating FAISS vector store")

        # Converting documents into vector store embeddings
        vector_store = FAISS.from_texts(documents, embeddings)

        # Creating directory into vector embeddings
        os.makedirs(VECTOR_DB_PATH, exist_ok = True)

        # Saving FAISS index
        vector_store.save_local(VECTOR_DB_PATH)

        logger.info("Vector store created and saved successfully")

        return vector_store

    except Exception as e:
        logger.error(f"Error creating vector store: {str(e)}")
        return None


# Loading the vector store
def load_vector_store():
    """
    Load existing FAISS vector database.

    Returns:
        vector_store: Loaded FAISS vector store
    """

    try:
        logger.info("Loading existing vector store")

        embeddings = HuggingFaceEmbeddings(
            model_name = "sentence-transformers/all-MiniLM-L6-v2"
        )

        vector_store = FAISS.load_local(
            VECTOR_DB_PATH,
            embeddings,
            allow_dangerous_deserialization = True
        )

        logger.info("Vector store loaded successfully")

        return vector_store

    except Exception as e:
        logger.error(f"Error loading vector store: {str(e)}")
        return None
    

# Testing the vector store creation and loading
# if __name__ == "__main__":
    
#     print("\nGenerating medical knowledge documents...\n")
#     docs = generate_medical_documents()
#     print(f"Total medical knowledge documents: {len(docs)}")
#     vs = create_vector_store(docs)

#     if vs:
#         print("Vector store created successfully\n")
#         query = "HDL Cholesterol 46 mg/dL"
#         results = vs.similarity_search(query, k=2)
#         print("Retrieved Knowledge:\n")

#         for r in results:
#             print("-", r.page_content)