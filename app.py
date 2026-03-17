import os
from flask import Flask, render_template, request

from agents.validation_agent import ValidationAgent

from processing.pdf_reader import read_pdf
from processing.report_parser import parse_medical_report

from graph.agent_graph import build_medical_graph

from storage.database import (
    init_database,
    save_report
)

from logger_config import logger


app = Flask(
    __name__,
    template_folder="layouts",
    static_folder=""
)

# Folder to store uploaded PDFs
UPLOAD_FOLDER = "data/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Initialize database
init_database()

# Load LangGraph
graph = build_medical_graph()

# Initialize Validation Agent
validator = ValidationAgent()


@app.route("/", methods=["GET", "POST"])
def index():

    try:
        if request.method == "POST":

            file = request.files.get("file")

            if not file:
                return "No file uploaded"

            # Save file
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
            file.save(file_path)

            logger.info(f"File uploaded: {file.filename}")

            # VALIDATION
            validation_result = validator.validate(file_path)

            # If invalid → stop here
            if not validation_result["is_valid"]:
                return render_template(
                    "main.html",
                    errors=validation_result["errors"]
                )

            # If duplicate → return cached result
            if validation_result["is_duplicate"]:
                logger.info("Returning cached result (Validation Agent)")

                existing = validation_result["existing_result"]

                return render_template(
                    "main.html",
                    medical_data=existing["medical_data"],
                    analysis=existing["analysis"],
                    explanation=existing["explanation"],
                    guidance=existing["guidance"],
                    validation=validation_result
                )

            # PROCESSING
            logger.info("Running full pipeline")

            report_text = read_pdf(file_path)
            medical_data = parse_medical_report(report_text)

            state = {
                "medical_data": medical_data
            }

            result = graph.invoke(state)


            # SAVE RESULT
            file_hash = validation_result["file_hash"]
            save_report(file_hash, result)

            logger.info("Pipeline completed successfully")

            return render_template(
                "main.html",
                medical_data=result["medical_data"],
                analysis=result["analysis"],
                explanation=result["explanation"],
                guidance=result["guidance"],
                validation=validation_result
            )

        return render_template("main.html")

    except Exception as e:
        logger.error(f"App error: {str(e)}")
        return "Something went wrong"


if __name__ == "__main__":
    app.run(debug=True)