# TCS NextStep Automation - Joining Letter(JL) Notifier

🚀 **Stop Manually Checking for Your Joining Letter!**

Tired of constantly logging into the TCS NextStep portal to check for your joining letter? This automation tool is specifically designed for TCS recruits who are eagerly waiting for their joining letters and want to be notified the moment there's an update.

### Why Use This Tool?
- 🤖 **Automated Checks**: No more manual logins - runs automatically in the background
- 🔔 **Instant Notifications**: Get immediate alerts when your joining letter is available or if not yet.
- ⏰ **24/7 Monitoring**: Checks the portal even when you're sleeping or busy
- 📱 **Peace of Mind**: Never miss an update about your joining status

This solution handles all the tedious parts of the TCS NextStep portal, including login, CAPTCHA solving, and OTP verification, so you don't have to!

## ✨ Features

- **Automated Login**: Handles TCS NextStep portal login process
- **CAPTCHA Solving**: Integrates with Gemini AI for automated CAPTCHA solving
- **OTP Handling**: Automatically retrieves and enters OTP from Gmail
- **Scheduled Checks**: Run automated checks at specified times
- **Error Handling**: Comprehensive error handling and logging
- **Headless Mode**: Supports both headless and visible browser modes

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- Playwright with Chromium browser
- [Google Gemini API Key](#obtaining-gemini-api-key)
- [Gmail account with App Password](#setting-up-gmail-app-password)

## 🔑 Obtaining Required Credentials

### Setting Up Gmail App Password

1. **Enable 2-Step Verification** (if not already enabled):
   - Go to your [Google Account](https://myaccount.google.com/)
   - Navigate to "Security"
   - Under "Signing in to Google," select **2-Step Verification**
   - Follow the steps to enable it

2. **Create an App Password**:
   - Go to [App Passwords](https://myaccount.google.com/apppasswords)
   - Select "Mail" as the app
   - Select "Other (Custom name)" as the device
   - Enter a name (e.g., "TCS Auto Login")
   - Click "Generate"
   - Copy the 16-character password (you'll use this as `GMAIL_APP_PASSWORD`)

### Obtaining Gemini API Key

1. **Go to Google AI Studio**:
   - Visit [Google AI Studio](https://makersuite.google.com/)
   - Sign in with your Google account

2. **Create an API Key**:
   - Click on "Get API Key" in the left sidebar
   - Click "Create API Key"
   - Copy the generated API key (you'll use this as `GEMINI_API_KEY`)

3. **Enable the API** (if required):
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Search for "Generative Language API"
   - Enable the API for your project

> **Note:** The Gemini API has usage limits. The free tier should be sufficient for personal use, but check the [pricing page](https://ai.google.dev/pricing) for details.

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/tcs-nextstep-automation.git
   cd tcs-nextstep-automation
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Chromium browser for Playwright**
   ```bash
   playwright install chromium
   ```
   
   This will only install the Chromium browser, keeping the installation lightweight.

### Configuration

1. **Create a `.env` file**
   ```bash
   cp .env.example .env
   ```

2. **Update `.env` with your credentials**
   ```
   # TCS Login Credentials (Email or CT/DT PIN)
   TCS_EMAIL=your_email@example.com
   
   # Gmail Credentials for OTP
   GMAIL_EMAIL=your_email@gmail.com
   GMAIL_APP_PASSWORD=your_app_password
   
   # Gemini API Key
   GEMINI_API_KEY=your_gemini_api_key
   
   # Application Settings
   HEADLESS=True  # Set to False for visible browser
   SCRIPT_TIMEOUT=100  # Script timeout in seconds
   ```

## 🛠 Usage

### Running the Script

```bash
python main.py
```

### Scheduling Automated Runs

1. **Start the scheduler**
   ```bash
   nohup python schedule_tcs_check.py > /dev/null 2>&1 &
   ```

2. **Check if scheduler is running**
   ```bash
   ps aux | grep schedule_tcs_check.py
   ```

3. **View scheduler logs**
   ```bash
   tail -f logs/scheduler.log
   ```

### Modifying Schedule

Edit the `RUN_TIMES` in `schedule_tcs_check.py` to change the schedule:

```python
# Scheduled times (24-hour format)
RUN_TIMES = [
    dt_time(9, 0),   # 9:00 AM
    dt_time(17, 0),  # 5:00 PM
]
```

Then restart the scheduler:
```bash
pkill -f schedule_tcs_check.py
nohup python schedule_tcs_check.py > /dev/null 2>&1 &
```

## 📝 Logging

The application maintains detailed logs in the `logs/` directory. Here's how to work with them:

### Viewing Logs

1. **List all log files**:
   ```bash
   ls -l logs/
   ```

2. **View logs in real-time**:
   ```bash
   # Main application logs
   tail -f logs/main.log
   
   # CAPTCHA solving logs
   tail -f logs/gemini_captcha_solver.log
   
   # Scheduler logs
   tail -f logs/scheduler.log
   ```

### Log Files

- `main.log`: Main application logs including login attempts and status checks
- `gemini_captcha_solver.log`: Detailed logs for CAPTCHA solving process
- `scheduler.log`: Scheduler execution logs and script run history

### Log Rotation

Logs are automatically rotated when they reach 5MB (2MB for CAPTCHA logs), keeping up to 3 backup files. Old logs are compressed and numbered (e.g., `main.log.1.gz`).

### Restarting the Scheduler

After making configuration changes, restart the scheduler:

```bash
# Stop existing scheduler
pkill -f schedule_tcs_check.py

# Start the scheduler
nohup python schedule_tcs_check.py > /dev/null 2>&1 &

# Verify it's running
ps aux | grep schedule_tcs_check.py
```

## 🤝 Contributing

We welcome contributions! Here's how you can help:

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Commit your changes**
   ```bash
   git commit -m 'Add some amazing feature'
   ```
4. **Push to the branch**
   ```bash
   git push origin feature/amazing-feature
   ```
5. **Open a Pull Request**

### Development Setup

1. Set up pre-commit hooks
   ```bash
   pre-commit install
   ```

2. Run tests
   ```bash
   python -m pytest
   ```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Playwright for browser automation
- Google Gemini for CAPTCHA solving
- Python community for awesome libraries
