import re

def extract_numbers(range_text):
    nums = re.findall(r'\d+\.?\d*', range_text)
    return [float(n) for n in nums]


def match_range(value, ranges):
    try:
        value = float(value)
    except:
        return "N/A"

    best_match = None

    for r in ranges:
        nums = extract_numbers(r)

        # Ignore unrealistic ranges (very large mismatch)
        if any(n > 1000 for n in nums):
            continue

        # Case: X - Y (MOST RELIABLE → PRIORITY)
        if len(nums) == 2:
            low, high = nums

            # Only accept if range is reasonable for value
            if low <= value <= high:
                return r

            # Store as fallback if close
            if low * 0.1 <= value <= high * 10:
                best_match = r

        # Case: <X
        elif "<" in r and len(nums) == 1:
            if value < nums[0] and nums[0] < 200:  # avoid picking 100 for small values
                best_match = r

        # Case: >X
        elif ">" in r and len(nums) == 1:
            if value > nums[0]:
                best_match = r

    return best_match if best_match else "N/A"