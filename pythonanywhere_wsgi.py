# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# PythonAnywhere WSGI configuration file for MediCompare
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# Replace <YOUR_PYTHONANYWHERE_USERNAME> with your actual username

import sys
import os

# Set project home directory
project_home = '/home/<YOUR_PYTHONANYWHERE_USERNAME>/MediCompare'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Import the Flask application instance
from app import app as application
