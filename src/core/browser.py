import logging
from playwright.sync_api import sync_playwright
from src.config.settings import HEADLESS, USER_AGENT

logger = logging.getLogger()

def launch_browser_and_page(playwright_sync_api):
    """
    Launches a Playwright browser and creates a new page with predefined settings.

    Args:
        playwright_sync_api: The Playwright Sync API context object obtained from sync_playwright().

    Returns:
        tuple: A tuple containing (browser, page) objects.
    """
    try:
        # Browser launch arguments
        browser_args = [
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-blink-features=AutomationControlled',
            '--window-size=1366,768',
            '--disable-infobars',
            '--disable-notifications',
        ]
        
        # Launch browser
        logging.info(f"Launching {'headless ' if HEADLESS else ''}browser...")
        browser = playwright_sync_api.chromium.launch(
            headless=HEADLESS,
            args=browser_args,
            slow_mo=100 if not HEADLESS else 0
        )
        
        # Create browser context
        context = browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent=USER_AGENT,
            locale='en-US',
            timezone_id='Asia/Kolkata',
            java_script_enabled=True,
            ignore_https_errors=True,
            device_scale_factor=1
        )
        
        # Set default timeout for all pages in this context
        context.set_default_timeout(30000)
        
        # Create new page
        page = context.new_page()
        
        return browser, page
    except Exception as e:
        logging.error(f"Failed to launch browser or create page: {str(e)}")
        if 'browser' in locals() and browser:
            browser.close()
        raise