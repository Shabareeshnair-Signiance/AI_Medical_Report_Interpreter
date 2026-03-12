import os
from pathlib import Path
import logging

logging.basicConfig(level = logging.INFO, format = '[%(asctime)s]: %(message)s:')

list_of_files = [
    "__init__.py",
    "agents/report_agent.py",
    "agents/explanation_agent.py",
    "agents/guidance_agent.py",
    "graph/agent_graph.py",
    "processing/pdf_reader.py",
    "processing/ocr_reader.py",
    "processing/report_parser.py",
    "rag/vector_store.py",
    "rag/retriever.py",
    "storage/database.py",
    "layouts/main.html",
    "design/theme.css",
    "logic/script.js",
    "logger_config.py",
    ".env",
    "requirements.txt"
]


for filepath in list_of_files:
    filepath = Path(filepath)
    filedir, filename = os.path.split(filepath)

    if filedir !="":
        os.makedirs(filedir, exist_ok = True)
        logging.info(f"Creating directory; {filedir} for the file: {filename}")

    if (not os.path.exists(filepath)) or (os.path.getsize(filepath) == 0):
        with open(filepath, "w") as f:
            pass
            logging.info(f"Creating empty file: {filepath}")

    else:
        logging.info(f"{filename} is already exists")