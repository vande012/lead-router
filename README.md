# Lead Router Automation

Automates data entry from Google Sheets into WordPress Gravity Forms to eliminate manual entry of hundreds of CRM and text addresses. Uses Python with Selenium for browser automation and Google APIs for sheet integration.

## 🚨 Important Prerequisites

Before starting, ensure:

- **WARP VPN MUST BE DISABLED** - The script cannot access Jumpcloud SSO with WARP enabled
- **Fresh Chrome Profile Required** - First run creates a new automation profile
- **Manual Authentication** - You must manually complete website login → Jumpcloud SSO → WordPress admin

## 📋 System Requirements

- **Python 3.8+**
- **Google Chrome** (latest version 137)
- **Git**

## 🔧 Installation

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/lead-router.git
cd lead-router
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Verify Pre-Configured Files

✅ **All credentials are pre-configured in this private repo:**
- `credentials.json` - Google Sheets API credentials
- `token.json` - OAuth token for Google authentication  
- `.env` - Environment variables with Chrome paths
- `chrome-for-testing/` - Chrome browser and ChromeDriver

**No additional setup required!** 🎉

## ✅ Pre-Run Checks

Before running the script, verify:

```bash
# Check Python version (3.8+)
python --version

# Check Chrome installation
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --version

# Check ChromeDriver (included in repo)
./chrome-for-testing/chromedriver --version

# Verify WARP VPN is OFF
# Check your system tray/menu bar - WARP must be disconnected

# Verify all required files are present
ls -la credentials.json .env token.json requirements.txt main.py
```

## 🚀 Usage

### 1. Prepare Your Google Sheet

Your sheet must have a tab named **"Combined Feed Info"** with these exact columns:
- `DEALERSHIP NAME`
- `FEED ID` 
- `ADF Email`
- `Text Email`

**⚠️ All cells must be filled** - empty cells will cause the script to abort.

### 2. Run the Script

```bash
python main.py
```

### 3. Provide Required Information

The script will prompt for:
- **Google Sheet URL or ID**
- **WordPress site URL** (e.g., `https://yoursite.com`)

### 4. Manual Authentication (CRITICAL)

🔴 **DISABLE WARP VPN BEFORE THIS STEP**

When the automation Chrome window opens (with yellow bar):

1. **Look for the YELLOW BAR** saying "Chrome is being controlled by automated test software"
2. **Navigate to the WordPress admin URL** shown in terminal (copy/paste - don't click terminal links)
3. **Complete authentication sequence**:
   - Website login credentials
   - Jumpcloud SSO authentication  
   - Reach WordPress admin dashboard
4. **Verify you see** the WordPress admin menu on the left side
5. **Press Enter** in terminal to continue automation

### 5. Automation Process

The script will automatically:
- Navigate to Gravity Forms
- Find all active forms
- Configure ADF/XML and Text notifications for each form
- Set up routing rules based on your sheet data
- Provide progress updates and completion summary

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
    └── chrome-*/         # Chrome for Testing browser
```

## 🔒 Security Notes

- **Private Repository** - All credentials are pre-configured for trusted users
- **Shared Access** - Google Sheets and WordPress access is shared among authorized team members
- **Use the automation Chrome profile only** for this script
- **Fresh profile isolates** automation from your personal browsing
- **WARP VPN must be disabled** during authentication for Jumpcloud SSO access

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