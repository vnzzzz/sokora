"""Application logging configuration."""

import logging

logger = logging.getLogger("sokora")


def configure_logging(log_level: str) -> None:
    """Configure process logging from an explicit application setting."""
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.getLogger().setLevel(level)
    logger.setLevel(level)
