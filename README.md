# TCS NextStep Automation - Joining Letter Notifier

🚀 **Automate Your TCS Joining Letter Check**

Tired of constantly checking the TCS NextStep portal for your joining letter? This tool automates the entire process and notifies you the moment there's an update.

## ✨ Key Features

- **Automated Portal Checks**: Runs on schedule without manual intervention
- **Instant Notifications**: Get email alerts for status updates
- **Cloud-Based**: Runs on GitHub Actions (24/7 availability)
- **Secure**: Uses GitHub Secrets to protect your credentials
- **Open Source**: Free to use and modify

## 🚀 Quick Start

### Prerequisites

- GitHub account (for cloud automation)
- Gmail account (for notifications)
- [Google Gemini API Key](#obtaining-gemini-api-key) (free tier available)

### 1. Fork & Set Up

1. **Fork** this repository
2. **Clone** your forked repository
3. **Set up GitHub Secrets**:
   ```
   TCS_EMAIL=your_tcs_email@example.com
   GMAIL_EMAIL=your_email@gmail.com
   GMAIL_APP_PASSWORD=your_16_digit_app_password
   GEMINI_API_KEY=your_gemini_api_key
   ```

### 2. Run Your First Check

1. Go to **Actions** tab
2. Select **TCS Joining Letter Check**
3. Click **Run workflow**

### 3. Get Notified

- Checks run automatically at 12 PM & 8 PM IST
- Receive email notifications for any updates
- View detailed logs in GitHub Actions

## 🔑 Setup Guide

### GitHub Secrets Setup

1. Go to your repository's **Settings** > **Secrets and variables** > **Actions**
2. Click **New repository secret** and add:
   - `TCS_EMAIL`: Your TCS login email
   - `GMAIL_EMAIL`: Your Gmail address
   - `GMAIL_APP_PASSWORD`: [Gmail App Password](#gmail-app-password)
   - `GEMINI_API_KEY`: [Google Gemini API Key](#gemini-api-key)

### Gmail App Password

1. Enable 2-Step Verification on your Google Account
2. Generate an App Password:
   - Go to [App Passwords](https://myaccount.google.com/apppasswords)
   - Select "Mail" and "Other (Custom name)"
   - Name it "TCS Auto Check"
   - Copy the 16-digit password

### Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/)
2. Click "Get API Key"
3. Create and copy your API key

## ⚙️ Advanced Configuration

### Custom Schedule

Edit `.github/workflows/tcs_check.yml` to change the schedule:

```yaml
on:
  schedule:
    - cron: '30 6,14 * * *'  # 12 PM & 8 PM IST
```

### Local Development

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   playwright install
   ```
3. Create `.env` file:
   ```
   TCS_EMAIL=your_email@example.com
   GMAIL_EMAIL=your_email@gmail.com
   GMAIL_APP_PASSWORD=your_app_password
   GEMINI_API_KEY=your_gemini_api_key
   HEADLESS=True
   SCRIPT_TIMEOUT=100
   ```
4. Run: `python main.py`

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md).

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Playwright for browser automation
- Google Gemini for CAPTCHA solving
- GitHub for free CI/CD with Actions
