"""
Bethel Trading Technologies
Logging System
"""

import logging
import os


LOG_FOLDER = "logs"


if not os.path.exists(LOG_FOLDER):
    os.makedirs(LOG_FOLDER)


logging.basicConfig(
    filename="logs/bethel_system.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


def get_logger(name):

    logger = logging.getLogger(name)

    return logger