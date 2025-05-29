import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Constants
DEFAULT_SCRIPT_TIMEOUT = 120
SCREENSHOT_DIR = 'screenshots'
LOG_FILE = 'main.log'
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

# Configuration from environment variables
TCS_EMAIL = os.getenv('TCS_EMAIL')
GMAIL_EMAIL = os.getenv('GMAIL_EMAIL')
GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
HEADLESS = os.getenv('HEADLESS', 'True').strip().lower() == 'true'

# Parse script timeout
script_timeout = os.getenv('SCRIPT_TIMEOUT', str(DEFAULT_SCRIPT_TIMEOUT)).split('#')[0].strip()
try:
    SCRIPT_TIMEOUT = int(script_timeout)
except (ValueError, TypeError):
    logging.warning(f"Invalid SCRIPT_TIMEOUT value: {script_timeout}, defaulting to {DEFAULT_SCRIPT_TIMEOUT}")
    SCRIPT_TIMEOUT = DEFAULT_SCRIPT_TIMEOUT