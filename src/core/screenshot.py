import os
import logging
from datetime import datetime
from pathlib import Path

# Import SCREENSHOT_DIR from settings
from src.config.settings import SCREENSHOT_DIR

logger = logging.getLogger()

def ensure_screenshots_dir():
    """Create screenshots directory if it doesn't exist"""
    if not os.path.exists(SCREENSHOT_DIR):
        os.makedirs(SCREENSHOT_DIR)
    return SCREENSHOT_DIR

def take_screenshot(page, prefix='screenshot', selector=None):
    """Take a screenshot of the current page or a specific element.
    
    Args:
        page: The Playwright page object
        prefix (str): Prefix for the screenshot filename
        selector (str, optional): CSS selector for the element to capture
        
    Returns:
        str: Path to the saved screenshot, or None if failed
    """
    try:
        ensure_screenshots_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create a safe filename
        filename = f"{SCREENSHOT_DIR}/screenshot_{timestamp}_{prefix}.png"
        
        if selector:
            try:
                # Wait for the element to be visible
                element = page.locator(selector)
                element.wait_for(state='visible', timeout=10000)
                
                # Take screenshot of just the element
                element.screenshot(
                    path=filename,
                    timeout=10000,
                    type='png',
                    omit_background=True
                )
                logging.info(f"Element screenshot saved: {filename}")
            except Exception as e:
                logging.warning(f"Failed to capture element {selector}: {str(e)}")
                # Fall back to full page screenshot
                page.screenshot(
                    path=filename,
                    full_page=True,
                    timeout=10000,
                    type='png'
                )
                logging.info(f"Fell back to full page screenshot: {filename}")
        else:
            # Take full page screenshot
            page.screenshot(
                path=filename,
                full_page=True,
                timeout=10000,
                type='png'
            )
            logging.info(f"Full page screenshot saved: {filename}")
            
        return filename
    except Exception as e:
        logging.error(f"Failed to take screenshot: {str(e)}")
        return None

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