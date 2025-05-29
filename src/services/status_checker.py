import logging
import time
import smtplib
from email.message import EmailMessage
from datetime import datetime
import os

from src.config.settings import GMAIL_EMAIL, GMAIL_APP_PASSWORD
from src.core.screenshot import take_screenshot, cleanup_screenshots

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
        
        msg.set_content(body)
        
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
            cleanup_screenshots()
            return True
            
    except Exception as e:
        logging.error(f"Failed to send email: {str(e)}")
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