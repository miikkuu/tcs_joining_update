"""
Gmail OTP Retriever Module

This module provides functionality to retrieve OTP from Gmail.
"""
import imaplib
import email
import re
import time
import os
import logging
from datetime import datetime, timedelta
from email.header import decode_header
from typing import Optional, Tuple
from src.config.settings import GMAIL_EMAIL, GMAIL_APP_PASSWORD

# Configure logging - use the root logger to prevent duplicates
logger = logging.getLogger()

class GmailOTPHandler:
    def __init__(self, email_address: str, app_password: str):
        """
        Initialize the Gmail OTP handler with email credentials.
        
        Args:
            email_address (str): Gmail address
            app_password (str): Gmail app password
        """
        self.email_address = email_address
        self.app_password = app_password
        self.mail = None
        
    def connect(self) -> bool:
        """Connect to Gmail IMAP server."""
        try:
            self.mail = imaplib.IMAP4_SSL('imap.gmail.com')
            self.mail.login(self.email_address, self.app_password)
            logging.info("Successfully connected to Gmail")
            return True
        except Exception as e:
            logging.error(f"Failed to connect to Gmail: {str(e)}")
            return False
            
    def disconnect(self) -> None:
        """Close the connection to Gmail."""
        if self.mail:
            try:
                self.mail.close()
                self.mail.logout()
                logging.info("Disconnected from Gmail")
            except Exception as e:
                logging.error(f"Error disconnecting from Gmail: {str(e)}")
    
    def get_latest_otp(self, sender: str = None, subject_contains: str = None, 
                       wait_time: int = 5, max_attempts: int = 10) -> Tuple[Optional[str], Optional[str]]:
        """
        Retrieve the latest OTP from Gmail.
        
        Args:
            sender (str, optional): Filter emails by sender
            subject_contains (str, optional): Filter emails by subject
            wait_time (int): Time to wait between checks in seconds
            max_attempts (int): Maximum number of attempts to check for new emails
            
        Returns:
            tuple: (otp_code, email_body) or (None, None) if not found
        """
        if not self.mail:
            if not self.connect():
                return None, None
                
        try:
            logging.info("Selecting inbox...")
            # Select the inbox
            self.mail.select('inbox')
            logging.info("Inbox selected. Searching for unseen emails...")
            
            # Construct the search criteria
            search_criteria = ['UNSEEN']
            if sender:
                search_criteria.append(f'FROM "{sender}"')
            if subject_contains:
                search_criteria.append(f'SUBJECT "{subject_contains}"')

            logging.info(f"Searching for emails with criteria: {' '.join(search_criteria)}")
            status, messages = self.mail.search(None, *search_criteria)
            logging.info(f"Search for emails completed. Status: {status}, Messages: {messages[0]}")
            
            # If no emails found with specific criteria, wait and try again
            attempt = 0
            while (not messages[0] or len(messages[0].split()) == 0) and attempt < max_attempts:
                logging.info(f"No emails found with specific criteria. Waiting {wait_time} seconds... (Attempt {attempt + 1}/{max_attempts})")
                time.sleep(wait_time)
                status, messages = self.mail.search(None, *search_criteria)
                logging.info(f"Re-search for emails completed. Status: {status}, Messages: {messages[0]}")
                attempt += 1
            
            if not messages[0]:
                logging.warning("No emails found matching criteria after maximum attempts")
                return None, None
                
            # Get all email IDs and check from latest to oldest
            email_ids = messages[0].split()
            # Limit to a reasonable number of recent emails to process, e.g., 10
            # This is a safeguard in case the IMAP search returns too many results
            max_emails_to_process = 10
            email_ids_to_process = email_ids[-max_emails_to_process:] # Get the latest N emails
            logging.info(f"Found {len(email_ids)} email IDs matching criteria. Processing latest {len(email_ids_to_process)}.")
            
            for email_id in reversed(email_ids_to_process):  # Check from latest to oldest
                try:
                    logging.info(f"Fetching email ID: {email_id}")
                    # Fetch the email
                    status, msg_data = self.mail.fetch(email_id, '(RFC822)')
                    logging.info(f"Email fetch completed for ID {email_id}. Status: {status}")
                    
                    if status != 'OK':
                        logging.warning(f"Failed to fetch email ID {email_id}. Status: {status}")
                        continue
                        
                    # Parse the email
                    email_message = email.message_from_bytes(msg_data[0][1])
                    logging.info(f"Email ID {email_id} parsed.")
                    
                    # Check sender if filter is provided
                    if sender and sender.lower() not in email_message.get('From', '').lower():
                        continue
                        
                    # Decode subject
                    subject = ''
                    subject_header = email_message.get('Subject', '')
                    if subject_header:
                        for part in decode_header(subject_header):
                            if isinstance(part[0], bytes):
                                subject += part[0].decode(part[1] or 'utf-8', errors='ignore')
                            else:
                                subject += str(part[0])
                    
                    logging.info(f"Checking email with subject: {subject}")
                    
                    # Check subject filter
                    if subject_contains and subject_contains.lower() not in subject.lower():
                        logging.info(f"Skipping email - subject doesn't contain '{subject_contains}'")
                        continue
                    
                    logging.info(f"Processing email with subject: {subject}")
                    
                    # Extract email body
                    email_body = ""
                    if email_message.is_multipart():
                        for part in email_message.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition"))
                            
                            if "attachment" not in content_disposition:
                                if content_type == "text/plain" or content_type == "text/html":
                                    try:
                                        body = part.get_payload(decode=True)
                                        if body:
                                            if isinstance(body, bytes):
                                                body = body.decode('utf-8', errors='ignore')
                                            email_body += body
                                    except Exception as e:
                                        logging.warning(f"Could not decode email part: {str(e)}")
                    else:
                        try:
                            body = email_message.get_payload(decode=True)
                            if body:
                                if isinstance(body, bytes):
                                    body = body.decode('utf-8', errors='ignore')
                                email_body = body
                        except Exception as e:
                            logging.warning(f"Could not decode email: {str(e)}")
                    
                    logging.info(f"Email body preview: {email_body[:200]}...")
                    
                    # Try to find OTP in the email body with specific patterns for TCS
                    otp_patterns = [
                        r'One Time Password \(OTP\) for login:\s*([A-Za-z0-9]{7})',  # TCS specific pattern
                        r'OTP for login:\s*([A-Za-z0-9]{7})',  # Alternative TCS pattern
                        r'OTP:\s*([A-Za-z0-9]{7})',  # Generic OTP pattern
                        r'\b([A-Za-z0-9]{7})\b',  # 7-character alphanumeric code
                        r'\b([A-Z0-9]{6})\b',  # 6-character uppercase alphanumeric
                        r'\b(\d{6})\b',  # 6-digit numeric OTP
                        r'\b(\d{4})\b',  # 4-digit numeric OTP
                    ]
                    
                    for pattern in otp_patterns:
                        matches = re.findall(pattern, email_body, re.IGNORECASE)
                        if matches:
                            for match in matches:
                                # Filter out common false positives
                                if len(match) >= 4 and not any(word in match.lower() for word in ['http', 'www', 'com', 'tcs', 'gmail']):
                                    otp_code = match.strip()
                                    logging.info(f"Found OTP code: {otp_code}")
                                    
                                    # Save OTP to file
                                    try:
                                        with open('otp.txt', 'w') as f:
                                            f.write(otp_code)
                                        logging.info(f"OTP saved to otp.txt: {otp_code}")
                                    except Exception as e:
                                        logging.error(f"Failed to save OTP to file: {str(e)}")
                                        
                                    return otp_code, email_body
                    
                    # If we processed an email matching the subject filter but found no OTP
                    if subject_contains and subject_contains.lower() in subject.lower():
                        logging.warning(f"Email matched subject filter but no OTP found. Email body: {email_body}")
                        return None, email_body
                        
                except Exception as e:
                    logging.error(f"Error processing email ID {email_id}: {str(e)}")
                    continue
            
            logging.warning("No OTP code found in any matching emails")
            return None, None
            
        except Exception as e:
            logging.error(f"Error retrieving OTP: {str(e)}")
            return None, None

def get_otp_from_gmail(email_address: str, app_password: str, 
                       sender: str = None, subject_contains: str = None,
                       wait_time: int = 0, max_attempts: int = 10) -> Tuple[Optional[str], Optional[str]]:
    """
    Helper function to get OTP from Gmail.
    
    Args:
        email_address (str): Gmail address
        app_password (str): Gmail app password
        sender (str, optional): Filter emails by sender
        subject_contains (str, optional): Filter emails by subject
        wait_time (int): Time to wait between checks in seconds
        max_attempts (int): Maximum number of attempts to check for new emails
        
    Returns:
        tuple: (otp_code, email_body) or (None, None) if not found
    """
    handler = GmailOTPHandler(email_address, app_password)
    try:
        return handler.get_latest_otp(
            sender=sender,
            subject_contains=subject_contains,
            wait_time=wait_time,
            max_attempts=max_attempts
        )
    finally:
        handler.disconnect()
