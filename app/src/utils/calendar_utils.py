"""
Calendar Utilities
-----------------

Utility functions for calendar processing
"""

import datetime
import calendar
from collections import defaultdict
from typing import Dict, List, Any, Tuple, DefaultDict

# Calendar settings for Sunday as first day of week (0: Monday start → 6: Sunday start)
calendar.setfirstweekday(6)


def parse_month(month: str) -> Tuple[int, int]:
    """Parse a string in YYYY-MM format into year and month

    Args:
        month: Month in YYYY-MM format

    Returns:
        Tuple[int, int]: Tuple of (year, month)

    Raises:
        ValueError: If month format is invalid
    """
    try:
        year, month_num = map(int, month.split("-"))
        if month_num < 1 or month_num > 12:
            raise ValueError(f"Invalid month number: {month_num}")
        return year, month_num
    except Exception:
        raise ValueError(f"Invalid month format: {month}. Please use YYYY-MM format.")


def get_prev_month_date(year: int, month: int) -> datetime.date:
    """Get the date for the previous month

    Args:
        year: Year
        month: Month

    Returns:
        datetime.date: Date object for the previous month
    """
    if month == 1:
        return datetime.date(year - 1, 12, 1)
    return datetime.date(year, month - 1, 1)


def get_next_month_date(year: int, month: int) -> datetime.date:
    """Get the date for the next month

    Args:
        year: Year
        month: Month

    Returns:
        datetime.date: Date object for the next month
    """
    if month == 12:
        return datetime.date(year + 1, 1, 1)
    return datetime.date(year, month + 1, 1)


def generate_location_data(location_types: List[str]) -> List[Dict[str, str]]:
    """Generate style information for work locations

    Args:
        location_types: List of work location types

    Returns:
        List[Dict[str, str]]: List of work locations and their style information
    """
    colors = ["success", "primary", "warning", "error", "info", "accent", "secondary"]
    locations = []

    for i, loc_type in enumerate(location_types):
        color_index = i % len(colors)
        locations.append(
            {
                "name": loc_type,
                "color": f"text-{colors[color_index]}",
                "key": loc_type,
                "badge": colors[color_index],
            }
        )

    return locations


def create_calendar_weeks(
    cal_data: List[List[int]],
    month: str,
    calendar_dict: DefaultDict[int, Dict[str, int]],
    location_types: List[str],
) -> List[List[Dict]]:
    """Create calendar data organized by weeks

    Args:
        cal_data: Result of calendar.monthcalendar
        month: Month in YYYY-MM format
        calendar_dict: Count of work locations by day
        location_types: List of work location types

    Returns:
        List[List[Dict]]: Calendar data by week
    """
    calendar_weeks = []

    for week in cal_data:
        week_data = []
        for day in week:
            if day == 0:  # 0 is a day outside the month range
                week_data.append(None)
            else:
                day_data = {
                    "day": day,
                    "date": f"{month}-{day:02d}",
                }
                # Add count for each work location type to the data
                for loc_type in location_types:
                    day_data[loc_type] = calendar_dict[day].get(loc_type, 0)
                week_data.append(day_data)
        calendar_weeks.append(week_data)

    return calendar_weeks
