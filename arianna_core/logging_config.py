import logging
import os

LOG_FILE = os.path.join(os.path.dirname(__file__), "log.txt")


def setup_logging() -> None:
    """Configure root logger to log to console and ``LOG_FILE``."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
