import csv
from pathlib import Path
from collections import defaultdict
import calendar
import datetime
import os
import logging
from typing import Dict, List, Optional, Any, DefaultDict, Tuple, Set

from ..utils.file_utils import get_csv_file_path, read_csv_file, write_csv_file
from ..utils.calendar_utils import (
    parse_month,
    get_prev_month_date,
    get_next_month_date,
    generate_location_data,
    create_calendar_weeks,
)
from ..utils.common import get_default_location_types

# Logger configuration
logger = logging.getLogger(__name__)

# Calendar settings for Sunday as first day of week (0: Monday start → 6: Sunday start)
calendar.setfirstweekday(6)


def get_location_types() -> List[str]:
    """Function to dynamically get work location types from CSV

    Returns:
        List[str]: List of work location types
    """
    data = read_all_entries()
    locations: Set[str] = set()

    # Extract work locations from all user data
    for user_data in data.values():
        for location in user_data.values():
            if location.strip():  # If not blank
                locations.add(location)

    # Handle case when there are no default work location types
    if not locations:
        return get_default_location_types()

    return sorted(list(locations))


def import_csv_data(content: str) -> None:
    """Save CSV data to a file

    Args:
        content: Content of the CSV file

    Raises:
        IOError: If file writing fails
    """
    from ..utils.file_utils import import_csv_data as file_import_csv_data

    try:
        file_import_csv_data(content)
    except IOError as e:
        logger.error(f"Failed to import CSV data: {str(e)}")
        raise


def read_all_entries() -> Dict[str, Dict[str, str]]:
    """Read all entries from CSV file

    Returns:
        Dict[str, Dict[str, str]]: Data in {user_id: {date: location}} format
    """
    headers, rows = read_csv_file()
    data: Dict[str, Dict[str, str]] = {}

    if not headers:
        return data

    dates = headers[2:]  # First column is user_name, second is user_id

    for row in rows:
        if len(row) < 2:  # At minimum, user_name and user_id are required
            continue

        user_id = row[1]
        user_data: Dict[str, str] = {}

        for i, location in enumerate(row[2:], 2):
            if (
                i < len(headers) and location.strip()
            ):  # Only register if not blank and index is valid
                date = headers[i]
                user_data[date] = location

        data[user_id] = user_data

    return data


def get_entries_by_date() -> DefaultDict[str, Dict[str, str]]:
    """Get entries organized by date

    Returns:
        DefaultDict[str, Dict[str, str]]: Data in {date: {user_id: location}} format
    """
    data = read_all_entries()
    date_entries: DefaultDict[str, Dict[str, str]] = defaultdict(dict)

    # Convert user-based data to date-based data
    for user_id, user_data in data.items():
        for date, location in user_data.items():
            date_entries[date][user_id] = location

    return date_entries


def get_all_users() -> List[Tuple[str, str]]:
    """Get all user names and IDs from CSV file

    Returns:
        List[Tuple[str, str]]: List of (user_name, user_id) tuples
    """
    headers, rows = read_csv_file()
    users = []

    for row in rows:
        if len(row) >= 2 and row[0].strip() and row[1].strip():
            users.append((row[0], row[1]))  # Tuple of (user_name, user_id)

    return sorted(users, key=lambda x: x[0])  # Sort by user_name


def get_user_name_by_id(user_id: str) -> str:
    """Get username from user ID

    Args:
        user_id: User ID

    Returns:
        str: Username (empty string if not found)
    """
    headers, rows = read_csv_file()

    for row in rows:
        if len(row) >= 2 and row[1] == user_id:
            return row[0]

    return ""


def add_user(username: str, user_id: str) -> bool:
    """Add a new user to CSV file

    Args:
        username: Username to add
        user_id: User ID

    Returns:
        bool: Whether the addition was successful
    """
    if not username.strip() or not user_id.strip():
        return False

    try:
        # Read current data
        users = get_all_users()

        # Don't add if username or ID already exists
        for name, id in users:
            if name == username or id == user_id:
                return False

        # Read file and get headers
        headers, rows = read_csv_file()

        if not headers:
            # Create new file if it doesn't exist
            headers = ["user_name", "user_id"]

        # Add new user
        new_row = [username, user_id] + [""] * (len(headers) - 2)
        rows.append(new_row)

        # Write to file
        write_csv_file(headers, rows)

        return True
    except Exception as e:
        logger.error(f"Failed to add user: {str(e)}")
        raise IOError(f"Failed to add user: {str(e)}")


def delete_user(user_id: str) -> bool:
    """Delete user from CSV file

    Args:
        user_id: User ID to delete

    Returns:
        bool: Whether the deletion was successful
    """
    try:
        # Read file
        headers, rows = read_csv_file()

        if not headers:
            return False

        original_row_count = len(rows)
        # Keep rows that don't match user_id
        filtered_rows = [row for row in rows if len(row) < 2 or row[1] != user_id]

        # If no rows are removed (no matching user)
        if len(filtered_rows) == original_row_count:
            return False

        # Write to file
        write_csv_file(headers, filtered_rows)

        return True
    except Exception as e:
        logger.error(f"Failed to delete user: {str(e)}")
        raise IOError(f"Failed to delete user: {str(e)}")


def update_user_entry(user_id: str, date: str, location: str) -> bool:
    """Update work location for a specific date for a user

    Args:
        user_id: User ID
        date: Date in YYYY-MM-DD format
        location: Work location

    Returns:
        bool: Whether the update was successful
    """
    try:
        # Read file
        headers, rows = read_csv_file()

        if not headers:
            return False

        # Check if date exists
        if date not in headers[2:]:
            # If date doesn't exist, insert it in the correct position
            date_headers = headers[2:]

            # Find the correct insertion position
            insert_position = 2  # Default is the first date position

            # If the date is after existing dates, find the correct position
            for i, existing_date in enumerate(date_headers):
                if existing_date > date:
                    # Found insertion position
                    insert_position = i + 2  # Add headers[0] and headers[1]
                    break
                else:
                    # If reached the end, add to the end
                    insert_position = len(headers)

            # Insert new date into headers
            headers.insert(insert_position, date)

            # Insert new column into all rows
            for row in rows:
                # If row is short, extend to the required length
                while len(row) < insert_position:
                    row.append("")
                row.insert(insert_position, "")

        # Get date index
        date_index = headers.index(date)

        # Check if user exists
        user_exists = False
        for row in rows:
            if len(row) >= 2 and row[1] == user_id:
                user_exists = True
                # If row is short, extend
                while len(row) <= date_index:
                    row.append("")
                row[date_index] = location
                break

        # If user doesn't exist, do nothing
        if not user_exists:
            return False

        # Write to file
        write_csv_file(headers, rows)

        return True
    except Exception as e:
        logger.error(f"Failed to update entry: {str(e)}")
        raise IOError(f"Failed to update entry: {str(e)}")


def get_calendar_data(month: str) -> Dict[str, Any]:
    """Generate calendar data for each month

    Args:
        month: Month specified in YYYY-MM format

    Returns:
        Dict: Data needed for calendar display

    Raises:
        ValueError: If invalid month format
    """
    date_entries = get_entries_by_date()
    location_types = get_location_types()
    calendar_dict: DefaultDict[int, Dict[str, int]] = defaultdict(
        lambda: {location_type: 0 for location_type in location_types}
    )

    # Parse month data
    year, month_num = parse_month(month)

    # Calendar data
    cal = calendar.monthcalendar(year, month_num)

    # Summarize entry data
    for date, entries in date_entries.items():
        if date.startswith(month):
            try:
                day = int(date.split("-")[2])
                for _, location in entries.items():
                    if location in location_types:
                        calendar_dict[day][location] += 1
            except (IndexError, ValueError):
                continue  # Skip invalid date format

    # Create calendar data summarized by week
    calendar_weeks = create_calendar_weeks(cal, month, calendar_dict, location_types)

    # Generate work location style information
    locations = generate_location_data(location_types)

    # Calculate previous and next month
    prev_month_date = get_prev_month_date(year, month_num)
    next_month_date = get_next_month_date(year, month_num)

    # Get English month name
    month_name = f"{year}-{month_num:02d}"

    return {
        "weeks": calendar_weeks,
        "prev_month": f"{prev_month_date.year}-{prev_month_date.month:02d}",
        "next_month": f"{next_month_date.year}-{next_month_date.month:02d}",
        "month_name": month_name,
        "locations": locations,
    }


def get_day_data(day: str) -> Dict[str, List[Dict[str, str]]]:
    """Get data for a specified day

    Args:
        day: Date in YYYY-MM-DD format

    Returns:
        Dict[str, List[Dict[str, str]]]: List of users by location (includes user_name and user_id)

    Raises:
        ValueError: If invalid date format
    """
    entries_by_date = get_entries_by_date()
    location_types = get_location_types()
    result: Dict[str, List[Dict[str, str]]] = {
        loc_type: [] for loc_type in location_types
    }

    # Date validation
    parts = day.split("-")
    if len(parts) != 3:
        return result

    # Summarize work locations for each user on the specified day
    for user_id, location in entries_by_date.get(day, {}).items():
        user_name = get_user_name_by_id(user_id)
        user_data = {"user_id": user_id, "user_name": user_name}

        # Accept all work locations
        if location in result:
            result[location].append(user_data)
        # If location type exists in CSV but not in dictionary, add it
        elif location.strip():
            result[location] = [user_data]

    return result


def get_user_data(user_id: str) -> List[Dict[str, str]]:
    """Get data for a specified user

    Args:
        user_id: User ID

    Returns:
        List[Dict[str, str]]: List of user entries
    """
    data = read_all_entries()
    entries = []

    if user_id in data:
        user_data = data[user_id]
        for date, location in user_data.items():
            entries.append({"date": date, "location": location})

    # Sort by date
    entries.sort(key=lambda x: x["date"])
    return entries
