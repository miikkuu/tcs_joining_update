# Project Code Documentation: TCS NextStep Automation

Welcome, aspiring developer! This document will guide you through the inner workings of the TCS NextStep Automation project. We'll break down each part of the code, explain its purpose, and show you how everything fits together.

## 1. Introduction: What Does This Project Do?

Imagine you're waiting for an important "Joining Letter" from TCS, and you have to keep checking their NextStep portal manually. This project automates that tedious task!

**In simple terms, this program:**
*   **Automatically logs into the TCS NextStep portal.**
*   **Handles tricky parts like CAPTCHAs and One-Time Passwords (OTPs).**
*   **Checks your Joining Letter (JL) status.**
*   **Sends you an email notification with your status and a screenshot of the portal.**
*   **It's designed to run automatically, even on a schedule (like twice a day!).**

This project uses a tool called **Playwright** to control a web browser (like Chrome) automatically, just as if a human were clicking and typing.

## 2. Project Structure: Where Everything Lives

The project is organized into several folders and files to keep things neat and understandable.

```
.
├── .env.example             # Example file for environment variables (your secret settings)
├── .gitignore               # Tells Git which files to ignore (like temporary files or secrets)
├── LICENSE                  # The license under which this project is shared
├── main.py                  # The main starting point of the program
├── README.md                # The general project overview and quick start guide
├── REFACTORING_PLAN.md      # (Internal) Notes on planned code improvements
├── requirements.txt         # Lists all the Python libraries this project needs to run
├── schedule_tcs_check.py    # A script to help schedule the main program (e.g., for daily runs)
└── src/                     # This folder contains all the core logic and services
    ├── config/
    │   └── settings.py      # Stores configuration settings (like email addresses, API keys)
    ├── core/
    │   ├── browser.py       # Handles launching and managing the web browser
    │   ├── screenshot.py    # Takes screenshots of the web page
    │   └── utils.py         # Contains small, reusable helper functions
    └── services/
        ├── captcha_solver.py # Solves CAPTCHAs using an AI service (Google Gemini)
        ├── otp_retriever.py  # Fetches OTPs from your Gmail inbox
        ├── status_checker.py # Checks the Joining Letter status on the portal
        └── tcs_login.py      # Orchestrates the entire login process
```

## 3. Core Components (Modules): What Each File Does

Let's dive into what each important Python file (`.py`) is responsible for:

*   **[`main.py`](main.py): The Conductor**
    *   This is where the program starts.
    *   It sets up logging (so you can see what the program is doing).
    *   It configures the Gemini API (for CAPTCHA solving).
    *   It checks if all necessary secret settings (like your email) are provided.
    *   Crucially, it calls the `tcs_login_and_screenshot()` function from `src/services/tcs_login.py` to start the whole login process.
    *   It handles overall errors and ensures the script exits gracefully.

*   **[`src/config/settings.py`](src/config/settings.py): The Settings Hub**
    *   This file holds all the important configuration values that the program needs.
    *   Examples: `TCS_EMAIL` (your TCS login ID), `GMAIL_EMAIL` (your Gmail for OTPs), `GMAIL_APP_PASSWORD` (a special password for apps to access Gmail), `GEMINI_API_KEY` (for CAPTCHA solving), `HEADLESS` (whether the browser runs visibly or in the background), `SCRIPT_TIMEOUT` (how long the script should run before giving up).
    *   These values are typically loaded from a `.env` file to keep your sensitive information separate from the code.

*   **[`src/core/browser.py`](src/core/browser.py): The Browser Launcher**
    *   This file is responsible for starting and setting up the web browser using Playwright.
    *   The `launch_browser_and_page()` function creates a new browser instance (like opening a new Chrome window) and a new "page" (like opening a new tab).
    *   It configures the browser with settings like screen size, user agent (what the website thinks your browser is), and whether it runs in "headless" mode (invisible) or not.
    *   It's designed to be called for each login attempt to ensure a fresh browser session, preventing issues like the "Playwright Sync API inside the asyncio loop" error we fixed!

*   **[`src/core/screenshot.py`](src/core/screenshot.py): The Photographer**
    *   Contains the `take_screenshot()` function.
    *   This function captures images of the web page at different stages of the login process.
    *   These screenshots are super helpful for debugging (understanding what went wrong if the script fails) and are also sent in the notification emails.

*   **[`src/core/utils.py`](src/core/utils.py): The Helper Toolkit**
    *   This file contains small, general-purpose functions that are used across different parts of the project.
    *   Examples: `wait_for_element_safely()` (waits for a specific part of the web page to appear before trying to interact with it, preventing errors), `find_and_click_next_button()` (a common action in web forms).

*   **[`src/services/captcha_solver.py`](src/services/captcha_solver.py): The CAPTCHA Breaker**
    *   This module integrates with the Google Gemini API to solve image-based CAPTCHAs.
    *   The `solve_captcha()` function takes a screenshot of the CAPTCHA image, sends it to Gemini, and gets the text solution back.

*   **[`src/services/otp_retriever.py`](src/services/otp_retriever.py): The OTP Fetcher**
    *   This file connects to your Gmail account (using your `GMAIL_EMAIL` and `GMAIL_APP_PASSWORD`).
    *   The `get_otp_from_gmail()` function searches your inbox for specific emails (like the TCS OTP email) and extracts the One-Time Password from them.
    *   It includes retry logic to wait for the email to arrive.

*   **[`src/services/status_checker.py`](src/services/status_checker.py): The Status Reporter**
    *   After a successful login, this module is responsible for navigating to the relevant page on the TCS portal and extracting your Joining Letter status.
    *   The `tcs_jl_status_checker()` function performs this check.

*   **[`src/services/tcs_login.py`](src/services/tcs_login.py): The Login Orchestrator (The Brains!)**
    *   This is one of the most important files. It brings together many other modules to perform the complete login sequence.
    *   The `tcs_login_and_screenshot()` function contains the main login logic, including:
        *   **Retry Mechanism:** It attempts the entire login process multiple times if it fails (e.g., due to a missed OTP).
        *   **Browser Management:** It ensures a fresh browser is launched for each attempt.
        *   **Navigation:** Goes to the TCS portal.
        *   **Email Input:** Fills in your TCS email.
        *   **CAPTCHA Handling:** Calls `handle_captcha()` to solve and input the CAPTCHA.
        *   **OTP Handling:** Calls `handle_otp_process()` to retrieve and input the OTP. If the OTP isn't found after retries, it signals for a full login restart.
        *   **Login Verification:** Checks if the login was truly successful.
        *   **Status Check:** Calls `tcs_jl_status_checker()` to get your JL status.

## 4. Program Flow: A Step-by-Step Journey

Let's trace how the program runs from start to finish:

1.  **Start (`main.py`):**
    *   The script begins execution.
    *   Logging is set up to record all actions and errors.
    *   Your secret credentials (from `.env`) are loaded and checked.
    *   The Gemini API is configured for CAPTCHA solving.

2.  **Login Attempts Loop (`tcs_login.py` - `tcs_login_and_screenshot` function):**
    *   The program enters a loop, ready to try logging in up to 3 times.
    *   **Crucially, for each attempt, a fresh Playwright browser instance is launched.** This ensures that if a previous attempt failed or got stuck, the next attempt starts with a clean slate.

3.  **Browser Launch (`src/core/browser.py`):**
    *   A new web browser (e.g., Chromium) is launched, either visibly or in headless (invisible) mode, along with a new blank page.

4.  **Navigate to TCS Portal:**
    *   The browser navigates to the TCS NextStep login page.

5.  **Click Login Button:**
    *   The script finds and clicks the "Login" button on the page.

6.  **Enter Email Address:**
    *   It waits for the email input field to appear and then types in your TCS email ID.
    *   A screenshot is taken at this stage.

7.  **CAPTCHA Handling (`src/services/captcha_solver.py`):**
    *   The script identifies the CAPTCHA image.
    *   A screenshot of the CAPTCHA is taken and sent to the Google Gemini AI for solving.
    *   The solved CAPTCHA text is received and typed into the CAPTCHA input field on the web page.
    *   If CAPTCHA solving fails, it might retry or signal for a page refresh.

8.  **Click Next/Proceed (after CAPTCHA):**
    *   The script clicks the "Next" or equivalent button to proceed after entering the CAPTCHA.

9.  **OTP Handling (`src/services/otp_retriever.py`):**
    *   The script waits for the OTP input field to be ready.
    *   It then connects to your Gmail account.
    *   It searches for the latest OTP email from TCS.
    *   **Internal Retries:** It will try to find the email a couple of times, waiting between attempts.
    *   If an OTP is found, it's typed into the OTP input field.
    *   **Full Restart Signal:** If no valid OTP is found after all internal retries, the `handle_otp_process` function returns `None`, which tells the main login loop (`tcs_login_and_screenshot`) to close the current browser and start a **completely new login attempt from the very beginning** (including launching a new browser). This is the key fix for the original problem!

10. **Verify Login Result (`tcs_login.py` - `check_login_result`):**
    *   After entering the OTP, the script checks the page for signs of successful login (e.g., a "Welcome" message, a dashboard) or error messages.

11. **Check JL Status (`src/services/status_checker.py`):**
    *   If login is successful, the script navigates to the relevant section of the portal to find and extract your Joining Letter status.

12. **Browser Closure:**
    *   Regardless of success or failure, the browser instance is always closed at the end of each login attempt (or when the script finishes). This cleans up resources.

13. **Final Outcome (`main.py`):**
    *   `main.py` receives the result of the login attempts.
    *   It logs whether the login was successful or failed after all retries.
    *   The script then exits.

## 5. Key Concepts for Beginners

*   **Playwright:** A powerful Python library that allows you to control web browsers (like Chrome, Firefox, Safari) programmatically. It's used here to automate clicks, typing, and navigation.
*   **Headless Browser:** A web browser that runs in the background without a visible user interface. This is useful for automation as it's faster and doesn't require a screen.
*   **CAPTCHA:** "Completely Automated Public Turing test to tell Computers and Humans Apart." These are those distorted images or puzzles designed to prevent bots. This project uses AI to solve them.
*   **OTP (One-Time Password):** A password that is valid for only one login session or transaction. Here, it's sent to your email for verification.
*   **Environment Variables:** Special variables set outside of your code (e.g., in a `.env` file or GitHub Secrets) that store sensitive information like passwords or API keys. This keeps your secrets safe and out of your main code.
*   **GitHub Actions:** A service provided by GitHub that allows you to automate tasks (like running this script) directly within your code repository. It's used here to schedule daily checks in the cloud.
*   **`try...except` blocks:** These are Python's way of handling errors. The code inside `try` is executed, and if an error occurs, the code inside `except` is run, preventing the program from crashing.
*   **`logging`:** A Python module used to record events that happen while the program is running. This helps you understand what the script is doing and diagnose problems.

## 6. How to Run/Debug Locally

If you want to run this project on your own computer and see it in action:

1.  **Get the Code:**
    ```bash
    git clone https://github.com/your-username/tcs-nextstep-automation.git
    cd tcs-nextstep-automation
    ```
2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    playwright install  # This downloads the necessary browser binaries
    ```
3.  **Set Up Your Secrets:**
    *   Create a file named `.env` in the main project folder (next to `main.py`).
    *   Add your credentials to this file (replace with your actual details):
        ```
        TCS_EMAIL=your_tcs_email@example.com
        GMAIL_EMAIL=your_email@gmail.com
        GMAIL_APP_PASSWORD=your_16_digit_app_password
        GEMINI_API_KEY=your_gemini_api_key
        HEADLESS=False  # Set to False to see the browser in action!
        SCRIPT_TIMEOUT=120
        ```
    *   **Important:** Never share your `.env` file or commit it to Git! It's already ignored by `.gitignore`.
4.  **Run the Program:**
    ```bash
    python main.py
    ```
    You will see the browser launch (if `HEADLESS=False`) and perform the login steps. The logs in your terminal will tell you what's happening.

This documentation should give a "noob developer" a solid understanding of how this project works!