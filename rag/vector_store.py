import os
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from logger_config import logger


# Folder where FAISS index will be stored
VECTOR_DB_PATH = "data/vector_store"

def create_vector_store(documents):
    """
    Create FAISS vector database from documents.
    
    Args:
        documents (list): List of text chunks
        
    Returns:
        vector_store: FAISS vector store object
    """

    try:
        logger.info("Initializing embedding model")

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
if __name__ == "__main__":
    sample_docs = [
        "Hemoglobin normal range for adults is 13 to 17 g/dL",
        "High glucose levels may indicate diabetes",
        "Normal fasting glucose level is between 70 and 99 mg/dL",
        "Low platelet count may increase bleeding risk",
        "High cholesterol increases risk of heart disease",
        "Normal white blood cell count is between 4000 and 11000 cells per microliter"
    ]

    vs = create_vector_store(sample_docs)

    print("Vector store created successfully")