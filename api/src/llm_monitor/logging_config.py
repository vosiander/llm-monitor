"""Logging configuration using loguru as the default logging mechanism.

This module provides a centralized logging setup that intercepts all standard
library logging (including uvicorn, FastAPI, etc.) and routes it through loguru
for consistent formatting and handling.
"""
import logging
import sys
import os
from loguru import logger


class InterceptHandler(logging.Handler):
    """
    Intercept standard library logging and route to loguru.
    
    This handler captures all logs from the standard logging module
    (used by uvicorn, FastAPI, and other libraries) and redirects them
    to loguru for consistent formatting.
    """
    
    def emit(self, record: logging.LogRecord) -> None:
        """
        Process a log record and route it to loguru.
        
        Args:
            record: The log record to process
        """
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        
        # Find caller from where the logging call originated
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        
        # Log the message through loguru
        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging(log_level: str = None) -> None:
    """
    Setup loguru as the default logging mechanism for the entire application.
    
    This function:
    - Removes default loguru handlers
    - Adds a custom formatted handler
    - Intercepts all standard library logging
    - Captures logs from uvicorn, FastAPI, and other libraries
    
    Args:
        log_level: Log level to use (DEBUG, INFO, WARNING, ERROR, CRITICAL).
                  If None, reads from LOG_LEVEL environment variable or defaults to INFO.
    """
    # Determine log level
    if log_level is None:
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Remove default loguru handler
    logger.remove()
    
    # Add custom handler with consistent format
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=log_level,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )
    
    # Intercept standard library logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    # Intercept specific loggers used by FastAPI/uvicorn
    for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"]:
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = [InterceptHandler()]
        logging_logger.propagate = False
    
    logger.info(f"Logging initialized with level: {log_level}")


def setup_file_logging(
    log_file: str = "logs/app.log",
    rotation: str = "500 MB",
    retention: str = "10 days",
    compression: str = "zip"
) -> None:
    """
    Add file-based logging in addition to stderr output.
    
    Args:
        log_file: Path to the log file
        rotation: When to rotate the log file (e.g., "500 MB", "1 day")
        retention: How long to keep old log files
        compression: Compression format for rotated logs
    """
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation=rotation,
        retention=retention,
        compression=compression,
        backtrace=True,
        diagnose=True,
    )
    logger.info(f"File logging enabled: {log_file}")
