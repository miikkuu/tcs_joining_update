import logging
import time
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright # Added this import

from src.config.settings import TCS_EMAIL, GMAIL_EMAIL, GMAIL_APP_PASSWORD, GEMINI_API_KEY
from src.core.screenshot import take_screenshot
from src.core.utils import wait_for_element_safely, find_and_click_next_button
from src.core.browser import launch_browser_and_page
from src.services.captcha_solver import setup_gemini, solve_captcha
from src.services.otp_retriever import get_otp_from_gmail
from src.services.status_checker import tcs_jl_status_checker

logger = logging.getLogger()

# Configure Gemini API (should be done once at startup, but placed here for modularity)
setup_gemini(GEMINI_API_KEY)

def handle_otp_process(page, max_attempts=5, wait_time=5):
    """Handle the OTP retrieval and input process.
    
    Args:
        page: Playwright page object
        max_attempts: Maximum attempts to retrieve OTP from Gmail
        wait_time: Time to wait between OTP retrieval attempts
        
    Returns:
        bool: True if OTP was successfully entered and submitted, False otherwise, None if full restart needed
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
        logging.info(f"Waiting for OTP email (will check internally for up to 20 seconds)...")
        time.sleep(20) # Initial wait to ensure email has time to arrive
        
        # Get OTP from Gmail with internal retries
        otp, _ = get_otp_from_gmail(
            email_address=GMAIL_EMAIL,
            app_password=GMAIL_APP_PASSWORD,
            subject_contains="TCS NextStep: Login Email ID Verification",
            sender="recruitment.entrylevel@tcs.com",
            wait_time=10,
            max_attempts=2
        )
        
        if not otp or len(otp) < 4:
            logging.error(f"Failed to retrieve valid OTP. Received: {otp}. Signalling for full restart.")
            take_screenshot(page, "otp_retrieval_failed")
            return None # Signal for a full restart
        
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

def handle_captcha(page, max_retries=2):
    """Handle CAPTCHA solving with retry logic.
    
    Returns:
        tuple: (success: bool, needs_refresh: bool)
    """
    logging.info("Starting CAPTCHA solving process...")
    
    captcha_input_selector = 'input#userCaptcha[ng-model="userVO.userCaptcha"][name="userCaptcha"]'
    
    for attempt in range(1, max_retries + 1):
        try:
            logging.info(f"CAPTCHA attempt {attempt}/{max_retries}")
            
            # Take screenshot of just the CAPTCHA element
            captcha_selector = 'label.control-label.input-sm.ng-binding[style*="letter-spacing: 20px"]'
            captcha_screenshot = take_screenshot(page, 'captcha_image', selector=captcha_selector)
            
            # If we couldn't take a screenshot at all, log and continue to next attempt
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
            
            # Wait for navigation to complete or timeout
            try:
                page.wait_for_load_state('networkidle', timeout=10000)
                
                # Check if we're on the OTP page
                if is_on_otp_page(page):
                    logging.info("Successfully navigated to OTP page")
                    return True, False
                    
                # If we're not on OTP page, check if we need a refresh
                logging.warning("Still on CAPTCHA page after submission")
                take_screenshot(page, f"captcha_retry_{attempt}")
                
                # Check if we need a full page refresh
                if should_retry_with_refresh(page):
                    logging.info("Page state indicates a refresh is needed")
                    return False, True
                    
                # Otherwise, just clear the field and retry
                logging.info("Retrying CAPTCHA...")
                if wait_for_element_safely(page, captcha_input_selector, timeout=3000):
                    page.locator(captcha_input_selector).fill('')
                page.wait_for_timeout(2000)
                
            except Exception as e:
                logging.warning(f"Navigation check error: {str(e)}")
                take_screenshot(page, f"navigation_error_attempt_{attempt}")
                if "navigation" in str(e).lower() or "timeout" in str(e).lower():
                    return False, True
                continue
            
        except Exception as e:
            logging.error(f"Error in CAPTCHA attempt {attempt}: {str(e)}")
            take_screenshot(page, f"captcha_error_attempt_{attempt}")
            if "navigation" in str(e).lower() or "timeout" in str(e).lower():
                return False, True
            continue
    
    logging.error(f"Failed to solve CAPTCHA after {max_retries} attempts")
    return False, False

def should_retry_with_refresh(page, max_attempts=3):
    """Check if we should retry with a page refresh or browser restart."""
    # Check for common error conditions that indicate a refresh is needed
    error_conditions = [
        page.locator('div.error-message:has-text("session")').is_visible(),
        page.locator('div.error-message:has-text("expired")').is_visible(),
        page.locator('div.error-message:has-text("invalid")').is_visible(),
        page.url == 'about:blank'  # Page got unloaded
    ]
    return any(error_conditions)

def tcs_login_and_screenshot():
    """Main function to handle TCS login process with retry logic."""
    max_login_attempts = 3
    
    with sync_playwright() as p:
        attempt = 0
        while attempt < max_login_attempts:
            attempt += 1
            logging.info(f"Starting login attempt {attempt}/{max_login_attempts}")
            
            browser = None
            try:
                browser, page = launch_browser_and_page(p) # Pass the playwright object
                
                # Navigate to TCS NextStep portal
                logging.info("Navigating to TCS NextStep portal...")
                try:
                    page.goto('https://nextstep.tcs.com/campus/', timeout=60000)
                    logging.info("Page loaded successfully")
                except Exception as e:
                    logging.error(f"Failed to load TCS portal: {str(e)}")
                    take_screenshot(page, "page_load_failed")
                    if browser:
                        browser.close()
                    continue
                
                # Click login button
                login_button_selector = 'a.updatesClick:has-text("Login")'
                if not wait_for_element_safely(page, login_button_selector):
                    logging.error("Login button not found")
                    take_screenshot(page, "login_button_not_found")
                    if browser:
                        browser.close()
                    continue
                
                logging.info("Clicking login button...")
                page.click(login_button_selector)
                
                # Wait for and fill email
                email_selector = 'input.form-control.loginID[type="text"][name="loginID"]'
                if not wait_for_element_safely(page, email_selector):
                    logging.error("Email input field not found")
                    take_screenshot(page, "email_input_not_found")
                    if browser:
                        browser.close()
                    continue
                
                logging.info("Entering email address...")
                email_input = page.locator(email_selector)
                email_input.fill('')  # Clear any existing text
                page.wait_for_timeout(200)
                email_input.fill(TCS_EMAIL)
                take_screenshot(page, "email_entered")
                
                # Handle CAPTCHA with refresh logic
                logging.info("Starting CAPTCHA solving process...")
                captcha_success, needs_refresh = handle_captcha(page)
                
                if needs_refresh:
                    logging.info("Page refresh needed, restarting login process...")
                    if browser:
                        browser.close()
                    continue  # Will retry from the beginning
                    
                if not captcha_success:
                    logging.error("Failed to solve CAPTCHA")
                    if browser:
                        browser.close()
                    return False
                
                # Handle OTP process
                logging.info("Starting OTP process...")
                otp_result = handle_otp_process(page)
                if otp_result is None:
                    logging.warning("OTP process requires a full restart.")
                    if browser:
                        browser.close()
                    continue # This will trigger the next attempt in the while loop
                elif not otp_result:
                    logging.error("OTP process failed (non-restartable error).")
                    if browser:
                        browser.close()
                    return False
                
                # Verify login and check JL status
                login_status = check_login_result(page)
                if login_status is False:
                    logging.error("Login verification failed")
                    if browser:
                        browser.close()
                    return False
                
                logging.info("Login successful! Proceeding to JL status check...")
                success, status = tcs_jl_status_checker(page)
                
                if success:
                    logging.info(f"Status check completed. Status: {status}")
                else:
                    logging.error(f"Status check failed: {status}")
                
                if browser:
                    browser.close()
                return success
                
            except Exception as e:
                logging.error(f"Error in login attempt {attempt}: {str(e)}")
                if browser:
                    browser.close()
                continue
                
        logging.error(f"Failed to login after {max_login_attempts} attempts")
        return False