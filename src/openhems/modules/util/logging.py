"""
Manage logging on OpenHEMS
"""

from datetime import datetime
from pathlib import Path
import logging
from logging import handlers
import sys

# pylint: disable=bad-indentation, invalid-name

def filer(param=None):
	"""
	Function used to get filename on rotating log
	"""
	print("filer(",param,")")
	now = datetime.now()
	return 'openhems.'+now.strftime("%Y-%m-%d")+'.log'

def get_log_file_path(logger: logging.Logger) -> str | None:
    """Return the file path of the first FileHandler attached to the logger, or None."""
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            return handler.baseFilename
    return None

def getLogger(loglevel, logformat, logfile, inDocker=False) -> logging.Logger:
	"""
	Configure a logger for all the Application.
	"""
	if loglevel=="debug":
		level=logging.DEBUG
	elif loglevel in ('warn', 'warning'):
		level=logging.WARNING
	elif loglevel=="error":
		level=logging.ERROR
	elif loglevel in ('critical', 'no'):
		level=logging.CRITICAL
	else: # if loglevel=="info":
		level=logging.INFO
	myHandlers = []
	fileHandler = None
	formatter = logging.Formatter(logformat)
	# Case wrong logfile path : set to empty : no logging file
	logfileparents = Path(logfile).parents
	if len(logfileparents)==0 or not next(iter(logfileparents)).is_dir():
		logfile = "" # No log file
	if not inDocker and logfile!="":
		fileHandler = handlers.TimedRotatingFileHandler(filename=logfile,
			when='D',
			interval=1,
			backupCount=5)
		fileHandler.rotation_filename = filer
		fileHandler.setFormatter(formatter)
		myHandlers.append(fileHandler)
	fileHandler = logging.StreamHandler(sys.stdout)
	fileHandler.setFormatter(formatter)
	myHandlers.append(fileHandler)
	logging.basicConfig(level=level, format=logformat, handlers=myHandlers)
	# self.logger.addHandler(fileHandler)
	# watched_file_handler = logging.handlers.WatchedFileHandler(logfile)
	# self.logger.addHandler(watched_file_handler)
	return logging.getLogger(__name__)
