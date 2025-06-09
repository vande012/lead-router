# Lead Router Automation Tool

This tool automates the configuration of Gravity Forms notification routing rules by reading data from Google Sheets.

## 🚨 Important Prerequisites

Before starting, ensure:

- **WARP VPN MUST BE DISABLED** - The script cannot access Jumpcloud SSO with WARP enabled
- **Manual Authentication** - You must manually complete website login → Jumpcloud SSO → WordPress admin in the automation window
- **Chrome must be updated** - Check chrome://settings/help for latest version
- **Github Account is created** - You must have a Github account to access the project repository

## 📋 System Requirements

- **Python**: 3.8 or higher (3.12 recommended)
- **Operating System**: macOS, Windows, or Linux
- **Chrome**: Latest version (check chrome://settings/help)
- **Terminal**: macOS comes with Terminal (zsh/bash) pre-installed
- **Command Line Tools**: Will be installed automatically with Homebrew

## 🔧 Installation

### Step 1: Install Prerequisites

**Open Terminal:**
- Press `Cmd + Space`, type "Terminal", and press Enter
- All commands below work in both zsh (default) and bash

**Install Homebrew (macOS only):**
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**Install Git:**
```bash
brew install git
```

**Install Python (if needed):**
- Download from: https://www.python.org/downloads/
- Choose Python 3.12 (recommended) or 3.8+

**Update Chrome:**
1. Open Chrome
2. Go to: `chrome://settings/help`
3. Chrome will automatically check and update
4. Restart Chrome when prompted

### Step 2: Check Python Version
```bash
python --version
# or
python3 --version
```
*Make sure you have Python 3.8 or higher*

### Step 3: Create Virtual Environment (Recommended)
```bash
# Create virtual environment
python -m venv leadrouter-env

# Activate it
# On macOS/Linux:
source leadrouter-env/bin/activate

# On Windows:
leadrouter-env\Scripts\activate
```

### Step 4: Navigate to Project and Install Dependencies
```bash
# Navigate to project folder
cd lead-router

# Upgrade pip first (important!)
python -m pip install --upgrade pip

# Install requirements
pip install -r requirements.txt
```

### Step 5: Set Up Google Credentials
1. Download your `credentials.json` file (provided by admin)
2. Place it in the `lead-router` folder

## 🚀 How to Use

### Step 1: Prepare Your Google Sheet
Your Google Sheet must have a tab named **"Combined Feed Info"** with these columns:
- **DEALERSHIP NAME** - The dealership name
- **FEED ID** - Used for Dealer ID routing  
- **ADF Email** - Email for ADF/XML notifications
- **Text Email** - Email for Text notifications

### Step 2: Run the Script
```bash
python main.py
```

### Step 3: Follow the Prompts
1. **Enter Google Sheet URL** - Paste your sheet URL or ID
2. **Enter WordPress URL** - Enter your site URL (e.g., https://yoursite.com)
3. **Wait for Chrome to open** - Look for window with yellow bar saying "Chrome is being controlled by automated test software"

### Step 4: Complete Authentication
In the **automation Chrome window** (with yellow bar):
1. Navigate to your WordPress admin dashboard
2. Complete website login → Jumpcloud SSO → WordPress admin
3. Make sure you reach the WordPress dashboard
4. Press Enter in the terminal when ready

### Step 5: Answer Prompts
- Script will ask about Text Notifications for location-based forms
- Choose 'y' for yes or 'n' for no

### Step 6: Wait for Completion
The script will automatically:
- Find all active forms
- Configure routing rules based on your Google Sheet
- Show progress and completion summary

## 🔄 How It Works

### Smart Form Detection
The script automatically detects two types of forms:

**Forms WITH "Choose A Location" field (Priority)**
- Uses location-based routing
- Selects dealership name from Google Sheet
- Uses corresponding email from same row

**Forms WITH "Dealer ID" field (Fallback)**
- Uses dealer ID routing  
- Uses Feed ID from Google Sheet
- Uses corresponding email from same row

## 🛠 Troubleshooting

### Installation Issues

**"No module named 'X'"**
- Make sure you activated your virtual environment
- Try: `source leadrouter-env/bin/activate`

**Permission errors**
- Try: `pip install --user -r requirements.txt`

**Python not found**
- Download from: https://www.python.org/downloads/
- Make sure Python is in your PATH

### Chrome Issues

**"Version mismatch between Chrome and ChromeDriver"**
1. Update Chrome: Go to `chrome://settings/help`
2. Restart Chrome
3. Restart the script

**"Chrome not found"**
- Make sure Chrome is installed
- Update to latest version: `chrome://settings/help`

### Runtime Issues

**"WARP VPN Blocking Authentication"**
- Completely disable WARP VPN
- Restart authentication

**"WebDriver session is broken"**
- Don't close the automation Chrome window
- Restart script if window was closed

**"Missing or empty values in sheet"**
- Fill all required columns in Google Sheet
- Check for empty cells

**"Forms not found"**
- Make sure you're on WordPress admin dashboard
- Check that Gravity Forms plugin is installed

## 📁 File Structure

```
lead-router/
├── main.py              # Main script
├── requirements.txt     # Dependencies  
├── credentials.json     # Google API credentials (you add this)
├── token.json          # Generated automatically
└── README.md           # This file
```

## ⚠️ Important Notes

- **Use only the automation Chrome window** (with yellow bar)
- **Keep the automation window open** during the process
- **WARP VPN must be OFF** for authentication to work
- **Don't interact with the automation window** while script is running
- **Keep Chrome updated** - Check `chrome://settings/help` regularly

## 🎯 What the Script Does

1. Reads dealership data from your Google Sheet
2. Opens Chrome for automation
3. Waits for you to authenticate manually
4. Finds all active Gravity Forms
5. Configures notification routing rules for each form
6. Uses smart logic to match dealership names with emails
7. Shows detailed progress and completion summary

---

**Ready to automate your form routing? Just follow the steps above!** 