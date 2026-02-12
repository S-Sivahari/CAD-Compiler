import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
import sys

sys.path.append(str(Path(__file__).parent.parent))
from core import config


def setup_logger(name: str, log_file: Optional[str] = None, level=logging.INFO):
    
    formatter = logging.Formatter(config.LOG_FORMAT)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False  # Prevent duplicate logs from parent loggers
    
    if logger.handlers:
        return logger
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    if log_file:
        log_path = config.LOGS_DIR / log_file
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_session_log_file():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"session_{timestamp}.log"


main_logger = setup_logger('synthocad', get_session_log_file())
api_logger = setup_logger('synthocad.api', 'api.log')
pipeline_logger = setup_logger('synthocad.pipeline', 'pipeline.log')
