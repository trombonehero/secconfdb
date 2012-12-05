import logging
from logging import FileHandler as Handler   # logging.handlers in Python 2.7

import os
import sys

abspath = os.path.dirname(__file__)
sys.path.append(abspath)
os.chdir(abspath)

log_handler = Handler('secconfdb.log')
log_handler.setLevel(logging.INFO)

from secconfdb import app as application
application.logger.addHandler(log_handler)
