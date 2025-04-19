"""
Application Configuration
========================

Load and manage application configuration from environment variables.
"""

import os
import logging

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
