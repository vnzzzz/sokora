"""
Sokora - Attendance Management Application
================================

This package contains the source code for the Sokora attendance management application.
A simple attendance tracking tool built with FastAPI.

Features:
- Daily attendance status display
- Monthly calendar view
- User-specific data viewing
- CSV data import/export
"""

import logging
import os
from .services import csv_store

# Application version
APP_VERSION = "1.0.0"

# Set log level (get from environment variable or use INFO as default)
log_level = os.environ.get("SOKORA_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Get root logger
logger = logging.getLogger("sokora")
