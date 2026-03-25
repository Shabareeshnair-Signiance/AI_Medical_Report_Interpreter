import re

def extract_test_lines(text: str):
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    grouped_blocks = []
    current_block = []

    for line in lines:
        # If line has a number → likely start of a test
        if re.search(r'\d', line):
            # Save previous block
            if current_block:
                grouped_blocks.append(" ".join(current_block))
                current_block = []

            current_block.append(line)

        else:
            # Continue adding related lines (unit, test name)
            if current_block:
                current_block.append(line)

    # Add last block
    if current_block:
        grouped_blocks.append(" ".join(current_block))

    # Remove very long paragraphs (comments)
    filtered_blocks = [
        block for block in grouped_blocks
        if len(block) < 150
    ]

    return "\n".join(filtered_blocks)