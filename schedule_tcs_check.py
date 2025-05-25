#!/usr/bin/env python3
# File: /home/yashraj/Desktop/test/schedule_tcs_check.py

import os
import time
import subprocess
import logging
import logging.handlers
from datetime import datetime, time as dt_time
from pathlib import Path

# Configuration
SCRIPT_DIR = Path(__file__).parent.absolute()
VENV_PYTHON = SCRIPT_DIR / "venv" / "bin" / "python"
TCS_SCRIPT = SCRIPT_DIR / "main.py"
LOG_DIR = SCRIPT_DIR / "logs"
LOG_FILE = LOG_DIR / "scheduler.log"

# Create logs directory if it doesn't exist
LOG_DIR.mkdir(exist_ok=True, parents=True)

# Configure logging
logger = logging.getLogger('TCSScheduler')
logger.setLevel(logging.INFO)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# File handler with rotation
file_handler = logging.handlers.RotatingFileHandler(
    LOG_FILE, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8'
)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Scheduled times (24-hour format)
RUN_TIMES = [
    dt_time(12, 0),  # 12:00 PM
    dt_time(20, 0),  # 8:00 PM
]

def run_tcs_check():
    """Run the TCS check script using the virtual environment's Python."""
    try:
        log(f"Starting TCS check at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", level=logging.INFO)
        
        # Run the script using the virtual environment's Python
        result = subprocess.run(
            [str(VENV_PYTHON), str(TCS_SCRIPT)],
            cwd=SCRIPT_DIR,
            capture_output=True,
            text=True
        )
        
        # Log the output
        if result.stdout:
            log(f"TCS check output: {result.stdout}", level=logging.DEBUG)
        if result.stderr:
            log(f"TCS check errors: {result.stderr}", level=logging.ERROR)
            
        log(f"TCS check completed with return code: {result.returncode}", 
            level=logging.INFO if result.returncode == 0 else logging.ERROR)
        return result.returncode == 0
        
    except Exception as e:
        log(f"Error running TCS check: {str(e)}", level=logging.ERROR)
        return False

def log(message, level=logging.INFO):
    """Log messages with specified level."""
    logger.log(level, message)

def get_next_run():
    """Calculate the next run time."""
    now = datetime.now().time()
    today = datetime.now().date()
    
    # Find the next run time today
    for run_time in sorted(RUN_TIMES):
        if run_time > now:
            return datetime.combine(today, run_time)
    
    # If all run times have passed today, use first run time tomorrow
    return datetime.combine(today.replace(day=today.day + 1), RUN_TIMES[0])

def main():
    log("TCS Check Scheduler started", level=logging.INFO)
    log(f"Virtual environment Python: {VENV_PYTHON}", level=logging.DEBUG)
    log(f"TCS Script: {TCS_SCRIPT}", level=logging.DEBUG)
    
    # Verify paths
    if not VENV_PYTHON.exists():
        log(f"Error: Virtual environment Python not found at {VENV_PYTHON}", level=logging.CRITICAL)
        return
    
    if not TCS_SCRIPT.exists():
        log(f"Error: TCS script not found at {TCS_SCRIPT}", level=logging.CRITICAL)
        return
    
    # Run immediately on start if it's time
    now = datetime.now().time()
    if any(run_time <= now for run_time in RUN_TIMES):
        log("Running initial check...", level=logging.INFO)
        run_tcs_check()
    
    # Main scheduling loop
    while True:
        next_run = get_next_run()
        wait_seconds = (next_run - datetime.now()).total_seconds()
        
        log(f"Next run scheduled for: {next_run}", level=logging.INFO)
        log(f"Sleeping for {wait_seconds/60:.1f} minutes...", level=logging.DEBUG)
        
        try:
            time.sleep(wait_seconds)
            run_tcs_check()
        except KeyboardInterrupt:
            log("Scheduler stopped by user", level=logging.INFO)
            break
        except Exception as e:
            log(f"Error in scheduler: {str(e)}", level=logging.ERROR)
            # Wait a bit before retrying in case of errors
            time.sleep(60)

if __name__ == "__main__":
    main()
