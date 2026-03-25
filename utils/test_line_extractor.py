import re

def extract_test_lines(text: str):
    lines = text.split("\n")

    filtered = []

    for line in lines:
        line = line.strip()

        # Skip empty
        if not line:
            continue

        # Keep lines with numbers (tests usually have values)
        if re.search(r'\d', line):
            # Remove long paragraph lines (comments)
            if len(line) < 120:
                filtered.append(line)

    return "\n".join(filtered)