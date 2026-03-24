from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from llm.llm_provider import get_llm
from logger_config import logger

# Guardrails for random chats
def classify_query_intent(query: str):
    llm = get_llm()

    if llm is None:
        return "unknown"

    prompt = f"""
Classify the user query into one of these categories:

1. medical (related to health, lab report, symptoms, analysis)
2. non-medical (general knowledge, geography, jokes, etc.)

Only return ONE word: medical OR non-medical

Query: {query}
"""

    try:
        response = llm.invoke(prompt)
        result = response.content.strip().lower()

        if result == "medical":
            return "medical"
        elif result == "non-medical":
            return "non-medical"
        else:
            return "unknown"

    except:
        return "unknown"


# Classifier to know the query
def is_query_related_to_report(query: str, analysis: str) -> bool:
    llm = get_llm()

    if llm is None:
        return False

    prompt = f"""
You are checking whether a doctor's question is related to a medical report.

Report Analysis:
{analysis}

Question:
{query}

Answer ONLY "yes" or "no"

Is the question related to the report?
"""

    try:
        response = llm.invoke(prompt)
        result = response.content.strip().lower()

        return result == "yes"

    except:
        return False


# Report agent 
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
            state["lab_results"] = []
            return state

        # Doctor-Focused Prompt
        prompt = ChatPromptTemplate.from_template(
            """
You are an experienced clinical assistant helping doctors interpret lab reports.

You will receive MULTIPLE medical test results from different types of reports (blood, urine, hormonal, etc.).
Data may vary in format, naming, and completeness.

CORE RULES:
- No hallucination
- Do NOT assume missing values or causes
- Do NOT provide diagnosis or treatment
- Use only observation-based statements (e.g., "low value observed", "elevated value observed")
- If unclear → "Requires clinical correlation"
- Be clinically conservative (do NOT overstate severity)
- Keep output SHORT, structured, and easy to scan
- Include ALL tests
- Prioritize abnormal findings over normal ones
- Include normal findings ONLY if present
- If no normal values → "No normal parameters available"
- If reference range is missing → do NOT assign severity
- Do NOT merge, convert, or assume test equivalence
- If data unclear → "Data unclear"

CRITICAL DETECTION (VERY IMPORTANT):
- Most abnormal values are NOT critical
- A value is "Critical" ONLY if it is EXTREMELY outside the reference range

Use RELATIVE deviation from reference range:
- Within range → NOT critical
- Slight/Moderate deviation (<50% outside range) → NOT critical
- Extreme deviation (>50% outside range) → CRITICAL

Additional rules:
- Borderline values are NEVER critical
- Slightly high/low values are NEVER critical
- If unsure → DO NOT mark as critical
- Default assumption: NO critical findings

TASK:
1. Highlight critical findings ONLY if deviation is extreme (>50% outside range)
2. Classify severity for each abnormal test:
   - Mild → slightly outside range
   - Moderate → clearly outside range
   - Severe → significantly outside range
3. List abnormal findings with severity (observation only)
4. Group by system (only if clearly identifiable)
5. Detect patterns ONLY if supported by multiple abnormal values
6. Provide short clinical summary (observation only)
7. Suggest next focus (tests/evaluation only)

SPECIAL RULE:
- If force_no_normal is True → write: "No normal parameters available"

Input:
{lab_results}

Output Format:

Critical Findings:
- Include ONLY tests where the value is EXTREMELY outside the reference range (>50% deviation from nearest boundary)
- Do NOT include mild, moderate, or borderline abnormalities
- Do NOT include values close to reference limits
- If no test meets strict critical criteria --> write: None

Abnormal Findings:
- <Test Name>: <Value> (<Status>) – <short simple observation>

Normal Findings:
- List normal tests ONLY if present
- If none -> "No normal parameters available"
- Do NOT assume existence of other tests

Patterns Detected:
- Only list if clearly supported by multiple abnormal values
- Otherwise write: "No clear pattern identified"

Systems Involved:
- List only if clearly identifiable
- Otherwise write: "Not clearly defined"

Overall Impression:
- Observation-based summary only
- Do NOT include diagnosis or assumptions
- If multiple abnormalities: "Multiple abnormal values observed -> Requires clinical correlation"

Recommended Focus:
- Only further evaluation or tests
- Do NOT include treatment, medication, or supplementation
- If unclear: "Further clinical evaluation recommended"

ONLY return this format. No JSON. No extra explanation.
"""
        )

        chain = prompt | llm | StrOutputParser()

        lab_results = state.get("lab_results", [])

        # Guard for checking normal values
        normal_tests = [
            item for item in lab_results
            if item.get("status", "").lower() == "normal"
        ]

        if len(lab_results) <= 1 and not normal_tests:
            state["force_no_normal"] = True
        else:
            state["force_no_normal"] = False

        result = chain.invoke({
            "lab_results": lab_results,
            "force_no_normal": state.get("force_no_normal", False)
        })

        # Safe fallback
        if not result or result.strip() == "":
            result = "Analysis could not be generated."

        state["analysis"] = result.strip()
        state["lab_results"] = lab_results

        logger.info("Report Agent Completed")
        return state

    except Exception as e:
        logger.error(f"Report Agent Error: {str(e)}")
        state["analysis"] = "Analysis failed"
        return state
    

def is_report_related(query: str) -> bool:
    keywords = [
        "report", "summary", "analysis", "result",
        "finding", "value", "test", "level",
        "normal", "abnormal", "explain"
    ]

    query = query.lower()
    return any(word in query for word in keywords)

# New Chat Function

def report_chat_agent(analysis: str, user_question: str):
    """
    Chatbox function for doctors to ask questions about report

    Inputs:
    - analysis -> output from report_agent
    - user_question -> question from UI chatbox

    Output:
    - AI response (short, doctor-focused)
    """

    try:
        logger.info("Running Report Chat Agent")

        # Guardrail (LLM-based)
        intent = classify_query_intent(user_question)

        logger.info(f"Query: {user_question} | Intent: {intent}")

        logger.info(f"Query: {user_question} | Intent: {intent}")

        # Allow if medical OR report-related
        if intent != "medical" and not is_report_related(user_question):
            return "I can assist only with medical report-related questions. Please ask about the report."
        #if intent != "medical":    
         #   return "I can assist only with medical report-related questions. Please ask about the report."
        
        if not is_query_related_to_report(user_question, analysis):
            return "Please ask questions related to this report only."
        
        llm = get_llm()

        if llm is None:
            return "LLM not available"
        
        # chat prompt using existing analysis
        chat_prompt = ChatPromptTemplate.from_template(
            """
You are a clinical assistant helping doctors understand a lab report.

STRICT RULES:
- Answer ONLY based on given analysis
- Answer STRICTLY from analysis text
- Do NOT assume existence of tests not mentioned
- If analysis mentions only one test -- do NOT refer to other tests
- Do NOT say "other tests are normal" unless explicitly written
- Use very simple language
- Explain in short and clear sentences
- Do NOT add new assumptions
- Do NOT give diagnosis or treatment
- Keep answer SHORT and CLEAR
- If unclear -- say "Requires Clinical correlation"

Report Analysis:
{analysis}

Doctor Question:
{question}

Answer:
"""
        )

        chain = chat_prompt | llm | StrOutputParser()

        response = chain.invoke({
            "analysis": analysis,
            "question": user_question
        })

        if not response or response.strip() == "":
            return "No response generated"
        
        return response.strip()
    
    except Exception as e:
        logger.error(f"Chat Agent Error: {str(e)}")
        return "Chat failed"


# TESTING BLOCK 
# if __name__ == "__main__":

#     from processing.pdf_reader import read_pdf
#     from processing.report_parser import parse_medical_report
#     from processing.llm_extractor import llm_extract_medical_data

#     print("\n=== Running Report Agent Test ===\n")

#     file_path = "sample_data/Glucose_report.pdf"

#     try:
#         # Read PDF
#         extracted_text = read_pdf(file_path)

#         print("\n=== EXTRACTED TEXT (Preview) ===\n")
#         print(extracted_text[:500])

#         # Try Regex Parser
#         parsed_results = parse_medical_report(extracted_text)

#         # Smart Fallback
#         lab_results = parsed_results.get("lab_results", [])

#         # Detect corrupted test names (numbers inside test name)
#         bad_parsing = any(
#             any(char.isdigit() for char in item.get("test", ""))
#             for item in lab_results
#         )

#         # Detect missing important tests (like TSH in your case)
#         missing_key_tests = not any(
#             "tsh" in item.get("test", "").lower()
#             for item in lab_results
#         )

#         # If parser fails OR data looks wrong → switch to LLM
#         if not lab_results or bad_parsing or missing_key_tests:
#             logger.warning("Parser unreliable, Switching to LLM Extractor")

#             parsed_results = llm_extract_medical_data(extracted_text)

#         print("\n=== FINAL PARSED LAB RESULTS ===\n")
#         print(parsed_results)

#         # Run Report Agent
#         result = report_agent(parsed_results)

#         print("\n=== FINAL ANALYSIS OUTPUT ===\n")
#         print(result.get("analysis"))

#         # chatbox testing
#         question = "Is my report okay?"

#         chat_response = report_chat_agent(result.get("analysis"), question)

#         print("\n=== Chat Response ===\n")
#         print(chat_response)

#     except Exception as e:
#         print("\nERROR OCCURRED:\n", str(e))