import os
import re
import io
import sys
import json
from flask import Flask, render_template, request
from flask import jsonify

from ocr_service.ocr_llm_extractor import run_ocr_pipeline
from agents.validation_agent import ValidationAgent
from agents.report_agent import report_chat_agent
from processing.pdf_reader import read_pdf
from processing.llm_extractor import llm_extract_medical_data
from processing.report_parser import parse_medical_report
from graph.agent_graph import build_medical_graph
from storage.database import init_database, save_report, generate_file_hash_from_bytes, check_existing_report

from graph.doctor_graph import app as doctor_app
from storage.medical_history_db import get_history_for_patient, init_history_database, calculate_file_hash
from agents.doctor_validation_agent import DoctorValidationAgent

from logger_config import logger

doc_validator = DoctorValidationAgent()

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

def parse_explanation(data):

    # Handles JSON string from DB
    if isinstance(data, str):
        try:
            parsed = json.loads(data)
            if isinstance(parsed, list):
                return parsed
        except:
            pass

    # NEW: handle list format (our updated agent)
    if isinstance(data, list):
        return data

    # OLD fallback: handle string (for backward compatibility)
    structured = []
    parts = data.split("Test Name:")

    for p in parts:
        if not p.strip():
            continue

        lines = p.strip().split("\n")
        title = lines[0].strip()

        content = "\n".join(lines[1:]).strip()

        structured.append({
            "test": title,
            "content": content
        })

    return structured

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

app = Flask(__name__, template_folder="layouts", static_folder="")

UPLOAD_FOLDER = "data/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


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
                    explanation=parse_explanation(existing["explanation"]),
                    guidance=parse_guidance(existing["guidance"]),
                    validation=validation_result
                )

            # PROCESSING
            report_text = read_pdf(file_path)


            # OCR fallback (only if PDF text is weak)
            if not report_text or len(report_text.strip()) < 50:
                logger.info("Scanned Document Detected -> switching to Vision AI pipeline")

                # Milisecond Cache fetch for Vision AI
                vision_cache = check_existing_report(file_hash)

                if vision_cache:
                    logger.info("Vision AI Cache Hit! Loading instantly from database...")
                    return render_template(
                        "main.html",
                        medical_data = vision_cache["medical_data"],
                        analysis = vision_cache["analysis"],
                        explanation=parse_explanation(vision_cache["explanation"]),
                        guidance=parse_guidance(vision_cache["guidance"]),
                        validation=validation_result
                    )

                # If not cached, run the expensive Vision AI
                ocr_result = run_ocr_pipeline(file_path)

                # Directly use OCR structured output
                medical_data = ocr_result

                state = {
                    "lab_results": medical_data.get("lab_results", [])
                }

                # Vision AI metadata addition
                state["source"] = "scanned_image_vision_ai"
                state["confidence"] = "high"

                result = graph.invoke(state)

                result["medical_data"] = medical_data

                db_result = result.copy()

                # Convert explanation list → string for DB
                if isinstance(db_result.get("explanation"), list):
                    db_result["explanation"] = json.dumps(db_result["explanation"])

                # SAVE (same DB, no change)
                save_report(file_hash, db_result)

                return render_template(
                    "main.html",
                    medical_data=result["medical_data"],
                    analysis=result["analysis"],
                    explanation=parse_explanation(result["explanation"]),
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

            db_result = result.copy()

            # Convert explanation list → string for DB
            if isinstance(db_result.get("explanation"), list):
                db_result["explanation"] = json.dumps(db_result["explanation"])

            # SAVE
            save_report(file_hash, result)

            return render_template(
                "main.html",
                medical_data=result["medical_data"],
                analysis=result["analysis"],
                explanation=parse_explanation(result["explanation"]),
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
    


# This is a new page for doctor's
@app.route("/doctor", methods=["GET", "POST"])
def doctor_dashboard():
    try:
        if request.method == "POST":
            file = request.files.get("file")
            if not file:
                return "No file uploaded"

            # 1. Save the file temporarily
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
            file.save(file_path)

            # 2. PHASE 1: VALIDATION (The New Step)
            # This uses your new Agent to check Hash, Identity, and History
            validation = doc_validator.validate_for_doctor(file_path)

            # Vision Rescue block
            if not validation.get("is_valid"):
                text_check = read_pdf(file_path)
                if not text_check or len(text_check.strip()) < 50:
                    logger.info("Text validation failed (likely a scanned image). Attempting Vision AI Rescue...")
                    import hashlib
                    import re
                    from storage.medical_history_db import get_existing_analysis
                    from processing.llm_doctor_validator import vision_extract_doctor_identity
                    
                    sha256 = hashlib.sha256()
                    with open(file_path, "rb") as f:
                        while chunk := f.read(8192): sha256.update(chunk)
                    rescue_hash = sha256.hexdigest()
                    
                    identity = vision_extract_doctor_identity(file_path)
                    if identity and identity.get("name"):
                        existing_row = get_existing_analysis(rescue_hash)
                        
                        raw_pid = identity.get("identifier")
                        true_uid = raw_pid
                        cached_lab_results = []
                        
                        # 1. Force the date into YYYY-MM-DD format so the database can match it
                        raw_date = str(identity.get("date", ""))
                        clean_date = raw_date
                        if raw_date:
                            match_yyyy = re.search(r"(\d{4})[\/\-\.](\d{1,2})[\/\-\.](\d{1,2})", raw_date)
                            match_dd = re.search(r"(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})", raw_date)
                            if match_yyyy:
                                clean_date = f"{match_yyyy.group(1)}-{int(match_yyyy.group(2)):02d}-{int(match_yyyy.group(3)):02d}"
                            elif match_dd:
                                clean_date = f"{match_dd.group(3)}-{int(match_dd.group(2)):02d}-{int(match_dd.group(1)):02d}"
                        
                        if existing_row:
                            past_history = get_history_for_patient(pid=raw_pid, name=identity.get("name"))
                            if past_history:
                                true_uid = past_history[0].get("patient_id") or past_history[0].get("uid") or past_history[0].get("pid") or raw_pid
                                
                                # 2. Match the cleaned date to get the lab results for Phase 2
                                for item in past_history:
                                    if item.get("date") == clean_date:
                                        cached_lab_results.append({
                                            "test": item.get("test") or item.get("parameter"),
                                            "value": item.get("value") or item.get("result_value"),
                                            "reference_range": item.get("reference_range") or item.get("ref_range")
                                        })
                                        
                                # 3. BULLETPROOF FALLBACK: If date matching still fails, grab the latest DB data
                                if not cached_lab_results:
                                    logger.warning("Exact date match failed. Falling back to latest DB records for duplicate.")
                                    fallback_date = max(item.get("date", "") for item in past_history)
                                    clean_date = fallback_date  # Sync report date so Phase 2 graphs work!
                                    for item in past_history:
                                        if item.get("date") == fallback_date:
                                            cached_lab_results.append({
                                                "test": item.get("test") or item.get("parameter"),
                                                "value": item.get("value") or item.get("result_value"),
                                                "reference_range": item.get("reference_range") or item.get("ref_range")
                                            })

                        validation = {
                            "is_valid": True,
                            "status": "DUPLICATE" if existing_row else "NEW",
                            "file_hash": rescue_hash,
                            "pid": true_uid,
                            "patient_name": identity.get("name"),
                            "report_date": clean_date,  # Uses the cleaned/synced date!
                            "existing_analysis": {
                                "llm_insight": existing_row[0] if existing_row else "N/A", 
                                "clinical_suggestion": existing_row[1] if existing_row else "N/A",
                                "lab_results": cached_lab_results
                            } if existing_row else None
                        }
            
            if not validation["is_valid"]:
                return render_template("doctor.html", 
                                       error="Could not identify patient in this report.",
                                       validation=validation)
            
            # Helper function logic for Normalization
            def get_clean_trends(pid, patient_name, current_date=None, current_tests = None, is_scanned = False):
                from storage.medical_history_db import get_trends_for_patient
                raw_data = get_trends_for_patient(pid, patient_name)

                if not raw_data:
                    return [], [], []

                for row in raw_data:
                    name_options = [row.get("parameter"), row.get("test"), row.get("biomarker"), row.get("name")]
                    row["parameter"] = next((name for name in name_options if name), "Unknown Biomarker")
                    row["result_value"] = row.get("value") or row.get("result") or "N/A"
                    row["ref_range"] = row.get("reference_range") or row.get("ref_range") or "N/A"
                    row["status"] = str(row.get("status", "")).upper()

                    # Vision Rescue
                    if is_scanned:
                        raw_history_date = str(row.get("date", ""))
                        match_yyyy = re.search(r"(\d{4})[\/\-\.](\d{1,2})[\/\-\.](\d{1,2})", raw_history_date)
                        match_dd = re.search(r"(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})", raw_history_date)
                        
                        if match_yyyy:
                            row["date"] = f"{match_yyyy.group(1)}-{int(match_yyyy.group(2)):02d}-{int(match_yyyy.group(3)):02d}"
                        elif match_dd:
                            row["date"] = f"{match_dd.group(3)}-{int(match_dd.group(2)):02d}-{int(match_dd.group(1)):02d}"

                # Finding the latest datte in all records
                # latest_date = max(row.get("date", "") for row in raw_data)

                # # splitting into current (table) and all (graph)
                # current_only = [row for row in raw_data if row.get("date") == latest_date]

                # Use the actual uploaded report date if provided
                # Otherwise fall back to latest date in DB
                if current_date:
                    latest_date = current_date
                else:
                    latest_date = max(row.get("date", "") for row in raw_data)

                # Current test name fetch
                if current_tests:
                    # Filter by actual test names from uploaded report
                    current_test_names = set(t.lower().strip() for t in current_tests)
                    current_only = [
                        row for row in raw_data
                        if row.get("parameter", "").lower().strip() in current_test_names
                    ]
                else:
                    current_only = [row for row in raw_data if row.get("date") == latest_date]

                # Get current test names for comparison
                current_names = set(row.get("parameter", "").lower().strip() for row in current_only)

                # Previous tests = not in current date AND name not in current report
                previous_only = [
                    row for row in raw_data
                    if row.get("date") != latest_date
                    and row.get("parameter", "").lower().strip() not in current_names
                ]

                # Deduplicate previous_only — keep only latest occurrence of each test
                seen = {}
                for row in sorted(previous_only, key=lambda x: x.get("date", "")):
                    seen[row.get("parameter", "").lower().strip()] = row
                previous_only = list(seen.values())

                return current_only, raw_data, previous_only

            # 3. PHASE 2: DUPLICATE HANDLING
            if validation["status"] == "DUPLICATE":

                # fetching the safely stored date from the DB for cached reports
                if not validation.get("report_date") or validation.get("report_date") == "Not Found":
                    try:
                        import sqlite3
                        # Using DB_PATH or exact database name here
                        from storage.medical_history_db import DB_PATH
                        
                        conn = sqlite3.connect(DB_PATH) 
                        cursor = conn.cursor()
                        cursor.execute("SELECT report_date FROM patient_reports WHERE file_hash=?", (validation.get("file_hash"),))
                        db_result = cursor.fetchone()
                        if db_result and db_result[0]:
                            validation["report_date"] = db_result[0] # Inject the missing date!
                        conn.close()
                    except Exception as e:
                        logger.error(f"Could not fetch cached date: {e}")

                existing_row = validation.get("existing_analysis")
                
                dup_text_check = read_pdf(file_path)
                is_scanned_dup = not dup_text_check or len(dup_text_check.strip()) < 50
                
                #t_data = get_trends_for_patient(validation.get("pid"))
                existing = validation.get("existing_analysis")
                curr_tests = [t.get("test") or t.get("parameter") for t in (existing.get("lab_results", []) if existing and isinstance(existing, dict) else [])]
                
                t_data, all_trends, prev_tests = get_clean_trends(validation.get("pid"), validation.get("patient_name"), validation.get("report_date"), curr_tests, is_scanned=is_scanned_dup)
                t_insight = existing_row["llm_insight"] if existing_row else "N/A"
                c_suggestion = existing_row["clinical_suggestion"] if existing_row else "N/A"
                past_history = get_history_for_patient(pid=validation.get("pid"), name=validation.get("patient_name"))
                
                return render_template(
                    "doctor.html",
                    validation=validation,
                    #trends_data = t_data,
                    trends=t_data,
                    all_trends = all_trends,
                    previous_tests = prev_tests,
                    trend_insight=t_insight,
                    clinical_suggestion=c_suggestion,
                    history=past_history,
                    report={"patient_name": validation.get("patient_name")},
                    status="CACHED"
                )

            # 4. PHASE 3: NEW PROCESSING (Run LangGraph)
            input_state = {
                "file_path": file_path, 
                "file_hash": validation["file_hash"]
            }
            
            logger.info("Running Doctor's Clinical Workflow for new/updated report")

            # The Multi modal router
            # from processing.pdf_reader import read_pdf
            report_text_check = read_pdf(file_path)

            # creating a tracker variable
            is_scanned_report = False

            if report_text_check and len(report_text_check.strip()) > 50:
                logger.info("Digital Text PDF detected. Running ORIGINAL Doctor App.")
                final_output = doctor_app.invoke(input_state)
            else:
                logger.info("Scanned Image detected. Running NEW Vision App.")
                from graph.doctor_graph import vision_app
                final_output = vision_app.invoke(input_state)

                is_scanned_report = True

            #final_output = doctor_app.invoke(input_state)

            # this ensures that even on the first upload we get the data just saved by the agent
            curr_tests = [t.get("test") or t.get("parameter") for t in final_output.get("current_report", {}).get("lab_results", [])]
            t_data, all_trends, prev_tests = get_clean_trends(validation.get("pid"), validation.get("patient_name"), validation.get("report_date"), curr_tests, is_scanned=is_scanned_report)

            # Fetch fresh history for the UI
            past_history = get_history_for_patient(
                pid=validation.get("pid"),
                name=validation.get("patient_name")
            )

            # Ensuring i don't pass None to the UI
            report_data = final_output.get("current_report", {})
            if not report_data.get("patient_name"):
                report_data["patient_name"] = validation.get("patient_name", "Unknown Patient")

            return render_template(
                "doctor.html",
                validation=validation, 
                report=report_data,
                clinical_suggestion=final_output.get("clinical_suggestion", "N/A"),
                trend_insight=final_output.get("trend_insight", "N/A"),
                #trends=final_output.get("trends", []),
                trends=t_data,
                all_trends = all_trends,
                previous_tests=prev_tests,
                history=past_history if past_history else [],
                status="PROCESSED"
            )

        return render_template("doctor.html")

    except Exception as e:
        logger.error(f"Doctor Dashboard Error: {str(e)}")
        return f"Error: {str(e)}"


# Doctor's chatbot assistant
@app.route("/chatbot", methods = ["POST"])
def doctor_chat():
    try:
        data = request.get_json()
        user_message = data.get("message", "")
        patient_context = data.get("context", "")

        if not user_message:
            return jsonify({"reply": "Please ask a question.", "next_chips": []})
        
        # building system prompt with patient context injected
        system_prompt = f"""You are an advanced Clinical Assistant helping a doctor.
        
Current Patient Context:
{patient_context}

Your Role & Clinical Constraints:
- Answer questions, explain abnormal values, and suggest follow-up tests.
- THE DOER: If the doctor asks you to draft paperwork (e.g., SOAP note, referral letter, patient email), WRITE IT professionally and completely based on the lab data. 
- NEVER make a final diagnosis; always defer to doctor judgement.
- Keep conversational responses under 150 words. Drafted paperwork can be as long as necessary.

STRICT OUTPUT FORMAT:
You MUST return your entire response as a valid JSON object. Do not output anything outside the JSON.
The JSON must have EXACTLY two keys: "reply" and "next_chips".

1. "reply": Your response formatted in Markdown. You MUST wrap every specific test name and numerical value in **bold** markdown.
2. "next_chips": An array of 2 to 3 short string suggestions for the doctor's next click. At least one MUST be an Action/Paperwork chip starting with an emoji (e.g., "📝 Draft SOAP Note", "✉️ Draft Patient Email").

Example JSON Output:
{{
    "reply": "The patient's **Fasting Glucose** is elevated at **124 mg/dL**...",
    "next_chips": ["Draft Pre-Diabetes Patient Note", "What is the Cholesterol?"]
}}
"""

        from llm.llm_provider import get_llm
        from langchain_core.messages import HumanMessage, SystemMessage

        llm = get_llm()
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ]

        response = llm.invoke(messages)
        raw_content = response.content if hasattr(response, 'content') else str (response)

        # return jsonify({"reply": reply})
        clean_json_str = re.sub(r"```json\n?|```", "", raw_content).strip()

        # parsing the string into python dictionary and send it to the frontend
        try:
            ai_output = json.loads(clean_json_str)
            # this directly return {"reply": "...", "next_chips": [...]}
            return jsonify(ai_output), 200
        except json.JSONDecodeError:
            # Defensive fallback
            logger.warning("LLM Failed to output valid JSON in chatbot route")
            return jsonify({
                "reply": raw_content,
                "next_chips": ["Retry Request"]
            }), 200
    
    except Exception as e:
        logger.error(f"Doctor Chat Error: {str(e)}")
        return jsonify({
            "reply": "Sorry, I could not process your question. Please try again.",
            "next_chips": []
        }), 500

    # except Exception as e:
    #     logger.error(f"Doctor Chat Error: {str(e)}")
    #     return jsonify({"reply": "Sorry, I could not process your question. Please try again."})


if __name__ == "__main__":
    init_database()
    init_history_database()
    app.run(host="0.0.0.0", port=5000, debug=True)