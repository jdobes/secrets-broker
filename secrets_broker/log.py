import os
import logging

logging.basicConfig(format="%(asctime)s:%(levelname)s:%(name)s:%(message)s")

LOG_LEVEL = os.getenv('LOG_LEVEL', "INFO")


def get_logger(name):
    logger = logging.getLogger(__name__)
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    return logger
