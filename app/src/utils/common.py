"""
Common Utility Functions
-----------------

Common utility functions used across multiple modules
"""

from typing import List, Dict, Any, Optional, Set


def generate_location_styles(location_types: List[str]) -> Dict[str, str]:
    """Generate style information for work locations

    Args:
        location_types: List of work location types

    Returns:
        Dict[str, str]: Mapping of work locations and their style information
    """
    colors = ["success", "primary", "warning", "error", "info", "accent", "secondary"]
    location_styles = {}

    for i, loc_type in enumerate(location_types):
        color_index = i % len(colors)
        location_styles[loc_type] = (
            f"bg-{colors[color_index]}/10 text-{colors[color_index]}"
        )

    return location_styles


def generate_location_badges(location_types: List[str]) -> List[Dict[str, str]]:
    """Generate badge information for work locations

    Args:
        location_types: List of work location types

    Returns:
        List[Dict[str, str]]: List of work locations and their badge information
    """
    colors = ["success", "primary", "warning", "error", "info", "accent", "secondary"]
    locations = []

    for i, loc_type in enumerate(location_types):
        color_index = i % len(colors)
        locations.append(
            {
                "name": loc_type,
                "badge": colors[color_index],
            }
        )

    return locations


def has_data_for_day(day_data: Dict[str, List]) -> bool:
    """Check if there is work information for a specific day

    Args:
        day_data: Daily data (dictionary with work locations as keys and user lists as values)

    Returns:
        bool: True if data exists, False otherwise
    """
    return bool(day_data)
