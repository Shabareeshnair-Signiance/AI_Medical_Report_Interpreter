import pdfplumber
from logger_config import logger

def read_pdf(file_path: str) -> str:
    """
    Reads a medical report PDF and extracts all text.
    
    Args:
        file_path (str): Path to the uploaded PDF file.
        
    Returns:
        str: Extracted text from the PDF.
    """

    try:
        logger.info(f"Opening PDF file: {file_path}")

        extracted_text = ""

        with pdfplumber.open(file_path) as pdf:

            total_pages = len(pdf.pages)
            logger.info(f"PDF loaded successfully. Total pages: {total_pages}")

            for page_number, page in enumerate(pdf.pages, start = 1):
                logger.info(f"Reading page {page_number}")
                page_text = page.extract_text()

                if page_text:
                    extracted_text += page_text + "\n"
                else:
                    logger.warning(f"No text found on page {page_number}")
        logger.info("PDF text extraction completed")

        return extracted_text
    
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return ""
    
    except Exception as e:
        logger.error(f"Error reading PDF: {str(e)}")
        return ""
    
# This line of code is to test the PDF reading functionality when this script is run directly.
#if __name__ == "__main__":
#    sample_path = "data/uploads/Sample Report.pdf"
#    text = read_pdf(sample_path)
    # Print the first 500 characters of the extracted text for verification 
#    print(text[:500]) 