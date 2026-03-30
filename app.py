import os
import io
import sys
from flask import Flask, render_template, request
from flask import jsonify

from ocr_service.ocr_llm_extractor import run_ocr_pipeline
from agents.validation_agent import ValidationAgent
from agents.report_agent import report_chat_agent
from processing.pdf_reader import read_pdf
from processing.llm_extractor import llm_extract_medical_data
from processing.report_parser import parse_medical_report
from graph.agent_graph import build_medical_graph
from storage.database import init_database, save_report, generate_file_hash_from_bytes
from logger_config import logger

# For Dropdown purpose
def parse_guidance(text):

    if isinstance(text, list):
        return text
    
    tests = text.split("Test:")
    structured = []

    for t in tests:
        if not t.strip():
            continue

        lines = t.strip().split("\n")
        title = lines[0].strip()

        eat, avoid, exercise = [], [], ""

        mode = None
        for line in lines:
            line = line.strip()

            if "What to Eat" in line:
                mode = "eat"
            elif "What to Avoid" in line:
                mode = "avoid"
            elif "Exercise" in line:
                mode = "exercise"
            elif line.startswith("-"):
                if mode == "eat":
                    eat.append(line[1:].strip())
                elif mode == "avoid":
                    avoid.append(line[1:].strip())
                elif mode == "exercise":
                    exercise += line[1:].strip() + " "

        structured.append({
            "title": title,
            "eat": eat,
            "avoid": avoid,
            "exercise": exercise.strip()
        })

    return structured

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

app = Flask(__name__, template_folder="layouts", static_folder="")

UPLOAD_FOLDER = "data/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# @app.before_first_request
# def setup():
init_database()


graph = build_medical_graph()
validator = ValidationAgent()


@app.route("/", methods=["GET", "POST"])
def index():

    #global latest_analysis

    try:
        if request.method == "POST":

            file = request.files.get("file")

            if not file:
                return "No file uploaded"

            # READ FILE FIRST
            file_bytes = file.read()

            if not file_bytes:
                return "Empty file uploaded"

            # HASH BEFORE SAVING
            file_hash = generate_file_hash_from_bytes(file_bytes)

            # SAVE FILE
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
            with open(file_path, "wb") as f:
                f.write(file_bytes)

            logger.info(f"File uploaded: {file.filename}")

            # VALIDATION
            validation_result = validator.validate(file_path, file_hash)

            if not validation_result["is_valid"]:
                return render_template(
                    "main.html",
                    validation=validation_result,
                    error_message="Invalid file. Please upload a proper medical report."
                )
            
            # DUPLICATION
            if validation_result["is_duplicate"]:
                existing = validation_result["existing_result"]

                # storing analysis for chat
                #latest_analysis = existing.get("analysis", "")

                print(type(existing["guidance"]))
                print(existing["guidance"])

                return render_template(
                    "main.html",
                    medical_data=existing["medical_data"],
                    analysis=existing["analysis"],
                    explanation=existing["explanation"],
                    guidance=parse_guidance(existing["guidance"]),
                    validation=validation_result
                )

            # PROCESSING
            report_text = read_pdf(file_path)

            # OCR fallback (only if PDF text is weak)
            if not report_text or len(report_text.strip()) < 50:
                logger.warning("PDF parsing weak -> switching to OCR pipeline")

                ocr_result = run_ocr_pipeline(file_path)

                # Directly use OCR structured output
                medical_data = ocr_result

                state = {
                    "lab_results": medical_data.get("lab_results", [])
                }

                result = graph.invoke(state)

                result["medical_data"] = medical_data

                # SAVE (same DB, no change)
                save_report(file_hash, result)

                return render_template(
                    "main.html",
                    medical_data=result["medical_data"],
                    analysis=result["analysis"],
                    explanation=result["explanation"],
                    guidance=parse_guidance(result["guidance"]),
                    validation=validation_result
                )

            # Trying Regex pattern
            parsed_data = parse_medical_report(report_text)
            lab_results = parsed_data.get("lab_results", [])

            # Checking if parser failed or not
            bad_parsing = any(
                any(char.isdigit() for char in item.get("test", ""))
                for item in lab_results
            )
            missing_data = not lab_results

            # Fallback to LLM
            if missing_data or bad_parsing:
                logger.warning("Parser unreliable, switching to LLM extractor")
                parsed_data = llm_extract_medical_data(report_text)

            # Final data
            medical_data = parsed_data

            state = {
                "lab_results": medical_data.get("lab_results", [])
            }

            state["source"] = "ocr"
            state["confidence"] = "low"

            result = graph.invoke(state)

            # storing alanlysis for chat
            #latest_analysis = result.get("analysis", "")

            # FORCE ORIGINAL DATA (avoid LLM corruption)
            result["medical_data"] = medical_data

            print(type(result["guidance"]))
            print(result["guidance"])

            # SAVE
            save_report(file_hash, result)

            return render_template(
                "main.html",
                medical_data=result["medical_data"],
                analysis=result["analysis"],
                explanation=result["explanation"],
                guidance=parse_guidance(result["guidance"]),
                validation=validation_result
            )

        return render_template("main.html")

    except Exception as e:
        logger.error(f"App error: {str(e)}")
        return "Something went wrong"

# chat route
@app.route("/chat", methods=["POST"])
def chat():

    #global latest_analysis

    try:
        data = request.get_json()
        user_question = data.get("message", "")
        analysis = data.get("analysis", "")

        if not user_question:
            return jsonify({"response": "No question provided"})
        
        if not analysis:
            return jsonify({"response": "No report analysis available"})
        
        # calling the chat agent
        response = report_chat_agent(analysis, user_question)

        return jsonify({"response": response})
    
    except Exception as e:
        logger.error(f"Chat route error: {str(e)}")
        return jsonify({"response": "Chat failed"})

if __name__ == "__main__":
    init_database()
    app.run(host="0.0.0.0", port=5000, debug=True)