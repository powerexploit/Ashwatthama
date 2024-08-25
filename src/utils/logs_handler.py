import logging
import os
import socket
import sys
from logging import handlers

script_directory = os.path.dirname(os.path.abspath(__file__))
script_name = os.path.basename(__file__)


def create_logger(logger_name, remote_logging=False):
    """
    Creates a logger with rotating file handler.
    Change stdout_handler = True, for adding STDOUT Handler as well.
    :param logger_name: logger name (eg, __name__)
    :param remote_logging: option to enable remote logging (eg, True/False)

    :return: logger
    """

    # Logs directory setup
    logs_directory = os.path.join(script_directory, "logs")
    if not os.path.exists(logs_directory):
        os.makedirs(logs_directory)
    hostname = socket.gethostname()

    # File Handler
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    log_template = "%(asctime)s %(module)s %(levelname)s: %(message)s"
    formatter = logging.Formatter(log_template)
    log_file_size_in_mb = 10
    count_of_backups = 10  # example.log example.log.1 example.log.2
    log_file_size_in_bytes = log_file_size_in_mb * 1024 * 1024
    log_filename = os.path.join(logs_directory, '{}~{}'.format(logger_name, hostname)) + '.log'

    file_handler = handlers.RotatingFileHandler(
        log_filename,
        maxBytes=log_file_size_in_bytes,
        backupCount=count_of_backups
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Stdout handler
    log_template = "%(asctime)s %(module)s %(levelname)s: %(message)s"
    formatter = logging.Formatter(log_template)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)

    return logger
