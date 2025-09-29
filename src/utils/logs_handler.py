import logging
import os
import socket
import sys
from logging import handlers

script_directory = os.path.dirname(os.path.abspath(__file__))
script_name = os.path.basename(__file__)


def create_logger(logger_name, remote_logging=False, log_level="INFO"):
    """
    Creates a logger with rotating file handler.
    :param logger_name: logger name (eg, __name__)
    :param remote_logging: option to enable remote logging (eg, True/False)
    :param log_level: logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    :return: logger
    """

    # Logs directory setup
    logs_directory = os.path.join(script_directory, "logs")
    if not os.path.exists(logs_directory):
        os.makedirs(logs_directory)
    hostname = socket.gethostname()

    # File Handler
    logger = logging.getLogger(logger_name)
    
    # Set log level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(numeric_level)
    
    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()
    
    log_template = "%(asctime)s %(module)s %(levelname)s: %(message)s"
    formatter = logging.Formatter(log_template)
    
    # File handler with rotation
    log_file_size_in_mb = 10
    count_of_backups = 5  # example.log example.log.1 example.log.2
    log_file_size_in_bytes = log_file_size_in_mb * 1024 * 1024
    log_filename = os.path.join(logs_directory, '{}~{}'.format(logger_name, hostname)) + '.log'

    file_handler = handlers.RotatingFileHandler(
        log_filename,
        maxBytes=log_file_size_in_bytes,
        backupCount=count_of_backups
    )
    file_handler.setLevel(logging.DEBUG)  # File handler always captures all levels
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler (only for INFO and above to avoid spam)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Prevent duplicate logs
    logger.propagate = False

    return logger
