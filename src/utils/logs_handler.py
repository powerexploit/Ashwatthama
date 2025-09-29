import logging
import os
import socket
import sys
from logging import handlers

scriptDirectory = os.path.dirname(os.path.abspath(__file__))
scriptName = os.path.basename(__file__)


def createLogger(loggerName, remoteLogging=False, logLevel="INFO"):

    logsDirectory = os.path.join(scriptDirectory, "logs")
    if not os.path.exists(logsDirectory):
        os.makedirs(logsDirectory)
    hostname = socket.gethostname()

    logger = logging.getLogger(loggerName)
    
    numericLevel = getattr(logging, logLevel.upper(), logging.INFO)
    logger.setLevel(numericLevel)
    
    logger.handlers.clear()
    
    log_template = "%(asctime)s %(module)s %(levelname)s: %(message)s"
    formatter = logging.Formatter(log_template)
    
    logFileSizeInMb = 10
    countOfBackups = 5
    logFileSizeInBytes = logFileSizeInMb * 1024 * 1024
    logFilename = os.path.join(logsDirectory, '{}~{}'.format(loggerName, hostname)) + '.log'

    fileHandler = handlers.RotatingFileHandler(
        logFilename,
        maxBytes=logFileSizeInBytes,
        backupCount=countOfBackups
    )
    fileHandler.setLevel(logging.DEBUG)
    fileHandler.setFormatter(formatter)
    logger.addHandler(fileHandler)

    consoleHandler = logging.StreamHandler(sys.stdout)
    consoleHandler.setLevel(numericLevel)
    consoleHandler.setFormatter(formatter)
    logger.addHandler(consoleHandler)

    logger.propagate = False

    return logger
