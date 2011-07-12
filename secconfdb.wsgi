import os
import sys

abspath = os.path.dirname(__file__)
sys.path.append(abspath)
os.chdir(abspath)

from secconfdb import app as application
