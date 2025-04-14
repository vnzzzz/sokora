import datetime
from fastapi import Request
from typing import Optional


def format_date(date: datetime.date) -> str:
    """Format date to YYYY-MM-DD

    Args:
        date: Date object

    Returns:
        str: String in YYYY-MM-DD format
    """
    return date.strftime("%Y-%m-%d")


def get_today_formatted() -> str:
    """Get today's date in YYYY-MM-DD format

    Returns:
        str: Today's date (YYYY-MM-DD format)
    """
    return format_date(datetime.date.today())


def get_current_month_formatted() -> str:
    """Get current month in YYYY-MM format

    Returns:
        str: Current month (YYYY-MM format)
    """
    today = datetime.date.today()
    return f"{today.year}-{today.month:02d}"


def get_last_viewed_date(request: Request) -> str:
    """Get the last viewed date

    Extracts the last viewed date from the request's Referer header.
    If there's a date after '/api/day/' path, returns that date,
    otherwise returns today's date.

    Args:
        request: FastAPI request object

    Returns:
        str: Last viewed date (YYYY-MM-DD format)
    """
    referer = request.headers.get("referer", "")
    if "/api/day/" in referer:
        return referer.split("/api/day/")[-1].split("?")[0]
    return get_today_formatted()


def parse_date(date_str: str) -> Optional[datetime.date]:
    """Convert a string in YYYY-MM-DD format to a date object

    Args:
        date_str: Date string in YYYY-MM-DD format

    Returns:
        Optional[datetime.date]: Converted date object, or None if conversion fails
    """
    try:
        year, month, day = map(int, date_str.split("-"))
        return datetime.date(year, month, day)
    except (ValueError, IndexError):
        return None
