import logging
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path


from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from gemini_captcha_solver import setup_gemini, solve_captcha
from gmail_otp_retriever import get_otp_from_gmail
from tcs_jl_status_checker import tcs_jl_status_checker

# Load environment variables from .env file
load_dotenv()

# Constants
DEFAULT_SCRIPT_TIMEOUT = 80
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

def setup_logging():
    """Configure logging with a single instance of handlers."""
    # Clear any existing handlers from the root logger
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Set the root logger level
    root_logger.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Add console handler if not already present
    if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # Add file handler if not already present
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / 'main.log'
    
    if not any(isinstance(h, logging.handlers.RotatingFileHandler) for h in root_logger.handlers):
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    return root_logger

# Configure logging
logger = setup_logging()

# Configure Gemini API
setup_gemini(GEMINI_API_KEY)

def ensure_screenshots_dir():
    """Create screenshots directory if it doesn't exist"""
    if not os.path.exists(SCREENSHOT_DIR):
        os.makedirs(SCREENSHOT_DIR)
    return SCREENSHOT_DIR

def take_screenshot(page, element_selector=None):
    """Take a screenshot of the current page or a specific element.
    
    Args:
        page: The Playwright page object
        element_selector: Optional CSS selector for the element to screenshot
    """
    try:
        ensure_screenshots_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create a safe filename
        safe_selector = ""
        if element_selector:
            safe_selector = "_" + "".join(c if c.isalnum() else "_" for c in element_selector)
            safe_selector = safe_selector[:50]  # Limit filename length
        
        filename = f"screenshot_{timestamp}{safe_selector}.png"
        screenshot_path = os.path.join(SCREENSHOT_DIR, filename)
        
        # Take the screenshot
        if element_selector:
            element = page.locator(element_selector).first
            if element.is_visible():
                element.screenshot(path=screenshot_path)
                logging.info(f"Screenshot saved: {screenshot_path}")
                return screenshot_path
            
        # Fallback to full page screenshot
        page.screenshot(path=screenshot_path, full_page=True)
        logging.info(f"Full page screenshot saved: {screenshot_path}")
        return screenshot_path
        
    except Exception as e:
        logging.error(f"Error taking screenshot: {str(e)}")
        return None

def wait_for_element_safely(page, selector, timeout=10000, state='visible'):
    """Safely wait for an element with proper error handling.
    
    Returns:
        bool: True if element found and in specified state, False otherwise
    """
    try:
        page.wait_for_selector(selector, state=state, timeout=timeout)
        return True
    except PlaywrightTimeoutError:
        logging.warning(f"Timeout waiting for selector: {selector}")
    except Exception as e:
        logging.error(f"Error waiting for {selector}: {str(e)}")
    return False

def find_and_click_next_button(page):
    """Find and click the Next button with multiple fallback strategies.
    
    Returns:
        bool: True if button was found and clicked, False otherwise
    """
    next_button_selectors = [
        'button.greenButton:has-text("Next")',
        'button:has-text("Next")',
        'input[type="submit"][value*="Next"]',
        'button:contains("Next")',
        'input[type="button"][value*="Next"]'
    ]
    
    for selector in next_button_selectors:
        try:
            button = page.locator(selector)
            if button.is_visible() and button.is_enabled():
                button.click(timeout=5000)
                page.wait_for_timeout(2000)
                logging.info(f"Clicked Next button using selector: {selector}")
                return True
        except Exception as e:
            logging.debug(f"Failed to click with selector {selector}: {str(e)}")
    
    # Fallback to JavaScript click
    try:
        clicked = page.evaluate('''() => {
            const buttons = Array.from(document.querySelectorAll('button, input[type="submit"], input[type="button"]'));
            const nextBtn = buttons.find(btn => {
                const text = (btn.textContent || '').toLowerCase().trim();
                const value = (btn.getAttribute('value') || '').toLowerCase().trim();
                return (text.includes('next') || value.includes('next')) && 
                       !btn.disabled && 
                       btn.offsetParent !== null;
            });
            if (nextBtn) {
                nextBtn.click();
                return true;
            }
            return false;
        }''')
        
        if clicked:
            page.wait_for_timeout(2000)
            logging.info("Clicked Next button using JavaScript fallback")
            return True
            
    except Exception as e:
        logging.error(f"JavaScript fallback failed: {str(e)}")
    
    logging.error("Could not find or click Next button")
    take_screenshot(page, "next_button_error")
    return False

def handle_otp_process(page, max_attempts=8, wait_time=3):
    """Handle the OTP retrieval and input process.
    
    Args:
        page: Playwright page object
        max_attempts: Maximum attempts to retrieve OTP from Gmail
        wait_time: Time to wait between OTP retrieval attempts
        
    Returns:
        bool: True if OTP was successfully entered and submitted, False otherwise
    """
    try:
        logging.info("Starting OTP process...")
        
        # Wait for OTP input field to be present and enabled
        otp_input_selector = 'input#loginOtp'
        if not wait_for_element_safely(page, otp_input_selector, timeout=20000):
            logging.error("OTP input field not found")
            take_screenshot(page, "otp_input_not_found")
            return False
        
        # Wait for input to be enabled
        try:
            page.wait_for_function('''() => {
                const input = document.querySelector('input#loginOtp');
                return input && !input.disabled;
            }''', timeout=30000)
            logging.info("OTP input field is ready")
        except PlaywrightTimeoutError:
            logging.warning("OTP input may still be disabled, proceeding anyway...")
        
        # Wait for OTP email
        logging.info(f"Waiting for OTP email (will check {max_attempts} times with {wait_time}s intervals)...")
        
        # Initial wait to ensure email has time to arrive
        logging.info("Waiting 20 seconds for OTP email to arrive...")
        time.sleep(20)
        
        # Get OTP from Gmail
        otp = None
        for attempt in range(1, max_attempts + 1):
            logging.info(f"Attempt {attempt}/{max_attempts}: Retrieving OTP from Gmail...")
            otp, _ = get_otp_from_gmail(
                email_address=GMAIL_EMAIL,
                app_password=GMAIL_APP_PASSWORD,
                subject_contains="TCS NextStep",
                wait_time=1,  # Shorter wait time since we're retrying
                max_attempts=1
            )
            
            if otp and len(otp) >= 4:
                logging.info("OTP retrieved successfully")
                break
                
            if attempt < max_attempts:
                time.sleep(wait_time)
        
        if not otp or len(otp) < 4:
            logging.error(f"Failed to retrieve valid OTP. Received: {otp}")
            take_screenshot(page, "otp_retrieval_failed")
            return False
        
        # Fill OTP
        otp_input = page.locator(otp_input_selector)
        otp_input.fill('')  # Clear existing text
        
        # Type OTP character by character to mimic human typing
        for char in otp:
            otp_input.type(char)
            time.sleep(0.1)  # Reduced delay for faster input
        
        logging.info("OTP filled successfully")
        
        # Trigger validation events
        page.evaluate('''() => {
            const input = document.querySelector('input#loginOtp');
            if (input) {
                input.dispatchEvent(new Event('input', { bubbles: true }));
                input.dispatchEvent(new Event('blur', { bubbles: true }));
            }
        }''')
        
        # Wait for validation (reduced from 2s to 1s)
        time.sleep(1)
        
        # Click login button with retry logic
        login_button_selector = 'button#verifyLoginOTPBtn'
        login_button = page.locator(login_button_selector)
        
        if login_button.is_enabled():
            logging.info("Login button is enabled, clicking...")
            take_screenshot(page, "before_login_click")
            
            # Try direct click first
            try:
                login_button.click(timeout=5000)
            except Exception as e:
                logging.warning(f"Direct click failed, trying JavaScript click: {str(e)}")
                page.evaluate(f'''() => {{
                    const btn = document.querySelector('{login_button_selector}');
                    if (btn) btn.click();
                }}''')
            
            logging.info("Login button clicked, waiting for response...")
            time.sleep(2)  # Reduced from 3s to 2s
            take_screenshot(page, "after_login_click")
            return True
            
        logging.warning("Login button is still disabled after OTP entry")
        take_screenshot(page, "otp_filled_but_disabled")
        return False
            
    except Exception as e:
        logging.error(f"Error in OTP process: {str(e)}", exc_info=True)
        take_screenshot(page, "otp_process_error")
        return False

def check_login_result(page, timeout=10000):
    """Check if login was successful or if there were errors.
    
    Args:
        page: Playwright page object
        timeout: Maximum time to wait for page to load (ms)
        
    Returns:
        bool: True if login successful, False if error detected, None if indeterminate
    """
    try:
        # Wait for page to load
        page.wait_for_load_state('networkidle', timeout=timeout)
        
        # Common error selectors
        error_selectors = [
            'div.error-message',
            'div.alert-danger',
            'div[class*="error"]',
            'div[ng-show*="error"]',
            'span.error',
            'p.error',
            'div.alert',
            'div[role="alert"]',
            '.error-text',
            '.validation-error',
            '.login-error',
            '.message-error'
        ]
        
        # Check for error messages
        for selector in error_selectors:
            try:
                element = page.locator(selector).first
                if element.is_visible():
                    error_text = element.inner_text().strip()
                    if error_text:
                        logging.error(f"Login error detected: {error_text}")
                        take_screenshot(page, f"login_error_{selector.replace('.', '_').replace(' ', '_')}")
                        return False
            except Exception as e:
                logging.debug(f"Error checking selector {selector}: {str(e)}")
                continue
        
        # Check for success indicators
        success_indicators = [
            'a[href*="logout"]',
            'div.welcome-message',
            'div.dashboard',
            'h1:has-text("Welcome")',
            'div[class*="success"]'
        ]
        
        for selector in success_indicators:
            try:
                if page.locator(selector).is_visible():
                    logging.info("Login successful - success indicator found")
                    return True
            except Exception:
                continue
        
        logging.warning("Could not determine login status - no clear success or error indicators found")
        return None
        
    except Exception as e:
        logging.error(f"Error checking login result: {str(e)}", exc_info=True)
        take_screenshot(page, "result_check_error")
        return None

def is_on_otp_page(page, timeout=5000):
    """Check if we're on the OTP verification page.
    
    Returns:
        bool: True if on OTP page, False otherwise
    """
    try:
        # Check for OTP section header
        otp_header = page.locator('div#loginSection:has-text("OTP Verification")')
        if otp_header.is_visible():
            return True
            
        # Also check for OTP input field as a fallback
        otp_input = page.locator('input#loginOtp')
        return otp_input.is_visible()
        
    except Exception as e:
        logging.debug(f"Error checking OTP page: {str(e)}")
        return False

def handle_captcha(page, max_retries=3):
    """Handle CAPTCHA solving with retry logic."""
    logging.info("Starting CAPTCHA solving process...")
    
    for attempt in range(1, max_retries + 1):
        try:
            logging.info(f"CAPTCHA attempt {attempt}/{max_retries}")
            
            # Take new screenshot for CAPTCHA
            captcha_screenshot = take_screenshot(page, 'captcha_image')
            if not captcha_screenshot:
                logging.error("Failed to take CAPTCHA screenshot")
                continue
            
            # Solve CAPTCHA using the existing solve_captcha function
            logging.info("Sending CAPTCHA to solver...")
            captcha_text = solve_captcha(captcha_screenshot)
            
            if not captcha_text:
                logging.error("Failed to solve CAPTCHA")
                take_screenshot(page, f"captcha_failed_attempt_{attempt}")
                continue
                
            logging.info(f"CAPTCHA solved: {captcha_text}")
            
            # Fill CAPTCHA
            captcha_input_selector = 'input#userCaptcha[ng-model="userVO.userCaptcha"][name="userCaptcha"]'
            if not wait_for_element_safely(page, captcha_input_selector, timeout=10000):
                logging.error("CAPTCHA input field not found")
                take_screenshot(page, "captcha_input_not_found")
                continue
            
            captcha_input = page.locator(captcha_input_selector)
            if not captcha_input.is_visible():
                logging.error("CAPTCHA input field is not visible")
                take_screenshot(page, "captcha_input_not_visible")
                continue
            
            # Clear and fill CAPTCHA
            captcha_input.fill('')
            page.wait_for_timeout(200)
            captcha_input.fill(captcha_text)
            logging.info("CAPTCHA filled successfully")
            take_screenshot(page, f"captcha_attempt_{attempt}")
            
            # Click Next button
            page.wait_for_timeout(2000)  # Give some time for any client-side validation
            if not find_and_click_next_button(page):
                logging.error("Failed to click Next button")
                continue
                
            # Wait for either OTP page or stay on current page (indicating CAPTCHA failure)
            try:
                # Wait for navigation to complete or timeout
                page.wait_for_load_state('networkidle', timeout=10000)
                
                # Check if we're on the OTP page
                if is_on_otp_page(page):
                    logging.info("Successfully navigated to OTP page")
                    return True
                    
                # If we're not on OTP page, assume CAPTCHA failed
                logging.warning("Still on CAPTCHA page after submission, will retry...")
                take_screenshot(page, f"captcha_retry_{attempt}")
                
                # Clear the CAPTCHA field for next attempt
                if wait_for_element_safely(page, captcha_input_selector, timeout=3000):
                    page.locator(captcha_input_selector).fill('')
                
                # Wait a bit before retrying
                page.wait_for_timeout(2000)
                
            except Exception as e:
                logging.warning(f"Navigation check error: {str(e)}")
                take_screenshot(page, f"navigation_error_attempt_{attempt}")
                continue
            
        except Exception as e:
            logging.error(f"Error in CAPTCHA attempt {attempt}: {str(e)}")
            take_screenshot(page, f"captcha_error_attempt_{attempt}")
    
    logging.error(f"Failed to solve CAPTCHA after {max_retries} attempts")
    return False

def tcs_login_and_screenshot():
    """Main function to handle TCS login process and JL status check."""
    logging.info("Starting TCS login process...")
    
    # Browser launch arguments
    browser_args = [
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-blink-features=AutomationControlled',
        '--window-size=1920,1080',
        '--disable-infobars',
        '--disable-notifications',
    ]
    
    with sync_playwright() as p:
        try:
            # Launch browser
            logging.info(f"Launching {'headless ' if HEADLESS else ''}browser...")
            browser = p.chromium.launch(
                headless=HEADLESS,
                args=browser_args,
                slow_mo=100 if not HEADLESS else 0  # Only slow down in non-headless mode
            )
            
            # Create browser context
            context = browser.new_context(
                viewport={'width': 1366, 'height': 768},
                user_agent=USER_AGENT,
                locale='en-US',
                timezone_id='Asia/Kolkata',
                java_script_enabled=True,
                ignore_https_errors=True
            )
            
            # Set default timeout for all pages in this context
            context.set_default_timeout(30000)  # 30 seconds
            
            # Create new page
            page = context.new_page()
            
            # Step 1: Navigate to TCS NextStep portal
            logging.info("Navigating to TCS NextStep portal...")
            try:
                page.goto('https://nextstep.tcs.com/campus/', timeout=60000)
                logging.info("Page loaded successfully")
            except Exception as e:
                logging.error(f"Failed to load TCS portal: {str(e)}")
                take_screenshot(page, "page_load_failed")
                return False
            
            # Step 2: Click login button
            login_button_selector = 'a.updatesClick:has-text("Login")'
            if not wait_for_element_safely(page, login_button_selector):
                logging.error("Login button not found")
                take_screenshot(page, "login_button_not_found")
                return False
            
            logging.info("Clicking login button...")
            page.click(login_button_selector)
            
            # Step 3: Wait for and fill email
            email_selector = 'input.form-control.loginID[type="text"][name="loginID"]'
            if not wait_for_element_safely(page, email_selector):
                logging.error("Email input field not found")
                take_screenshot(page, "email_input_not_found")
                return False
            
            logging.info("Entering email address...")
            email_input = page.locator(email_selector)
            email_input.fill('')  # Clear any existing text
            page.wait_for_timeout(200)
            email_input.fill(TCS_EMAIL)
            take_screenshot(page, "email_entered")
            
            # Step 4: Handle CAPTCHA with retry logic
            logging.info("Starting CAPTCHA solving process...")
            captcha_success = handle_captcha(page)
            
            if not captcha_success:
                logging.error("Failed to solve CAPTCHA after multiple attempts")
                return False
            
            # Step 5: Handle OTP process
            logging.info("Starting OTP process...")
            if not handle_otp_process(page):
                logging.error("OTP process failed")
                return False
            
            # Step 6: Verify login and check JL status
            login_status = check_login_result(page)
            if login_status is False:
                logging.error("Login verification failed")
                return False
            
            logging.info("Login successful! Proceeding to JL status check...")
            success, status = tcs_jl_status_checker(page)
            
            if success:
                logging.info(f"Status check completed. Status: {status}")
            else:
                logging.error(f"Status check failed: {status}")
            
            return success
            
        except Exception as e:
            logging.error(f"An unexpected error occurred: {str(e)}", exc_info=True)
            take_screenshot(page, "unexpected_error")
            return False
            
        finally:
            # Ensure browser is closed properly
            try:
                if 'browser' in locals() and browser:
                    browser.close()
            except Exception as e:
                logging.error(f"Error closing browser: {str(e)}")

def timeout_handler(signum, frame):
    """Handle script timeout by logging and exiting gracefully.
    
    Args:
        signum: Signal number
        frame: Current stack frame
    """
    logging.error(f"Script timed out after {SCRIPT_TIMEOUT} seconds")
    logging.error("Forcing script exit due to timeout")
    # Force exit with a non-zero status code to indicate error
    os._exit(1)

def main():
    """Main entry point for the TCS login script."""
    try:
        # Set up signal handler for script timeout
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(SCRIPT_TIMEOUT)
        
        logging.info("=" * 50)
        logging.info("Starting TCS Login Automation")
        logging.info(f"Script timeout set to {SCRIPT_TIMEOUT} seconds")
        logging.info(f"Running in {'HEADLESS' if HEADLESS else 'VISIBLE'} mode")
        
        # Verify required credentials
        missing_creds = []
        if not TCS_EMAIL:
            missing_creds.append("TCS_EMAIL")
        if not GMAIL_EMAIL:
            missing_creds.append("GMAIL_EMAIL")
        if not GEMINI_API_KEY:
            missing_creds.append("GEMINI_API_KEY")
            
        if missing_creds:
            logging.error(f"Missing required environment variables: {', '.join(missing_creds)}")
            sys.exit(1)
            
        # Prompt for Gmail App Password if not set
        global GMAIL_APP_PASSWORD
        if not GMAIL_APP_PASSWORD:
            try:
                import getpass
                GMAIL_APP_PASSWORD = getpass.getpass("Enter your Gmail App Password: ")
                if not GMAIL_APP_PASSWORD:
                    logging.error("No password provided")
                    sys.exit(1)
            except Exception as e:
                logging.error(f"Error reading password: {str(e)}")
                sys.exit(1)
        
        # Run the main login process
        success = tcs_login_and_screenshot()
        
        if success is None:
            logging.warning("Login process completed with indeterminate status")
            sys.exit(2)
        elif not success:
            logging.error("Login process failed")
            sys.exit(1)
            
        logging.info("TCS Login Automation completed successfully")
        sys.exit(0)
        
    except KeyboardInterrupt:
        logging.warning("Script interrupted by user")
        sys.exit(130)  # Standard exit code for Ctrl+C
    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        # Always ensure the alarm is disabled
        signal.alarm(0)
        logging.info("Script execution completed")
        logging.info("=" * 50)

if __name__ == "__main__":
    main()