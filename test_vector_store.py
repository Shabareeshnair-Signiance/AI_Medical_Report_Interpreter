from processing.pdf_reader import read_pdf
from rag.vector_store import create_vector_store, load_vector_store
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Reading medical report
text = read_pdf("data/uploads/sample_report.pdf")

# splitting text into chunks
splitter = RecursiveCharacterTextSplitter(chunk_size = 300, chunk_overlap = 50)
documents = splitter.split_text(text)

# creating vector store
create_vector_store(documents)

# loading the vector store
vs = load_vector_store()

# testing vector store
query = "medical test results blood report cholesterol glucose platelet values "

results = vs.similarity_search(query, k=2)

for doc in results:
    print(doc.page_content)