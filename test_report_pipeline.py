from storage.database import (
    init_database,
    generate_file_hash,
    check_existing_report,
    save_report
)

from processing.pdf_reader import read_pdf
from processing.report_parser import parse_medical_report

from agents.report_agent import report_agent
from agents.explanation_agent import explanation_agent
from agents.guidance_agent import guidance_agent


# initialize database (create table if not exists)
init_database()


# path of sample report
#report_path = "data/uploads/Sample Report.pdf"
report_path = "data/uploads/Glucose_report.pdf"

print("\nReading medical report...\n")


# generate hash for uploaded file
file_hash = generate_file_hash(report_path)


# check if report already processed earlier
cached_result = check_existing_report(file_hash)

if cached_result:

    print("Report loaded from database cache\n")

    # load saved state
    state = cached_result

else:

    print("Processing report using AI agents...\n")

    # read text from PDF
    report_text = read_pdf(report_path)

    if not report_text:
        print("Failed to read report")
        exit()

    # parse medical report
    parsed_data = parse_medical_report(report_text)

    if not parsed_data:
        print("Failed to parse report")
        exit()

    # extract lab results
    lab_results = parsed_data.get("lab_results", [])

    # convert lab results list → dictionary
    medical_data = {}

    for item in lab_results:

        test_name = item["test"]
        value = item["value"]
        unit = item["unit"]
        ref_range = item.get("reference_range", "unknown")

        medical_data[test_name] = f"{value} {unit} (normal range {ref_range})"

    # create initial agent state
    state = {
        "medical_data": medical_data
    }

    # run Report Agent (Agent 1)
    state = report_agent(state)

    # run Explanation Agent (Agent 2)
    state = explanation_agent(state)

    # run Guidance Agent (Agent 3)
    state = guidance_agent(state)

    # save result to database for caching
    save_report(file_hash, state)


print("\n========= FINAL RESULT =========\n")

print("Analysis:\n", state.get("analysis", "No analysis generated"))

print("\nExplanation:\n", state.get("explanation", "No explanation generated"))

print("\nGuidance:\n", state.get("guidance", "No guidance generated"))