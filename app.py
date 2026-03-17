from flask import Flask, render_template, request
import os

from processing.pdf_reader import read_pdf
from processing.report_parser import parse_medical_report

from graph.agent_graph import build_medical_graph

from storage.database import (
    init_database,
    generate_file_hash,
    check_existing_report,
    save_report
)

from logger_config import logger


app = Flask(__name__)

# Folder to store uploaded PDFs
UPLOAD_FOLDER = "data/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# initialize database at startup
init_database()

# Loading LangGraph once
graph = build_medical_graph()

@app.route("/", methods = ["GET", "POST"])
def index():

    try:
        if request.method == "POST":
            file = request.files.get("file")

            if not file:
                return "No file uploaded"
            
            # Saving file
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
            file.save(file_path)

            logger.info(f"File uploaded: {file.filename}")

            # generating file hash
            file_hash = generate_file_hash(file_path)

            if not file_hash:
                return "Error generating file hash"
            
            # checking database (CACHE)
            cached_result = check_existing_report(file_hash)

            if cached_result:
                logger.info("Returning cached result")

                return render_template(
                    "main.html",
                    medical_data = cached_result["medical_data"],
                    analysis = cached_result["analysis"],
                    explanation = cached_result["explanation"],
                    guidance = cached_result["guidance"]
                )
            
            # Running the Full Pipeline
            logger.info("Running full Pipeline")

            # Reading PDF
            report_text = read_pdf(file_path)

            # Parse medical values
            medical_data = parse_medical_report(report_text)

            # Preparing the state
            state = {
                "medical_data": medical_data
            }

            # running langgraph
            result = graph.invoke(state)

            # saving result in DB
            save_report(file_hash, result)

            logger.info("Pipeline completed successfully")

            return render_template(
                "main.html",
                medical_data = result["medical_data"],
                analysis = result["analysis"],
                explanation = result["explanation"],
                guidance = result["guidance"]
            )

        return render_template("main.html")
        
    except Exception as e:
        logger.error(f"App error: {str(e)}")
        return "Something went wrong"
    
if __name__ == "__main__":
    app.run(debug = True)