# Lead Router Automation Tool

This tool automates the configuration of Gravity Forms notification routing rules by reading data from Google Sheets.

## 🚨 Important Prerequisites

Before starting, ensure:

- **WARP VPN MUST BE DISABLED** - The script cannot access Jumpcloud SSO with WARP enabled
- **Manual Authentication** - You must manually complete website login → Jumpcloud SSO → WordPress admin in the automation window
- **Chrome must be at version 137** - This is due to the chrome-driver binary 

## 📋 System Requirements

- **Python**: 3.8 or higher
- **Operating System**: macOS
- **Chrome**: Version 317+

## 🔧 Installation

### Quick Setup (Recommended)

1. **Clone/Download** this project to your computer
2. **Run the setup script**:
   ```bash
   python setup.py
   ```

The setup script will:
- Check your Python version compatibility
- Install all required packages
- Create configuration templates
- Guide you through the setup process

### Manual Installation

If the quick setup doesn't work, follow these steps:

#### Step 1: Check Python Version
This tool works with **Python 3.8 or higher**. Check your version:
```bash
python --version
# or
python3 --version
```
Install Homebrew first
```/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"```

Then install Git ```$ brew install git```

If python is needed download from - https://www.python.org/downloads/

#### Step 2: Create Virtual Environment (Recommended)
```bash
# Create virtual environment
python -m venv leadrouter-env

# Activate it
# On macOS/Linux:
source leadrouter-env/bin/activate
```

#### Step 3: Install Dependencies
```bash
# Upgrade pip first (important!)
python -m pip install --upgrade pip

# Install requirements
pip install -r requirements.txt
```

### 🐛 Troubleshooting Installation Issues


#### Common Issues
- **"No module named 'X'"**: Make sure you activated your virtual environment
- **Permission errors**: Try adding `--user` flag: `pip install --user -r requirements.txt`

## 📋 Configuration


```bash
# macOS
CHROME_BINARY_PATH=/Applications/Google Chrome.app/Contents/MacOS/Google Chrome
CHROMEDRIVER_PATH=./chrome-for-testing/chromedriver

## 🚀 Usage

1. **Prepare your Google Sheet** with columns:
   - `DEALERSHIP NAME`
   - `FEED ID`
   - `ADF Email`
   - `Text Email`

2. **Run the automation**:
   ```bash
   python main.py
   ```

3. **Follow the prompts**:
   - Enter your Google Sheet URL or ID
   - Enter your WordPress site URL
   - Complete manual authentication in the browser window

## 🔍 System Requirements

- **Python**: 3.8 or higher (3.12 recommended, 3.13 has some package compatibility issues)
- **Operating System**: Windows, macOS, or Linux
- **Browser**: Google Chrome
- **Memory**: At least 2GB RAM
- **Network**: Internet connection for Google Sheets API and web automation


## 🆘 Getting Help

If you're still having issues:

1. **Check the error message** - most issues are in the installation step
2. **Try using Python 3.12** instead of 3.13 if you're having package issues
3. **Make sure you're using a virtual environment**
4. **Update pip** before installing: `python -m pip install --upgrade pip`

## 🔍 Troubleshooting

### Common Issues

**"WebDriver session is broken"**
- The automation Chrome window was closed
- Solution: Restart script, use the NEW automation window

**"Not on WordPress admin page"**
- Manual navigation incomplete
- Solution: Navigate to WordPress admin dashboard before pressing Enter

**"WARP VPN Blocking Authentication"**
- WARP VPN is still enabled
- Solution: Completely disable WARP VPN and restart authentication

**"Version mismatch between Chrome and ChromeDriver"**
- Chrome auto-updated but ChromeDriver didn't
- Solution: Use included Chrome for Testing or update ChromeDriver

**"Missing or empty values in sheet"**
- Required columns are missing or have empty cells
- Solution: Fill all cells in required columns

### Debug Mode

For troubleshooting, the script creates:
- Debug screenshots on errors
- Detailed console logging
- Chrome automation profile preservation

## 📁 Project Structure

```
lead-router/
├── main.py                 # Main automation script
├── requirements.txt        # Python dependencies
├── README.md              # This file
├── .env                   # Environment variables (you create)
├── credentials.json       # Google API credentials (you create)
├── token.json            # Generated OAuth token
└── chrome-for-testing/   # Chrome automation browser
    ├── chromedriver      # WebDriver executable
```

## 🔒 Security Notes

- **Private Repository** - All credentials are pre-configured for trusted users
- **Shared Access** - Google Sheets and WordPress access is shared among authorized team members
- **Use the automation Chrome profile only** for this script
- **Fresh profile isolates** automation from your personal browsing
- **WARP VPN must be disabled** during authentication for Jumpcloud SSO access
- **Google Cloud Console Sheets API** this gives all users in org access to the sheets API with these pre-configured credentials

## 🎯 Features

- **Batch Processing**: Handles multiple forms automatically
- **Smart Routing**: Configures both ADF/XML and Text notifications
- **Error Recovery**: Continues processing after individual form failures
- **Progress Tracking**: Clear progress indicators and completion summaries
- **Resume Capability**: Skips already completed forms on restart
- **Manual Authentication**: Secure SSO integration without storing credentials

## 📞 Support

If you encounter issues:

1. **Check WARP VPN** is disabled
2. **Verify all prerequisites** are installed
3. **Review error messages** for specific guidance
4. **Check debug screenshots** for visual confirmation of errors
5. **Restart with fresh Chrome profile** if WebDriver issues persist

---

**⚠️ Remember: WARP VPN must be OFF for Jumpcloud SSO to work properly!** 