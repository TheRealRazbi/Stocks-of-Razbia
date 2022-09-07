__all__ = ('setup_logging', )

import sys
from loguru import logger


def setup_logging(level='INFO'):
    logger.configure(handlers=[{"sink": sys.stdout,
                                "format": "<cyan>{time:HH : mm}[<magenta>{time:ss.SSSSSS}</magenta>]</cyan> | <yellow>{level}</yellow> | <green>{message}</green>",
                                "level": level}])
