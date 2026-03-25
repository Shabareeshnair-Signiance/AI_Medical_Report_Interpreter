import re

def extract_test_lines(text: str):
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    grouped_blocks = []
    current_block = []

    for line in lines:

        has_number = bool(re.search(r'\d', line))
        has_unit = bool(re.search(r'(mg|dl|g|mmol|%)', line.lower()))

        # Start new block if line has number or looks like value/unit
        if has_number or has_unit:
            if current_block:
                grouped_blocks.append(" ".join(current_block))
                current_block = []

            current_block.append(line)

        else:
            if current_block:
                current_block.append(line)

    # Add last block
    if current_block:
        grouped_blocks.append(" ".join(current_block))

    # Remove long paragraph blocks (comments)
    filtered_blocks = [
        block for block in grouped_blocks
        if len(block) < 200 and len(block.split()) < 25
    ]

    return "\n".join(filtered_blocks)