from agents.validation_agent import ValidationAgent

file_path = "sample_data/Medical_report.pdf"

user_name = "Shankar"

# Try different cases:
reg_no = "REG12345"
lab_no = ""   # leave empty to test fallback

agent = ValidationAgent()

result = agent.validate(file_path, user_name, reg_no, lab_no)

print("\n=== VALIDATION RESULT ===")
print(f"Is Valid: {result['is_valid']}")
print(f"Errors: {result['errors']}")
print(f"File Hash: {result['file_hash']}")
print(f"Is Duplicate: {result['is_duplicate']}")
print(f"Identifier Used: {result['identifier_used']}")

if result["is_duplicate"]:
    print("\nRetrieved Existing Result:")
    print(result["existing_result"])
else:
    print("\nProceed to processing pipeline")