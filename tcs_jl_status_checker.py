import logging
import time
from gmail_otp_retriever import get_otp_from_gmail
from gemini_captcha_solver import solve_captcha
import smtplib
from email.message import EmailMessage
from datetime import datetime
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Email configuration from environment variables
GMAIL_EMAIL = os.getenv('GMAIL_EMAIL')
GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD')

# Configure logging - use the root logger to prevent duplicates
logger = logging.getLogger()
logger.info("Starting JL status check after successful login.")

def send_email(subject, body, image_path=None):
    try:
        if not all([GMAIL_EMAIL, GMAIL_APP_PASSWORD]):
            logging.error("Email configuration is incomplete. Please check your .env file.")
            return False
            
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = GMAIL_EMAIL
        msg['To'] = GMAIL_EMAIL
        
        # Set the email body
        msg.set_content(body)
        
        # Add image attachment if provided
        if image_path and os.path.exists(image_path):
            with open(image_path, 'rb') as f:
                file_data = f.read()
                file_name = os.path.basename(image_path)
                msg.add_attachment(
                    file_data,
                    maintype='image',
                    subtype='png',
                    filename=file_name
                )
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(GMAIL_EMAIL, GMAIL_APP_PASSWORD)
            smtp.send_message(msg)
            logging.info("Notification email sent successfully.")
            # Clean up screenshots after successful email
            cleanup_screenshots()
            return True
            
    except Exception as e:
        logging.error(f"Failed to send email: {str(e)}")
        return False

def ensure_screenshots_dir():
    path = Path("screenshots")
    path.mkdir(exist_ok=True)
    return path

def take_screenshot(page, name):
    path = ensure_screenshots_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = path / f"{name}_{timestamp}.png"
    page.screenshot(path=str(file_path), full_page=True)
    logging.info(f"Screenshot saved: {file_path}")
    return str(file_path)

def cleanup_screenshots():
    """Remove all files from the screenshots directory"""
    try:
        screenshots_dir = ensure_screenshots_dir()
        if os.path.exists(screenshots_dir):
            for file in os.listdir(screenshots_dir):
                file_path = os.path.join(screenshots_dir, file)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    logging.error(f"Failed to delete {file_path}: {str(e)}")
            logging.info("Cleaned up all screenshots")
            return True
    except Exception as e:
        logging.error(f"Error during screenshot cleanup: {str(e)}")
        return False

def tcs_jl_status_checker(page):
    try:
        # Navigate to "Track My Application"
        page.click('a:has-text("Track My Application")')
        page.wait_for_timeout(3000)

        # Check top row of table
        rows = page.locator('table tr')
        first_row = rows.nth(1)
        first_row_text = first_row.inner_text()
        screenshot_path = take_screenshot(page, "application_status")
      
        today = datetime.now().strftime("%d/%m/%Y")
        status = 'ILP Scheduled' if 'ILP Scheduled' in first_row_text or today in first_row_text else 'No JL'

        if status == 'ILP Scheduled':
            send_email(" TCS JL Received!", 
                     f"Congratulations! You have received your JL from TCS.\n\nStatus Row:\n{first_row_text}",
                     screenshot_path)
        else:
            send_email("NO JL Received by TCS", 
                     f"NO JL yet by TCS.\n\nStatus Row:\n{first_row_text}",
                     screenshot_path)
        
        return True, status

    except Exception as e:
        logging.error(f"Error during JL status check: {str(e)}")
        take_screenshot(page, "jl_status_error")
        return False, str(e)