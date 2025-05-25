"""
Gemini Captcha Solver Module

This module provides functionality to solve captchas using the Google Gemini API.
"""
import google.generativeai as genai
from pathlib import Path
import logging
import logging.handlers
import os

# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create logs directory if it doesn't exist
log_dir = Path('logs')
log_dir.mkdir(exist_ok=True)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# File handler with rotation
log_file = log_dir / 'gemini_captcha_solver.log'
file_handler = logging.handlers.RotatingFileHandler(
    log_file, maxBytes=2*1024*1024, backupCount=2, encoding='utf-8'
)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

def setup_gemini(api_key):
    """
    Initialize the Gemini API with the provided API key.
    
    Args:
        api_key (str): The Gemini API key
    """
    try:
        genai.configure(api_key=api_key)
        logger.info("Gemini API configured successfully")
    except Exception as e:
        logger.error(f"Failed to configure Gemini API: {str(e)}")
        raise

def solve_captcha(image_path):
    """
    Solve a captcha using the Gemini API.
    
    Args:
        image_path (str): Path to the captcha image file
        
    Returns:
        str: The solved captcha text, or None if solving failed
    """
    if not Path(image_path).exists():
        logger.error(f"Image file not found: {image_path}")
        return None
        
    try:
        logger.info(f"Attempting to solve captcha from: {image_path}")
        
        # Initialize the model
        model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
        
        # Read the image file
        image_data = Path(image_path).read_bytes()
        
        # Generate content with more specific instructions
        response = model.generate_content([
            """
            Analyze this CAPTCHA image and extract ONLY the alphanumeric characters.
            The text is typically 4-6 characters long and may include both letters and numbers.
            Return ONLY the characters with no additional text, spaces, or punctuation.
            If the text is unclear, make your best guess.
            """,
            {"mime_type": "image/png", "data": image_data}
        ])
        
        # Extract and clean the response
        captcha_text = response.text.strip()
        
        # Clean up the response (remove any non-alphanumeric characters)
        import re
        captcha_text = re.sub(r'[^a-zA-Z0-9]', '', captcha_text)
        
        if not captcha_text:
            logger.warning("Empty response from Gemini API")
            return None
            
        logger.info(f"Successfully solved captcha: {captcha_text}")
        
        # Save the deciphered captcha to a file for reference
        with open('captcha_deciphered.txt', 'w') as f:
            f.write(captcha_text)
        
        return captcha_text
        
    except Exception as e:
        logger.error(f"Error solving captcha: {str(e)}", exc_info=True)
        return None
