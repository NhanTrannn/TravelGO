"""
Logging configuration
"""

import logging
import sys
from app.core.config import settings


def setup_logging():
    """Configure logging for the application"""
    
    # Create logger
    logger = logging.getLogger("travel-advisor")
    logger.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # Create console handler with UTF-8 encoding support
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # Create formatter - avoid emojis in Windows console
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(handler)
    
    return logger


# Global logger instance
logger = setup_logging()
