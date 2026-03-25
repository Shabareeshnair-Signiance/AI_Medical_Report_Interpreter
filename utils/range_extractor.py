import re

def extract_reference_ranges(text):
    lines = text.split("\n")

    ranges = []

    for line in lines:
        line = line.strip()

        # Match: 0.6 - 1.2
        if re.search(r'\d+\s*[-–]\s*\d+', line):
            ranges.append(line)

        # Match: <100 or >5
        elif re.search(r'[<>]\s*\d+', line):
            ranges.append(line)

    return ranges