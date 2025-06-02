#!/usr/bin/env python3
"""
Special installation script for Python 3.13 users.
Handles package compatibility issues that may arise with newer Python versions.
"""

import sys
import subprocess
import os
from pathlib import Path

def check_python_313():
    """Check if this is Python 3.13."""
    version = sys.version_info
    if version.major == 3 and version.minor == 13:
        print(f"✅ Python 3.13.{version.micro} detected - using special compatibility mode")
        return True
    else:
        print(f"ℹ️  Python {version.major}.{version.minor}.{version.micro} detected - you may want to use setup.py instead")
        return False

def install_packages_individually():
    """Install packages one by one with better error handling for Python 3.13."""
    packages = [
        "google-auth>=2.0.0",
        "google-auth-oauthlib>=1.0.0", 
        "google-auth-httplib2>=0.1.0",
        "google-api-python-client>=2.86.0",
        "selenium>=4.10.0",
        "python-dotenv>=1.0.0"
    ]
    
    print("📦 Installing packages individually for Python 3.13 compatibility...")
    
    failed_packages = []
    
    for package in packages:
        print(f"\n🔧 Installing {package}...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install",
                "--prefer-binary", "--no-cache-dir",
                package
            ])
            print(f"✅ {package} installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Failed to install {package}: {e}")
            failed_packages.append(package)
            
            # Try alternative installation methods
            print(f"🔄 Trying alternative installation for {package}...")
            try:
                # Try without prefer-binary
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install",
                    "--no-cache-dir", package
                ])
                print(f"✅ {package} installed with alternative method")
                failed_packages.remove(package)
            except subprocess.CalledProcessError:
                print(f"❌ Could not install {package} with any method")
    
    if failed_packages:
        print(f"\n⚠️  Some packages failed to install: {failed_packages}")
        print("This may be due to Python 3.13 compatibility issues.")
        print("\n🔧 Suggested solutions:")
        print("1. Use Python 3.12 instead (recommended)")
        print("2. Wait for package maintainers to release Python 3.13 compatible versions")
        print("3. Try installing from source (advanced users only)")
        return False
    else:
        print("\n✅ All packages installed successfully!")
        return True

def create_virtual_env_instructions():
    """Provide instructions for creating a virtual environment."""
    print("\n📋 For best results with Python 3.13, use a virtual environment:")
    print("1. Create virtual environment:")
    print("   python -m venv leadrouter-py313")
    print("2. Activate it:")
    if os.name == 'nt':  # Windows
        print("   leadrouter-py313\\Scripts\\activate")
    else:  # macOS/Linux
        print("   source leadrouter-py313/bin/activate")
    print("3. Run this script again:")
    print("   python install-python313.py")

def main():
    """Main installation function for Python 3.13."""
    print("🐍 Python 3.13 Installation Script")
    print("=" * 50)
    
    # Check if this is actually Python 3.13
    is_313 = check_python_313()
    
    # Upgrade pip first - crucial for Python 3.13
    print("\n📊 Upgrading pip (essential for Python 3.13)...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "--upgrade", "pip"
        ])
        print("✅ pip upgraded successfully")
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Could not upgrade pip: {e}")
        print("This may cause issues with package installation.")
    
    # Install packages
    if install_packages_individually():
        print("\n🎉 Installation complete!")
        print("\n📋 Next steps:")
        print("1. Configure your .env file")
        print("2. Add your Google credentials.json")
        print("3. Run the script: python main.py")
    else:
        print("\n❌ Installation incomplete")
        if is_313:
            print("\n💡 Python 3.13 is very new. Consider using Python 3.12 for better compatibility:")
            print("1. Install Python 3.12 from python.org")
            print("2. Create virtual environment with Python 3.12")
            print("3. Use the regular setup.py script")
        
        create_virtual_env_instructions()

if __name__ == "__main__":
    main() 