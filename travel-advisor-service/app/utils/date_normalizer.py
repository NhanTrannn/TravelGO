"""
Date Normalizer - Convert various date formats to YYYY-MM-DD
"""

import re
from datetime import datetime, timedelta
from typing import Optional


def normalize_date(date_str: str) -> str:
    """
    Normalize Vietnamese date string to YYYY-MM-DD format

    Supports formats:
    - "20/1/2026", "20-1-2026" → "2026-01-20"
    - "ngày 20 tháng 1 năm 2026" → "2026-01-20"
    - "20 tháng 1" → "2026-01-20" (current year)
    - "mai", "ngày mai" → tomorrow
    - "hôm nay" → today
    - "YYYY-MM-DD" → unchanged

    Args:
        date_str: Date string in various formats

    Returns:
        Normalized date string in YYYY-MM-DD format

    Examples:
        >>> normalize_date("20/1/2026")
        "2026-01-20"
        >>> normalize_date("mai")
        "2026-01-18"  # if today is 2026-01-17
    """
    if not date_str:
        return datetime.now().strftime("%Y-%m-%d")

    date_str = date_str.strip().lower()
    today = datetime.now()

    # Already normalized format
    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return date_str

    # Relative dates
    if any(kw in date_str for kw in ["hôm nay", "today"]):
        return today.strftime("%Y-%m-%d")

    if any(kw in date_str for kw in ["mai", "ngày mai", "tomorrow"]):
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")

    if any(kw in date_str for kw in ["ngày kia", "day after tomorrow"]):
        return (today + timedelta(days=2)).strftime("%Y-%m-%d")

    # Vietnamese format: "ngày 20 tháng 1 năm 2026"
    match = re.search(
        r"ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})(?:\s+năm\s+(\d{4}))?", date_str
    )
    if match:
        day = int(match.group(1))
        month = int(match.group(2))
        year = int(match.group(3)) if match.group(3) else today.year
        return f"{year:04d}-{month:02d}-{day:02d}"

    # Format: "20 tháng 1 2026" or "20 tháng 1"
    match = re.search(r"(\d{1,2})\s+tháng\s+(\d{1,2})(?:\s+(\d{4}))?", date_str)
    if match:
        day = int(match.group(1))
        month = int(match.group(2))
        year = int(match.group(3)) if match.group(3) else today.year
        return f"{year:04d}-{month:02d}-{day:02d}"

    # Format: "20/1/2026", "20-1-2026", "20.1.2026"
    match = re.search(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})", date_str)
    if match:
        day = int(match.group(1))
        month = int(match.group(2))
        year = int(match.group(3))
        if year < 100:  # 2-digit year
            year = 2000 + year
        return f"{year:04d}-{month:02d}-{day:02d}"

    # Format: "2026-1-20", "2026/1/20" (year first)
    match = re.search(r"(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})", date_str)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        return f"{year:04d}-{month:02d}-{day:02d}"

    # Default: return today
    return today.strftime("%Y-%m-%d")


if __name__ == "__main__":
    # Test cases
    test_cases = [
        "20/1/2026",
        "20-1-2026",
        "ngày 20 tháng 1 năm 2026",
        "20 tháng 1",
        "mai",
        "hôm nay",
        "2026-01-20",
        "2026/1/20",
    ]

    for test in test_cases:
        print(f"{test:30} → {normalize_date(test)}")
