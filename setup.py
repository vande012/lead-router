#!/usr/bin/env python3
"""
Setup script for Lead Router automation tool.
Handles cross-platform and cross-Python-version compatibility.
"""

import sys
import subprocess
import os
from pathlib import Path

def check_python_version():
    """Check if Python version is supported."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python {version.major}.{version.minor} is not supported.")
        print("Please use Python 3.8 or higher.")
        return False
    
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} detected - supported!")
    return True

def install_requirements():
    """Install requirements with error handling."""
    requirements_file = Path(__file__).parent / "requirements.txt"
    
    if not requirements_file.exists():
        print("❌ requirements.txt not found!")
        return False
    
    print("📦 Installing required packages...")
    try:
        # Use --prefer-binary to avoid building from source when possible
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", 
            "--upgrade", "--prefer-binary", 
            "-r", str(requirements_file)
        ])
        print("✅ All packages installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing packages: {e}")
        print("\n🔧 Troubleshooting tips:")
        print("1. Make sure you're using a virtual environment")
        print("2. Try updating pip: python -m pip install --upgrade pip")
        print("3. If using Python 3.13, some packages may need manual installation")
        return False

def create_env_template():
    """Create a .env template file if it doesn't exist."""
    env_file = Path(__file__).parent / ".env"
    env_template = Path(__file__).parent / ".env.template"
    
    template_content = """# Google API Credentials
GOOGLE_CREDENTIALS_FILE=credentials.json
GOOGLE_TOKEN_FILE=token.json

# Chrome/ChromeDriver Paths (adjust for your system)
# macOS default paths:
CHROME_BINARY_PATH=/Applications/Google Chrome.app/Contents/MacOS/Google Chrome
CHROMEDRIVER_PATH=./chrome-for-testing/chromedriver

# Windows paths (uncomment and modify if needed):
# CHROME_BINARY_PATH=C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe
# CHROMEDRIVER_PATH=./chrome-for-testing/chromedriver.exe

# Linux paths (uncomment and modify if needed):
# CHROME_BINARY_PATH=/usr/bin/google-chrome
# CHROMEDRIVER_PATH=./chrome-for-testing/chromedriver
"""
    
    if not env_file.exists():
        with open(env_template, "w") as f:
            f.write(template_content)
        print(f"📝 Created .env.template - please copy to .env and configure your paths")
    else:
        print("✅ .env file already exists")

def main():
    """Main setup function."""
    print("🚀 Lead Router Setup")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Install requirements
    if not install_requirements():
        print("\n⚠️  Installation had issues. You may need to:")
        print("1. Create a virtual environment:")
        print("   python -m venv leadrouter-env")
        print("   source leadrouter-env/bin/activate  # On Windows: leadrouter-env\\Scripts\\activate")
        print("2. Upgrade pip:")
        print("   python -m pip install --upgrade pip")
        print("3. Try installing again:")
        print("   pip install -r requirements.txt")
        sys.exit(1)
    
    # Create environment template
    create_env_template()
    
    print("\n🎉 Setup complete!")
    print("\n📋 Next Run: python main.py")

if __name__ == "__main__":
    main() 