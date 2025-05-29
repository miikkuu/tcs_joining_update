import logging
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from src.core.screenshot import take_screenshot

logger = logging.getLogger()

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