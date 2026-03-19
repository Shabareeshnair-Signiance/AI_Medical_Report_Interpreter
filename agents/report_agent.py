from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from llm.llm_provider import get_llm
from logger_config import logger


def report_agent(state: dict):
    """
    Production-ready Doctor-Focused Report Agent (Multi-test, UI-friendly output)
    """

    try:
        logger.info("Running Report Agent (Production Mode)")

        llm = get_llm()

        if llm is None:
            logger.error("LLM initialization failed")
            state["analysis"] = "LLM initialization failed"
            return state

        # Multi-test input
        lab_results = state.get("lab_results", [])

        if not lab_results:
            logger.error("No lab results found")
            state["analysis"] = "No lab data available"
            return state

        # Doctor-Focused Prompt
        prompt = ChatPromptTemplate.from_template(
            """
You are an experienced clinical assistant helping doctors interpret lab reports.

You will receive MULTIPLE medical test results from different types of reports (blood, urine, hormonal, etc.).
Data may vary in format, naming, and completeness.

STRICT RULES:
- No hallucination
- Do NOT assume missing values
- Do NOT assume causes or diagnoses not directly supported by given values
- Do NOT use terms like "likely", "suggests", "may indicate", "possible", "indicates"
- Do NOT provide diagnoses or treatment advice
- Use only observation-based clinical statements
- Always describe findings using neutral terms like "low value observed", "elevated value observed"
- If interpretation is uncertain, state: "Requires clinical correlation"
- Be clinically accurate and conservative
- Keep output SHORT, structured, and easy to scan
- Do NOT explain for patients
- Include ALL tests in output
- Highlight abnormal findings clearly
- Include normal findings briefly (do not expand too much)
- Prioritize abnormal findings over normal ones
- You MUST include a "Normal Findings" section
- Do NOT skip normal values
- Severity must be based ONLY on comparison with reference range
- If reference range is missing or unclear → do NOT assign severity
- If only one abnormal test is present, use "Single abnormal value observed"
- If multiple, use "Multiple abnormal values observed"

ROBUSTNESS RULES (VERY IMPORTANT):
- Test names may vary (e.g., "Hb", "Hemoglobin", "HGB") → treat them as independent entries without guessing equivalence
- Units may differ → do NOT convert or assume
- If a value or range is unclear → report as "Data unclear"
- Do NOT merge or invent tests
- Handle both single-test and multi-test inputs correctly

Your job:
1. Highlight critical findings (if any)
2. Classify severity for each abnormal test:
   - Mild → slightly outside range
   - Moderate → clearly outside range
   - Severe → significantly outside range
3. List abnormal findings with severity (observation only)
4. Group by system (if clearly identifiable from test name; otherwise skip grouping)
5. Detect patterns across tests (ONLY if clearly supported by multiple abnormal values)
6. Provide a short clinical summary (observation-based only)
7. Suggest next focus (tests or evaluation only, no treatment)

Input:
{lab_results}

Output Format:

=== CLINICAL SUMMARY ===

Critical Findings:
- List only if clearly critical
- Otherwise write: None

Abnormal Findings:
- Test → value (Status, Severity) → observation only (e.g., "Low value observed", "Elevated value observed")

Normal Findings:
- List ALL normal tests briefly (do not skip)
- If many, summarize as: "Other parameters within normal limits"

Patterns Detected:
- Only list if clearly supported by multiple abnormal values
- Otherwise write: "No clear pattern identified"

Systems Involved:
- List only if clearly identifiable
- Otherwise write: "Not clearly defined"

Overall Impression:
- Observation-based summary only
- Do NOT include diagnosis or assumptions
- If multiple abnormalities: "Multiple abnormal values observed → Requires clinical correlation"

Recommended Focus:
- Only further evaluation or tests
- Do NOT include treatment, medication, or supplementation
- If unclear: "Further clinical evaluation recommended"

ONLY return this format. No JSON. No extra explanation.
"""
        )

        chain = prompt | llm | StrOutputParser()

        result = chain.invoke({
            "lab_results": lab_results
        })

        # Safe fallback
        if not result or result.strip() == "":
            result = "Analysis could not be generated."

        state["analysis"] = result.strip()

        logger.info("Report Agent Completed")
        return state

    except Exception as e:
        logger.error(f"Report Agent Error: {str(e)}")
        state["analysis"] = "Analysis failed"
        return state


# TESTING BLOCK 
if __name__ == "__main__":

    from processing.pdf_reader import read_pdf
    from processing.report_parser import parse_medical_report
    from processing.llm_extractor import llm_extract_medical_data

    print("\n=== Running Report Agent Test ===\n")

    file_path = "sample_data/Glucose_report.pdf"

    try:
        # Read PDF
        extracted_text = read_pdf(file_path)

        print("\n=== EXTRACTED TEXT (Preview) ===\n")
        print(extracted_text[:500])

        # Try Regex Parser
        parsed_results = parse_medical_report(extracted_text)

        # Smart Fallback
        lab_results = parsed_results.get("lab_results", [])

        # Detect corrupted test names (numbers inside test name)
        bad_parsing = any(
            any(char.isdigit() for char in item.get("test", ""))
            for item in lab_results
        )

        # Detect missing important tests (like TSH in your case)
        missing_key_tests = not any(
            "tsh" in item.get("test", "").lower()
            for item in lab_results
        )

        # If parser fails OR data looks wrong → switch to LLM
        if not lab_results or bad_parsing or missing_key_tests:
            logger.warning("Parser unreliable, Switching to LLM Extractor")

            parsed_results = llm_extract_medical_data(extracted_text)

        print("\n=== FINAL PARSED LAB RESULTS ===\n")
        print(parsed_results)

        # Run Report Agent
        result = report_agent(parsed_results)

        print("\n=== FINAL ANALYSIS OUTPUT ===\n")
        print(result.get("analysis"))

    except Exception as e:
        print("\nERROR OCCURRED:\n", str(e))