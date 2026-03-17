from agents.validation_agent import ValidationAgent

file_path = "sample_data/Glucose_report.pdf"

agent = ValidationAgent()

result = agent.validate(file_path)

print("\n=== VALIDATION RESULT ===")
print(f"Is Valid: {result['is_valid']}")
print(f"Errors: {result['errors']}")
print(f"File Hash: {result['file_hash']}")
print(f"Is Duplicate: {result['is_duplicate']}")
print(f"Identifier Used: {result['identifier_used']}")

print("\n=== EXTRACTED DATA ===")
print(result["extracted_data"])

if result["is_duplicate"]:
    print("\nRetrieved Existing Result:")
    print(result["existing_result"])
else:
    print("\nProceed to processing pipeline")