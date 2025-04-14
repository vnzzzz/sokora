"""
File Operation Utilities
-----------------

Utility functions related to file operations
"""

import os
from pathlib import Path
import csv
from typing import Dict, List, Optional, Tuple
import logging
from ..utils.date_utils import normalize_date_format, parse_date

# Logger configuration
logger = logging.getLogger(__name__)


def get_csv_file_path() -> Path:
    """Function to locate the CSV_FILE

    Returns:
        Path: Path to the CSV file
    """
    possible_paths = [
        "work_entries.csv",  # Base path
        os.path.join(os.getcwd(), "work_entries.csv"),  # Current directory
        os.path.join(os.getcwd(), "data", "work_entries.csv"),  # data/ directory
        os.path.join(
            os.path.dirname(os.getcwd()), "data", "work_entries.csv"
        ),  # data/ in parent directory
        os.path.join(os.getcwd(), "app", "work_entries.csv"),  # For Docker environment
        os.path.join(
            os.getcwd(), "app", "data", "work_entries.csv"
        ),  # data/ for Docker environment
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return Path(path)

    # Return base path if not found (for new file creation)
    return Path("work_entries.csv")


def import_csv_data(content: str) -> None:
    """Save CSV data to a file

    Args:
        content: Content of the CSV file

    Raises:
        IOError: If file writing fails
    """
    try:
        # Parse the CSV content
        reader = csv.reader(content.splitlines())
        rows = list(reader)

        if not rows:
            raise IOError("CSV content is empty")

        # Get headers
        headers = rows[0]

        # Normalize date format in headers
        if len(headers) > 2:  # Make sure there are date columns
            for i in range(2, len(headers)):
                if parse_date(headers[i]):
                    # If it's a date, normalize to YYYY-MM-DD format
                    headers[i] = normalize_date_format(headers[i])

        # Create new CSV content with normalized headers
        output = []
        output.append(",".join(headers))
        for row in rows[1:]:
            output.append(",".join(row))

        normalized_content = "\n".join(output)

        # Write to file
        with get_csv_file_path().open("w", encoding="utf-8-sig", newline="") as f:
            f.write(normalized_content)
    except Exception as e:
        logger.error(f"Failed to write CSV data: {str(e)}")
        raise IOError(f"Failed to write CSV data: {str(e)}")


def read_csv_file() -> Tuple[List[str], List[List[str]]]:
    """Read headers and row data from a CSV file

    Returns:
        Tuple[List[str], List[List[str]]]: (List of headers, List of row data)

    Raises:
        IOError: If file reading fails
    """
    csv_path = get_csv_file_path()
    headers = []
    rows = []

    if not csv_path.exists():
        return headers, rows

    try:
        with csv_path.open("r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            headers = next(
                reader, []
            )  # Read header row, return empty list if file is empty
            rows = list(reader)
    except Exception as e:
        logger.error(f"Failed to read CSV data: {str(e)}")
        raise IOError(f"Failed to read CSV data: {str(e)}")

    return headers, rows


def write_csv_file(headers: List[str], rows: List[List[str]]) -> None:
    """Write headers and row data to a CSV file

    Args:
        headers: List of header rows
        rows: List of data rows

    Raises:
        IOError: If file writing fails
    """
    csv_path = get_csv_file_path()

    try:
        with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)
    except Exception as e:
        logger.error(f"Failed to write CSV data: {str(e)}")
        raise IOError(f"Failed to write CSV data: {str(e)}")
