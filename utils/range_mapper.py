import re

def extract_numbers(range_text):
    nums = re.findall(r'\d+\.?\d*', range_text)
    return [float(n) for n in nums]


def match_range(value, ranges):
    try:
        value = float(value)
    except:
        return "N/A"

    for r in ranges:
        nums = extract_numbers(r)

        # Case: X - Y
        if len(nums) == 2:
            low, high = nums
            if low <= value <= high:
                return r

        # Case: <X
        if "<" in r and len(nums) == 1:
            if value < nums[0]:
                return r

        # Case: >X
        if ">" in r and len(nums) == 1:
            if value > nums[0]:
                return r

    return "N/A"