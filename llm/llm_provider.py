from langchain_openai import ChatOpenAI
from logger_config import logger
from dotenv import load_dotenv
import os


# loading environment variables from .env file
load_dotenv()


def get_llm():
    """
    Initialize and return the LLM used by all agents.
    """

    try:
        logger.info("Initializing OpenAI LLM")

        # reading the API key from env variables
        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            logger.error("OPENAI_API_KEY not found in environment variables")
            return None
        
        # initializing the LLM
        llm = ChatOpenAI(
            model = "gpt-4o-mini",
            temperature = 0.3,
            api_key=api_key
        )

        logger.info("OpenAI LLM initialized successfully")

        return llm
    
    except Exception as e:
        logger.error(f"LLM initialization failed: {str(e)}")
        return None
    
# A quick test to know whether API key is working or not
# if __name__ == "__main__":
#     llm = get_llm()

#     if llm:
#         response = llm.invoke("Say hello in one sentence.")
#         print(response.content)