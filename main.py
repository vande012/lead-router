import os
import re
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

import json
import logging
import subprocess
import time
import sys
import threading

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables (for Google credentials)
load_dotenv()

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

def get_sheet_id_from_url(url):
    match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
    if match:
        return match.group(1)
    else:
        return url  # If user just pasted the ID

class LeadRouter:
    def __init__(self, sheet_id, wp_url, headless=True):
        self.google_creds = None
        self.driver = None
        self.headless = headless
        self.sheet_id = sheet_id
        self.wp_url = wp_url
        self.add_text_notifications = None  # Will be set by user prompt
        self.setup_browser()

    def setup_browser(self, port=9222):
        # Use system Chrome directly from environment
        chrome_binary = os.getenv('CHROME_BINARY_PATH', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
        chromedriver_path = os.getenv('CHROMEDRIVER_PATH', './chrome-for-testing/chromedriver')
        user_data_dir = "/tmp/chrome-leadrouter-profile"
        
        # Check if Chrome and chromedriver exist and are executable
        if not os.path.isfile(chrome_binary) or not os.access(chrome_binary, os.X_OK):
            print(f"ERROR: Chrome binary not found or not executable at {chrome_binary}.\nPlease check your CHROME_BINARY_PATH in .env file.")
            sys.exit(1)
        if not os.path.isfile(chromedriver_path) or not os.access(chromedriver_path, os.X_OK):
            print(f"ERROR: ChromeDriver not found or not executable at {chromedriver_path}.\nPlease check your CHROMEDRIVER_PATH in .env file.")
            sys.exit(1)
        
        # Create user data directory if it doesn't exist
        if not os.path.exists(user_data_dir):
            os.makedirs(user_data_dir, exist_ok=True)
            print("Created new Chrome profile for automation.")
        
        print(f"Using Chrome at: {chrome_binary}")
        print(f"Using ChromeDriver at: {chromedriver_path}")
        
        chrome_options = Options()
        chrome_options.binary_location = chrome_binary
        chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_experimental_option("prefs", {
            "profile.default_content_setting_values.images": 2,
            "profile.managed_default_content_settings.javascript": 1,
        })
        service = Service(executable_path=chromedriver_path)
        
        try:
            self.driver = webdriver.Chrome(
                service=service,
                options=chrome_options
            )
        except Exception as e:
            print(f"ERROR: Failed to start Selenium with Chrome: {e}")
            print("If you see a 'user data directory is already in use' error, please close all Chrome windows using this profile and try again.")
            print("If you see a version mismatch error, please update Chrome or ChromeDriver so their versions are compatible.")
            sys.exit(1)
        
        self.driver.implicitly_wait(5)
        
        # Give user instructions for manual navigation
        wp_admin_url = self.wp_url.rstrip('/') + '/wp/wp-admin/'
        print("\n" + "="*60)
        print("MANUAL NAVIGATION REQUIRED")
        print("="*60)
        print("A new Chrome window has opened for automation.")
        print("Look for the window with a YELLOW BAR saying 'Chrome is being controlled by automated test software'")
        print("")
        print("Please complete these steps in the AUTOMATION Chrome window:")
        print(f"1. Navigate to: {wp_admin_url}")
        print("2. Complete all authentication (website login, Jumpcloud SSO, etc.)")
        print("3. Ensure you reach the WordPress admin dashboard")
        print("4. You should see the WordPress menu on the left side")
        print("")
        print("IMPORTANT: Use the automation window (with yellow bar), not your regular Chrome!")
        print("="*60)
        
        def wait_for_enter():
            input("\nPress Enter after you have navigated to the WordPress admin dashboard in the AUTOMATION window...")
        
        t = threading.Thread(target=wait_for_enter)
        t.start()
        t.join(timeout=900)  # 15 minutes for manual navigation
        
        if t.is_alive():
            print("\nTimeout reached. Proceeding with automation...")
            print("If you're not on the WordPress admin dashboard, the automation may fail.")
            t.join(0)
        else:
            print("\nReady to begin automation!")
        
        logger.info(f"Launched Chrome with user data dir {user_data_dir}")
        logger.info(f"User will manually navigate to {wp_admin_url}")

    def setup_google_credentials(self):
        """Set up Google API credentials."""
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
        creds = None
        token_file = os.getenv('GOOGLE_TOKEN_FILE', 'token.json')
        credentials_file = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
        # Load credentials from token file if it exists
        if os.path.exists(token_file):
            with open(token_file, 'r') as token:
                creds = Credentials.from_authorized_user_info(json.load(token), SCOPES)
        # If credentials are not valid, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_file, SCOPES)
                creds = flow.run_local_server(port=8080)
            # Save credentials for future use
            with open(token_file, 'w') as token:
                token.write(creds.to_json())
        self.google_creds = creds

    def read_google_sheet(self):
        """Read data from Google Sheet and extract specific columns with row alignment. Abort if any required value is missing or empty, and summarize all issues."""
        self.setup_google_credentials()
        service = build('sheets', 'v4', credentials=self.google_creds)
        sheet_range = 'Combined Feed Info'  # You can prompt for a specific tab if needed
        try:
            result = service.spreadsheets().values().get(
                spreadsheetId=self.sheet_id, range=sheet_range).execute()
        except Exception as e:
            print(f"Error reading sheet: {e}")
            raise
        values = result.get('values', [])
        logger.info(f"Read {len(values)} rows from Google Sheet.")
        if not values:
            logger.warning("No data found in the sheet.")
            return []
        header = values[0]
        required_cols = ['DEALERSHIP NAME', 'FEED ID', 'ADF Email', 'Text Email']
        col_indices = {}
        for col in required_cols:
            if col in header:
                col_indices[col] = header.index(col)
            else:
                logger.error(f"Required column '{col}' not found in sheet header.")
                return []
        extracted = []
        missing_issues = []
        for i, row in enumerate(values[1:], start=2):
            row_dict = {}
            for col in required_cols:
                idx = col_indices[col]
                value = row[idx] if idx < len(row) else ''
                if value is None or str(value).strip() == '':
                    missing_issues.append(f"Row {i}, Column '{col}' is missing or empty.")
                row_dict[col] = value
            extracted.append(row_dict)
        if missing_issues:
            logger.error("Missing or empty values detected:")
            for issue in missing_issues:
                logger.error(issue)
            print("Error: Missing or empty values detected in the sheet:")
            for issue in missing_issues:
                print(issue)
            logger.error("Aborting due to missing or empty values in the sheet.")
            return []
        logger.info(f"Extracted {len(extracted)} rows with required columns.")
        return extracted

    def prompt_for_text_notifications(self):
        """Ask user if they want to add Text Notifications for inventory forms with location fields"""
        if self.add_text_notifications is None:
            print("\n" + "="*60)
            print("TEXT NOTIFICATIONS CONFIGURATION")
            print("="*60)
            print("For inventory forms that use location-based routing (Choose A Location),")
            print("would you like to also configure Text Notifications?")
            print("")
            while True:
                response = input("Add Text Notifications to location-based forms? (y/n): ").lower().strip()
                if response in ['y', 'yes']:
                    self.add_text_notifications = True
                    print("✓ Text Notifications will be configured for location-based forms")
                    break
                elif response in ['n', 'no']:
                    self.add_text_notifications = False
                    print("✓ Text Notifications will be skipped for location-based forms")
                    break
                else:
                    print("Please enter 'y' for yes or 'n' for no")
            print("="*60)
            
        return self.add_text_notifications

    def check_form_has_dealer_id(self, driver, wait, form_id):
        """Check if a form should use Dealer ID routing or location-based routing.
        Location fields take PRIORITY over Dealer ID fields."""
        try:
            print(f"Checking routing priority for form {form_id}...")
            
            # Navigate to form notifications to check available fields
            notifications_url = f"{self.wp_url.rstrip('/')}/wp/wp-admin/admin.php?page=gf_edit_forms&view=settings&subview=notification&id={form_id}"
            driver.get(notifications_url)
            wait.until(EC.presence_of_element_located((By.LINK_TEXT, "Notifications")))
            
            # Try to find ADF/XML notification to check available routing fields
            notification_selectors = [
                "//a[strong[text()='ADF/XML Formatted Notification']]",
                "//strong[text()='ADF/XML Formatted Notification']/parent::a",
                "//a[contains(@href, 'notification') and contains(., 'ADF/XML Formatted Notification')]"
            ]
            
            notification_link = None
            for selector in notification_selectors:
                try:
                    notification_link = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    break
                except:
                    continue
            
            if not notification_link:
                print(f"Could not find ADF/XML notification for form {form_id} - defaulting to Dealer ID routing")
                return True  # Default to Dealer ID if we can't check
            
            # Click the notification
            notification_link.click()
            
            # Ensure Configure Routing is selected
            try:
                routing_radio = wait.until(EC.presence_of_element_located((By.ID, "gform_notification_to_type_routing")))
                if not routing_radio.is_selected():
                    routing_radio.click()
                    time.sleep(0.5)  # Wait for routing fields to load
            except:
                print(f"Could not find routing option for form {form_id}")
                return True  # Default to Dealer ID if we can't configure routing
            
            # Check available routing fields with LOCATION PRIORITY
            try:
                # Look for the first routing field dropdown
                if_dropdown = driver.find_element(By.ID, "routing_field_id_0")
                from selenium.webdriver.support.ui import Select
                select = Select(if_dropdown)
                
                # Check all available options
                available_options = [option.text for option in select.options]
                print(f"Available routing fields: {available_options}")
                
                # Check for location fields first (PRIORITY)
                location_field_names = [
                    "Choose A Location",
                    "Location", 
                    "Dealership Location",
                    "Store Location",
                    "Dealer Location"
                ]
                
                has_location = False
                location_field_found = None
                for location_name in location_field_names:
                    if location_name in available_options:
                        has_location = True
                        location_field_found = location_name
                        break
                
                # Also check for any field containing "location" in the name
                if not has_location:
                    for option in available_options:
                        if "location" in option.lower():
                            has_location = True
                            location_field_found = option
                            break
                
                has_dealer_id = "Dealer ID" in available_options
                
                print(f"Form {form_id} field analysis:")
                print(f"  - Has location field: {has_location} ({'(' + location_field_found + ')' if location_field_found else ''})")
                print(f"  - Has Dealer ID field: {has_dealer_id}")
                
                # PRIORITY LOGIC: Location fields take precedence over Dealer ID
                if has_location:
                    print(f"  ➤ USING LOCATION-BASED ROUTING (Priority: {location_field_found})")
                    return False  # Return False to indicate "don't use Dealer ID routing"
                elif has_dealer_id:
                    print(f"  ➤ USING DEALER-ID-BASED ROUTING (No location field found)")
                    return True   # Return True to indicate "use Dealer ID routing"
                else:
                    print(f"  ➤ WARNING: Neither location nor Dealer ID field found - defaulting to Dealer ID")
                    return True   # Default to Dealer ID if neither is found
                
            except Exception as e:
                print(f"Could not check routing fields for form {form_id}: {e}")
                return True  # Default to Dealer ID if we can't check
                
        except Exception as e:
            print(f"Error checking form {form_id} routing priority: {e}")
            return True  # Default to Dealer ID if we can't check

    def automate_form_notifications(self, sheet_data):
        """
        Automate Gravity Forms notification routing rules for ADF/XML Formatted Notification.
        Only implements ADF/XML for now, using 'ADF Email' from sheet_data.
        """
        print("Starting form automation...")
        driver = self.driver
        wait = WebDriverWait(driver, 10)
        logger.info("Starting automation of ADF/XML Formatted Notification.")

        # Import Select at function level so it's available everywhere
        from selenium.webdriver.support.ui import Select

        try:
            # Check if WebDriver session is still alive
            print("Validating WebDriver session...")
            try:
                # Test basic WebDriver functionality
                window_handles = driver.window_handles
                print(f"WebDriver has {len(window_handles)} window(s)")
                
                # If we have windows, make sure we're using the right one
                if window_handles:
                    print("Switching to the main browser window...")
                    driver.switch_to.window(window_handles[0])
                    time.sleep(1)  # Give it a moment to switch
                
                # Try to get basic browser info
                try:
                    current_url = driver.current_url
                    print(f"Current URL: {current_url}")
                    logger.info(f"Current URL: {current_url}")
                except Exception as e:
                    print(f"ERROR: Cannot get current URL - WebDriver session may be broken: {e}")
                    print("\nPossible causes:")
                    print("1. The automation browser window was closed")
                    print("2. You're using a different Chrome window")
                    print("3. The browser lost connection to the automation script")
                    print("\nSolution: Restart the script and use the NEW automation window (with yellow bar)")
                    return
                
                # Check if we have a valid URL
                if not current_url or current_url == "None" or current_url == "data:,":
                    print("ERROR: No valid page loaded in browser.")
                    print("The automation window shows a blank page or new tab.")
                    print("Please navigate to your WordPress admin dashboard in the AUTOMATION window.")
                    print("Current URL shows:", repr(current_url))
                    return
                    
            except Exception as e:
                print(f"ERROR: WebDriver session is broken: {e}")
                print("\nTo fix this issue:")
                print("1. Make sure the automation Chrome window (with yellow bar) stays open")
                print("2. Don't close or switch away from the automation window")
                print("3. Restart the script to create a fresh browser session")
                return
            
            # Check if we're on a WordPress admin page
            if "wp-admin" not in current_url.lower():
                print("ERROR: Not on WordPress admin page.")
                print(f"Current page: {current_url}")
                print("Please manually navigate to the WordPress admin dashboard.")
                return
            
            print("WordPress admin page detected. Looking for Forms menu...")
            
            # Look for Forms menu with a simple approach first
            logger.info("Looking for Forms menu...")
            try:
                # Try the most common selector first
                forms_menu = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'wp-menu-name') and text()='Forms']")))
                print("Found Forms menu!")
                logger.info("Found Forms menu with primary selector")
            except Exception as e:
                print("Primary selector failed, trying alternatives...")
                logger.info(f"Primary selector failed: {e}")
                
                # Try alternative selectors
                selectors = [
                    "//a[contains(@href, 'gf_edit_forms')]",
                    "//div[@class='wp-menu-name'][text()='Forms']",
                    "//*[contains(text(), 'Forms') and contains(@class, 'menu')]"
                ]
                
                forms_menu = None
                for i, selector in enumerate(selectors):
                    try:
                        print(f"Trying alternative selector {i+1}...")
                        forms_menu = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                        print(f"Found Forms menu with alternative selector {i+1}!")
                        logger.info(f"Found Forms menu with selector {i+1}")
                        break
                    except Exception:
                        continue
                
                if not forms_menu:
                    print("ERROR: Could not find Forms menu.")
                    print("Please check:")
                    print("1. Are you on the WordPress admin dashboard?")
                    print("2. Is Gravity Forms plugin installed and activated?")
                    print("3. Do you have permission to access Forms?")
                    
                    # Try to list available menu items for debugging
                    try:
                        menu_items = driver.find_elements(By.XPATH, "//div[@class='wp-menu-name']")
                        print("Available menu items:")
                        for item in menu_items:
                            try:
                                print(f"  - {item.text}")
                            except:
                                pass
                    except Exception as e:
                        print(f"Could not list menu items: {e}")
                    
                    return

            # Click Forms menu
            print("Clicking Forms menu...")
            forms_menu.click()
            
            # Look for Forms submenu
            try:
                print("Looking for Forms submenu...")
                forms_submenu = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Forms")))
                forms_submenu.click()
                print("Clicked Forms submenu")
            except Exception as e:
                print("Could not find Forms submenu, might already be on Forms page")
                logger.warning(f"Could not find Forms submenu: {e}")

            # Continue with the rest of the automation...
            logger.info("Looking for active forms...")
            
            # Navigate directly to active forms page
            print("Navigating directly to active forms...")
            active_forms_url = f"{self.wp_url.rstrip('/')}/wp/wp-admin/admin.php?page=gf_edit_forms&active=1"
            driver.get(active_forms_url)
            
            # Wait for either the page to complete loading or 10 seconds max
            try:
                WebDriverWait(driver, 10).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
            except TimeoutException:
                print("Page load took too long, proceeding anyway")

            # Then look for just the critical element we need
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".wp-list-table"))
                )
                print("Active forms page loaded")
            except TimeoutException:
                print("Forms table not found but proceeding anyway")
            
            # Now find all forms with a simpler, more reliable approach
            print("Finding forms on the page...")
            all_forms = []
            
            # Try the most reliable selector first - just look for edit links
            try:
                all_forms = driver.find_elements(By.XPATH, "//a[contains(@href, 'page=gf_edit_forms') and contains(@href, 'id=') and not(contains(@href, 'view='))]")
                print(f"Found {len(all_forms)} forms with primary selector")
            except Exception as e:
                print(f"Primary form selector failed: {e}")
            
            # If that didn't work, try a broader search
            if not all_forms:
                try:
                    print("Trying alternative form selector...")
                    all_forms = driver.find_elements(By.XPATH, "//table//a[contains(@href, 'id=') and contains(text(), '') and not(contains(@href, 'view='))]")
                    print(f"Found {len(all_forms)} forms with alternative selector")
                except Exception as e:
                    print(f"Alternative form selector failed: {e}")
            
            # Get all form IDs and titles at the start
            all_form_info = []
            for form_link in all_forms:
                try:
                    form_title = form_link.text.strip()
                    form_href = form_link.get_attribute('href')
                    
                    # Extract form ID from the href
                    import re
                    form_id_match = re.search(r'[?&]id=(\d+)', form_href)
                    form_id = form_id_match.group(1) if form_id_match else None
                    
                    if form_id and form_title:
                        all_form_info.append({
                            'id': form_id,
                            'title': form_title,
                            'href': form_href
                        })
                except Exception as e:
                    print(f"Error getting form info: {e}")
                    continue
            
            total_forms = len(all_form_info)
            logger.info(f"Found {total_forms} active forms to process.")
            print(f"Found {total_forms} active forms to process:")
            for i, form_info in enumerate(all_form_info):
                print(f"  {i+1}. {form_info['title']} (ID: {form_info['id']})")
            
            if total_forms == 0:
                print("No forms found to process. Please check:")
                print("1. Are there any active forms?")
                print("2. Is the forms page loaded correctly?")
                return

            # Track completed forms by ID
            completed_form_ids = set()
            forms_with_errors = []  # Track forms that had errors but were still processed
            skipped_forms = []  # Track forms that were skipped due to missing fields
            
            # Process each form by ID
            for form_index, form_info in enumerate(all_form_info):
                try:
                    form_id = form_info['id']
                    form_title = form_info['title']
                    
                    # Skip if already completed
                    if form_id in completed_form_ids:
                        print(f"Skipping form {form_index + 1}: {form_title} (ID: {form_id}) - already completed")
                        continue
                    
                    print(f"\n--- Processing Form {form_index + 1} of {total_forms} ---")
                    print(f"Form: {form_title} (ID: {form_id})")
                    
                    # Navigate directly to the form using its ID
                    form_url = f"{self.wp_url.rstrip('/')}/wp/wp-admin/admin.php?page=gf_edit_forms&id={form_id}"
                    driver.get(form_url)
                    
                    # Wait for the form to load
                    try:
                        wait.until(EC.presence_of_element_located((By.LINK_TEXT, "Form Settings")))
                    except Exception as e:
                        print(f"Form {form_id} did not load properly: {e}")
                        continue

                    # Check if this form has Dealer ID field available
                    has_dealer_id = self.check_form_has_dealer_id(driver, wait, form_id)
                    use_location_routing = not has_dealer_id
                    
                    if use_location_routing:
                        print(f"✓ Form {form_id} will use LOCATION-BASED routing (Choose A Location)")
                        print(f"  - Field: Choose A Location")
                        print(f"  - Condition: IS")  
                        print(f"  - Value: Dealership Name from sheet")
                        print(f"  - Email: Corresponding email from dropdown menu")
                    else:
                        print(f"✓ Form {form_id} will use DEALER-ID-BASED routing (standard)")
                        print(f"  - Field: Dealer ID")
                        print(f"  - Condition: IS")
                        print(f"  - Value: Feed ID from sheet")

                    # Go to Form Settings > Notifications
                    driver.find_element(By.LINK_TEXT, "Form Settings").click()
                    wait.until(EC.presence_of_element_located((By.LINK_TEXT, "Notifications")))
                    driver.find_element(By.LINK_TEXT, "Notifications").click()

                    # Track results for this form
                    form_skipped = False
                    form_failed = False
                    
                    # Process ADF/XML notification first
                    adf_result = self._process_notification(driver, wait, sheet_data, "ADF/XML Formatted Notification", "ADF Email", form_title, form_id, Select, use_location_routing)
                    if adf_result == "skipped":
                        form_skipped = True
                    elif adf_result == "failed":
                        form_failed = True
                    
                    # Process Text notification second (only if ADF didn't fail/skip)
                    if not form_skipped and not form_failed:
                        text_result = self._process_notification(driver, wait, sheet_data, "Text Formatted Notification", "Text Email", form_title, form_id, Select, use_location_routing)
                        if text_result == "skipped":
                            form_skipped = True
                        elif text_result == "failed":
                            form_failed = True
                    
                    # Categorize the form based on results
                    if form_skipped:
                        print(f"⏭️  Skipped form (missing required fields): {form_title} (ID: {form_id})")
                        skipped_forms.append({'id': form_id, 'title': form_title})
                    elif form_failed:
                        print(f"❌ Failed to process form: {form_title} (ID: {form_id})")
                        # Don't add to any completion list - this is a true failure
                    else:
                        # Mark this form as completed successfully
                        completed_form_ids.add(form_id)
                        print(f"✓ Successfully completed form: {form_title} (ID: {form_id})")
                    
                    # Only navigate back if we have more forms to process and this form wasn't skipped/failed
                    remaining_forms = [f for f in all_form_info if f['id'] not in completed_form_ids and f['id'] not in [sf['id'] for sf in skipped_forms]]
                    if remaining_forms and not form_skipped and not form_failed:
                        print(f"Returning to forms list... ({len(remaining_forms)} forms remaining)")
                        
                        # Check if we're already on the forms page before attempting navigation
                        try:
                            current_url = driver.current_url
                            if 'page=gf_edit_forms' in current_url:
                                print("Already on forms page - no navigation needed")
                                time.sleep(0.5)  # Brief pause to ensure page is stable
                            else:
                                # Only navigate if we're not already there
                                forms_list_url = self.wp_url.rstrip('/') + '/wp/wp-admin/admin.php?page=gf_edit_forms&active=1'
                                print(f"Navigating to forms list from: {current_url}")
                                driver.get(forms_list_url)
                                
                                # Quick check that navigation worked
                                try:
                                    wait.until(EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), 'Forms')]")))
                                    print("Successfully navigated to forms list")
                                    time.sleep(1)  # Allow page to stabilize
                                except Exception:
                                    # If wait fails, just check if we're actually on the right page
                                    final_url = driver.current_url
                                    if 'page=gf_edit_forms' in final_url:
                                        print("Navigation succeeded despite wait timeout")
                                    else:
                                        print(f"Navigation may have failed - current URL: {final_url}")
                        
                        except Exception as nav_error:
                            print(f"Navigation check failed: {nav_error}")
                            # Try to continue anyway
                            try:
                                current_url = driver.current_url
                                if 'page=gf_edit_forms' in current_url:
                                    print("On forms page despite navigation error - continuing...")
                                else:
                                    print(f"Not on forms page after error - URL: {current_url}")
                            except:
                                print("Could not determine current page state")
                        
                    else:
                        if form_skipped or form_failed:
                            print("Form was skipped/failed - moving to next form")
                        else:
                            print("No more forms to process - skipping navigation back")
                    
                except Exception as e:
                    # Enhanced error reporting
                    error_msg = str(e) if str(e).strip() else "Unknown WebDriver error"
                    print(f"✗ Error processing form {form_index + 1} ({form_title}, ID: {form_id}): {error_msg}")
                    logger.error(f"Error processing form {form_index + 1} ({form_title}): {error_msg}")
                    
                    # Try to recover gracefully
                    print("Attempting to recover from error...")
                    try:
                        # Check if WebDriver session is still alive
                        current_url = driver.current_url
                        print(f"Current URL after error: {current_url}")
                        
                        # Try to get back to forms list
                        driver.get(self.wp_url.rstrip('/') + '/wp/wp-admin/admin.php?page=gf_edit_forms&active=1')
                        wait.until(EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), 'Forms')]")))
                        print("Successfully recovered to forms list")
                        time.sleep(1)
                        
                    except Exception as recovery_error:
                        print(f"Recovery failed: {recovery_error}")
                        print("WebDriver session may be broken. Consider restarting the script.")
                        break  # Exit the loop if we can't recover
                    
                    continue  # Continue with next form
            
            # Final summary
            print(f"\n" + "="*60)
            print("AUTOMATION COMPLETE")
            print("="*60)
            print(f"Total forms found: {total_forms}")
            print(f"Successfully processed: {len(completed_form_ids)}")
            print(f"Skipped (missing fields): {len(skipped_forms)}")
            print(f"Failed: {total_forms - len(completed_form_ids) - len(skipped_forms)}")
            print("")
            
            if completed_form_ids:
                print("✅ SUCCESSFULLY PROCESSED FORMS:")
                for form_info in all_form_info:
                    if form_info['id'] in completed_form_ids:
                        print(f"  ✓ {form_info['title']} (ID: {form_info['id']})")
            
            if skipped_forms:
                print(f"\n⏭️  SKIPPED FORMS ({len(skipped_forms)} total):")
                print("These forms were skipped because required fields were not available:")
                for skipped_form in skipped_forms:
                    print(f"  • {skipped_form['title']} (ID: {skipped_form['id']})")
                print("\nReasons forms get skipped:")
                print("  - No 'Dealer ID' field found (for dealer-id-based routing)")
                print("  - No 'Choose A Location' or location field found (for location-based routing)")
                print("  - Form structure doesn't support the required routing type")
            
            failed_forms = [f for f in all_form_info if f['id'] not in completed_form_ids and f['id'] not in [sf['id'] for sf in skipped_forms]]
            if failed_forms:
                print(f"\n❌ FAILED FORMS ({len(failed_forms)} total):")
                print("These forms encountered errors during processing:")
                for form_info in failed_forms:
                    print(f"  • {form_info['title']} (ID: {form_info['id']})")
                print("\nCommon causes of form failures:")
                print("  - WordPress/Gravity Forms interface errors")
                print("  - Network connectivity issues")
                print("  - Unexpected form structure changes")
                print("  - Browser automation errors")
            
            print(f"\n{'='*60}")
            
            if len(completed_form_ids) == total_forms:
                print("🎉 ALL FORMS PROCESSED SUCCESSFULLY!")
            elif len(completed_form_ids) > 0:
                processed_count = len(completed_form_ids)
                skipped_count = len(skipped_forms)
                failed_count = len(failed_forms)
                
                if skipped_count > 0 and failed_count == 0:
                    print(f"✅ PARTIAL SUCCESS: {processed_count}/{total_forms} forms completed")
                    print(f"   ({skipped_count} forms skipped due to missing required fields)")
                elif failed_count > 0 and skipped_count == 0:
                    print(f"⚠️  PARTIAL SUCCESS: {processed_count}/{total_forms} forms completed")
                    print(f"   ({failed_count} forms failed due to errors)")
                elif skipped_count > 0 and failed_count > 0:
                    print(f"⚠️  PARTIAL SUCCESS: {processed_count}/{total_forms} forms completed")
                    print(f"   ({skipped_count} skipped, {failed_count} failed)")
                else:
                    print(f"✅ SUCCESS: {processed_count}/{total_forms} forms completed")
            else:
                print("❌ NO FORMS COMPLETED")
                if len(skipped_forms) > 0:
                    print(f"   All {len(skipped_forms)} forms were skipped due to missing required fields")
                if len(failed_forms) > 0:
                    print(f"   {len(failed_forms)} forms failed due to errors")
            
            print("="*60)
                    
        except Exception as e:
            driver.save_screenshot("debug_automation_error.png")
            logger.error(f"Error during form notification automation: {e}")
            print(f"ERROR during automation: {e}")
            print("Debug screenshot saved: debug_automation_error.png")
            import traceback
            traceback.print_exc()

    def _process_notification(self, driver, wait, sheet_data, notification_name, email_column, form_title, form_id, Select, use_location_routing=False):
        """Helper method to process a single notification type"""
        try:
            # For location-based routing, ask user about Text Notifications
            if use_location_routing and notification_name == "Text Formatted Notification":
                if not self.prompt_for_text_notifications():
                    print(f"Skipping {notification_name} for location-based form as requested by user")
                    return "skipped"
            
            # 3c. Find and click the notification link directly
            print(f"Looking for {notification_name} link...")
            notification_link = None
            
            # Try multiple ways to find the notification link based on actual HTML structure
            selectors = [
                f"//a[strong[text()='{notification_name}']]",
                f"//strong[text()='{notification_name}']/parent::a",
                f"//a[contains(@href, 'notification') and contains(., '{notification_name}')]",
                f"//a[strong[contains(text(), '{notification_name}')]]",
                f"//strong[contains(text(), '{notification_name}')]/parent::a"
            ]
            
            for i, selector in enumerate(selectors):
                try:
                    print(f"Trying notification link selector {i+1}: {selector}")
                    notification_link = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    print(f"Found {notification_name} notification link with selector {i+1}")
                    break
                except Exception as e:
                    print(f"Selector {i+1} failed: {e}")
                    continue
            
            if not notification_link:
                print(f"Could not find {notification_name} notification link.")
                print(f"Available {notification_name} links on this page:")
                try:
                    # List all notification links for debugging
                    notification_links = driver.find_elements(By.XPATH, "//table//a[strong]")
                    for link in notification_links:
                        try:
                            link_text = link.text.strip()
                            if link_text:
                                print(f"  - {link_text}")
                        except:
                            pass
                    
                    # Also check for links with href containing 'notification'
                    print(f"Links with '{notification_name}' in href:")
                    notif_href_links = driver.find_elements(By.XPATH, f"//a[contains(@href, 'notification') and contains(text(), '{notification_name}')]")
                    for link in notif_href_links:
                        try:
                            link_text = link.text.strip()
                            if link_text:
                                print(f"  - {link_text}")
                        except:
                            pass
                except Exception as e:
                    print(f"Could not list {notification_name} links: {e}")
                return "failed"
            
            print(f"Clicking {notification_name} notification link...")
            notification_link.click()

            # 3d. Ensure 'Configure Routing' is selected
            print(f"Checking if Configure Routing is selected for {notification_name}...")
            try:
                routing_radio = wait.until(EC.presence_of_element_located((By.ID, f"gform_notification_to_type_routing")))
                if not routing_radio.is_selected():
                    print(f"Selecting Configure Routing for {notification_name}...")
                    routing_radio.click()
                    time.sleep(0.5)  # Wait for routing options to load
                else:
                    print(f"{notification_name} Configure Routing is already selected")
            except Exception as e:
                print(f"Could not find Configure Routing radio button for {notification_name}: {e}")
                return "failed"

            # Check if required fields are available before processing
            print(f"Checking if required fields are available for {notification_name}...")
            try:
                # Check the first routing field dropdown to see what's available
                if_dropdown = driver.find_element(By.ID, "routing_field_id_0")
                from selenium.webdriver.support.ui import Select
                select = Select(if_dropdown)
                available_options = [option.text.strip() for option in select.options if option.text.strip()]
                
                print(f"Available routing fields: {available_options}")
                
                # Check for required fields based on routing type
                if use_location_routing:
                    # Check for location fields
                    location_fields = ["Choose A Location", "Location", "Dealership Location", "Store Location", "Dealer Location"]
                    has_location_field = any(field in available_options for field in location_fields)
                    
                    if not has_location_field:
                        # Also check for any field containing "location"
                        has_location_field = any("location" in opt.lower() for opt in available_options)
                    
                    if not has_location_field:
                        print(f"❌ SKIPPING FORM: No location field found for {notification_name}")
                        print(f"   Required: One of {location_fields} or field containing 'location'")
                        print(f"   Available: {available_options}")
                        return "skipped"
                else:
                    # Check for Dealer ID field
                    dealer_id_fields = ["Dealer ID", "Dealership ID", "Dealer", "ID"]
                    has_dealer_id_field = any(field in available_options for field in dealer_id_fields)
                    
                    if not has_dealer_id_field:
                        print(f"❌ SKIPPING FORM: No Dealer ID field found for {notification_name}")
                        print(f"   Required: One of {dealer_id_fields}")
                        print(f"   Available: {available_options}")
                        return "skipped"
                
                print(f"✓ Required fields are available for {notification_name}")
                
            except Exception as e:
                print(f"Error checking available fields for {notification_name}: {e}")
                return "failed"

            # 3e. Fill blank rules first, then add new ones if needed
            print(f"Configuring {notification_name} routing rules...")
            routing_type = "location-based" if use_location_routing else "dealer-id-based"
            print(f"Using {routing_type} routing strategy")
            
            try:
                # Find all existing email fields and check which are blank
                all_email_fields = driver.find_elements(By.XPATH, f"//input[starts-with(@id, 'routing_email_')]")
                existing_count = len(all_email_fields)
                needed_count = len(sheet_data)
                
                print(f"Found {existing_count} existing rule slots")
                print(f"Need to configure {needed_count} rules")
                
                # Check which existing rules are blank or incomplete
                blank_rules = []
                filled_rules = []
                
                for i in range(existing_count):
                    try:
                        email_field = driver.find_element(By.ID, f"routing_email_{i}")
                        value_field = driver.find_element(By.ID, f"routing_value_{i}")
                        
                        email_value = email_field.get_attribute('value').strip()
                        routing_value = value_field.get_attribute('value').strip()
                        
                        if not email_value or not routing_value:
                            blank_rules.append(i)
                            print(f"  Rule {i} is blank/incomplete")
                        else:
                            filled_rules.append(i)
                            print(f"  Rule {i} is already filled: {email_value}")
                    except:
                        blank_rules.append(i)  # If we can't find fields, consider it blank
                
                print(f"Found {len(blank_rules)} blank rules, {len(filled_rules)} filled rules")
                
                # Fill blank rules first with our data
                data_index = 0
                rules_configured = 0
                
                print(f"Filling blank rules with our data...")
                for rule_index in blank_rules:
                    if data_index >= needed_count:
                        break  # No more data to fill
                        
                    row = sheet_data[data_index]
                    print(f"Filling blank rule {rule_index} with: {row['DEALERSHIP NAME']} -> {row[email_column]}")
                    
                    try:
                        # Fill email field
                        email_field = driver.find_element(By.ID, f"routing_email_{rule_index}")
                        email_field.clear()
                        email_field.send_keys(row[email_column])
                        
                        # Set dropdown fields based on routing type
                        if_dropdown = driver.find_element(By.ID, f"routing_field_id_{rule_index}")
                        
                        if use_location_routing:
                            # Use location-based routing - try priority fields first
                            location_field_names = ["Choose A Location", "Location", "Dealership Location", "Store Location", "Dealer Location"]
                            
                            field_selected = False
                            for location_name in location_field_names:
                                try:
                                    Select(if_dropdown).select_by_visible_text(location_name)
                                    field_selected = True
                                    print(f"  ✓ Selected location field: {location_name}")
                                    break
                                except:
                                    continue
                            
                            # If none of the priority fields worked, try any field containing "location"
                            if not field_selected:
                                select_obj = Select(if_dropdown)
                                for option in select_obj.options:
                                    if "location" in option.text.lower():
                                        try:
                                            select_obj.select_by_visible_text(option.text)
                                            field_selected = True
                                            print(f"  ✓ Selected location field: {option.text}")
                                            break
                                        except:
                                            continue
                        else:
                            # Use dealer ID routing - try priority fields first
                            dealer_id_fields = ["Dealer ID", "Dealership ID", "Dealer", "ID"]
                            
                            field_selected = False
                            for dealer_field in dealer_id_fields:
                                try:
                                    Select(if_dropdown).select_by_visible_text(dealer_field)
                                    field_selected = True
                                    print(f"  ✓ Selected dealer field: {dealer_field}")
                                    break
                                except:
                                    continue
                        
                        is_dropdown = driver.find_element(By.ID, f"routing_operator_{rule_index}")
                        Select(is_dropdown).select_by_visible_text("is")
                        
                        value_field = driver.find_element(By.ID, f"routing_value_{rule_index}")
                        
                        if use_location_routing:
                            # For location routing, use dealership name from Google Sheet
                            dealership_name = row['DEALERSHIP NAME']
                            corresponding_email = row[email_column]
                            
                            print(f"  Looking for dealership: '{dealership_name}' (email: {corresponding_email})")
                            
                            # Ensure the value field is visible and interactable
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", value_field)
                            time.sleep(0.5)
                            
                            # Try to select the dealership name from dropdown
                            try:
                                # Wait for element to be clickable and check if it's a select element
                                wait.until(EC.element_to_be_clickable(value_field))
                                
                                if value_field.tag_name.lower() == 'select':
                                    # It's a dropdown - use Select
                                    value_dropdown = Select(value_field)
                                    available_options = []
                                    
                                    # Get all option texts safely
                                    for option in value_dropdown.options:
                                        option_text = option.text.strip()
                                        if option_text:  # Only add non-empty options
                                            available_options.append(option_text)
                                    
                                    print(f"  Available location options ({len(available_options)}): {available_options[:10]}{'...' if len(available_options) > 10 else ''}")
                                    
                                    # First priority: Try to find exact dealership name match
                                    dealership_found = False
                                    for option_text in available_options:
                                        if option_text == dealership_name:
                                            try:
                                                value_dropdown.select_by_visible_text(option_text)
                                                print(f"  ✓ Selected exact dealership match: '{option_text}'")
                                                dealership_found = True
                                                break
                                            except Exception as select_error:
                                                print(f"  ! Error selecting exact match '{option_text}': {select_error}")
                                                continue
                                    
                                    # Second priority: Try partial dealership name match
                                    if not dealership_found:
                                        for option_text in available_options:
                                            if (dealership_name.lower() in option_text.lower() or 
                                                option_text.lower() in dealership_name.lower()):
                                                try:
                                                    value_dropdown.select_by_visible_text(option_text)
                                                    print(f"  ✓ Selected partial dealership match: '{option_text}' (for '{dealership_name}')")
                                                    dealership_found = True
                                                    break
                                                except Exception as select_error:
                                                    print(f"  ! Error selecting partial match '{option_text}': {select_error}")
                                                    continue
                                    
                                    # Third priority: Try to find the corresponding email in dropdown
                                    if not dealership_found:
                                        for option_text in available_options:
                                            if corresponding_email.lower() in option_text.lower():
                                                try:
                                                    value_dropdown.select_by_visible_text(option_text)
                                                    print(f"  ✓ Selected email match in dropdown: '{option_text}'")
                                                    dealership_found = True
                                                    break
                                                except Exception as select_error:
                                                    print(f"  ! Error selecting email match '{option_text}': {select_error}")
                                                    continue
                                    
                                    # If nothing found, warn user but don't change selection
                                    if not dealership_found:
                                        print(f"  ⚠️  WARNING: Could not find '{dealership_name}' in dropdown options")
                                        print(f"  ⚠️  Available options (first 10): {available_options[:10]}")
                                        print(f"  ⚠️  Leaving current selection unchanged")
                                        
                                else:
                                    # It's a text field, not dropdown - clear and type the dealership name
                                    value_field.clear()
                                    value_field.send_keys(dealership_name)
                                    print(f"  ✓ Entered dealership name in text field: '{dealership_name}'")
                                    
                            except Exception as dropdown_error:
                                print(f"  ! Error interacting with value field: {dropdown_error}")
                                # Try fallback approach - clear and type
                                try:
                                    value_field.clear()
                                    value_field.send_keys(dealership_name)
                                    print(f"  ✓ Fallback: Entered dealership name as text: '{dealership_name}'")
                                except Exception as fallback_error:
                                    print(f"  ✗ Fallback also failed: {fallback_error}")
                        else:
                            # Use Feed ID for Dealer ID routing
                            value_field.clear()
                            value_field.send_keys(row['FEED ID'])
                        
                        # Verify the fields were actually populated
                        time.sleep(0.2)  # Brief pause for field updates
                        actual_email = email_field.get_attribute('value')
                        actual_value = value_field.get_attribute('value')
                        
                        if actual_email != row[email_column]:
                            print(f"  ! Warning: Email field shows '{actual_email}' instead of '{row[email_column]}'")
                        
                        expected_value = row['DEALERSHIP NAME'] if use_location_routing else row['FEED ID']
                        if actual_value != expected_value:
                            print(f"  ! Warning: Value field shows '{actual_value}' instead of '{expected_value}'")
                            # Try again if it didn't work
                            value_field.clear()
                            if use_location_routing:
                                value_field.send_keys(row['DEALERSHIP NAME'])
                            else:
                                value_field.send_keys(row['FEED ID'])
                            time.sleep(0.1)
                            actual_value = value_field.get_attribute('value')
                            print(f"  ! Retry result: Value field now shows '{actual_value}'")
                        
                        print(f"  ✓ Filled rule {rule_index}: Email='{actual_email}', Value='{actual_value}'")
                        rules_configured += 1
                        data_index += 1
                        
                    except Exception as e:
                        print(f"  ✗ Error filling rule {rule_index}: {e}")
                        data_index += 1  # Skip this data row
                        continue
                
                # If we still have more data, create new rules
                remaining_data = needed_count - data_index
                if remaining_data > 0:
                    print(f"Creating {remaining_data} new rules for remaining data...")
                    
                    for i in range(remaining_data):
                        if data_index >= needed_count:
                            break
                            
                        row = sheet_data[data_index]
                        print(f"Creating new rule for: {row['DEALERSHIP NAME']} -> {row[email_column]}")
                        
                        # Add a new rule
                        try:
                            add_buttons = driver.find_elements(By.XPATH, "//a[contains(@onclick, 'InsertRouting')]")
                            if add_buttons:
                                last_add_button = add_buttons[-1]
                                
                                # Scroll to the add button and try to clear any overlays
                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", last_add_button)
                                time.sleep(0.3)
                                
                                # Try to dismiss WordPress admin bar if it's covering the button
                                try:
                                    driver.execute_script("window.scrollBy(0, -50);")  # Scroll up a bit
                                    time.sleep(0.2)
                                except:
                                    pass
                                
                                # Try regular click first
                                click_successful = False
                                try:
                                    last_add_button.click()
                                    click_successful = True
                                except Exception as e:
                                    print(f"    Regular click failed: {e}")
                                    
                                    # Try JavaScript click as fallback
                                    try:
                                        driver.execute_script("arguments[0].click();", last_add_button)
                                        click_successful = True
                                        print("    JavaScript click succeeded")
                                    except Exception as e2:
                                        print(f"    JavaScript click also failed: {e2}")
                                
                                if click_successful:
                                    time.sleep(0.5)
                                    
                                    # Calculate the new rule index
                                    new_rule_index = existing_count + i
                                    
                                    # Fill the new rule
                                    email_field = driver.find_element(By.ID, f"routing_email_{new_rule_index}")
                                    email_field.clear()
                                    email_field.send_keys(row[email_column])
                                    
                                    if_dropdown = driver.find_element(By.ID, f"routing_field_id_{new_rule_index}")
                                    
                                    if use_location_routing:
                                        # Use location-based routing - try priority fields first
                                        location_field_names = ["Choose A Location", "Location", "Dealership Location", "Store Location", "Dealer Location"]
                                        
                                        field_selected = False
                                        for location_name in location_field_names:
                                            try:
                                                Select(if_dropdown).select_by_visible_text(location_name)
                                                field_selected = True
                                                print(f"  ✓ Selected location field: {location_name}")
                                                break
                                            except:
                                                continue
                                        
                                        # If none of the priority fields worked, try any field containing "location"
                                        if not field_selected:
                                            select_obj = Select(if_dropdown)
                                            for option in select_obj.options:
                                                if "location" in option.text.lower():
                                                    try:
                                                        select_obj.select_by_visible_text(option.text)
                                                        field_selected = True
                                                        print(f"  ✓ Selected location field: {option.text}")
                                                        break
                                                    except:
                                                        continue
                                    else:
                                        # Use dealer ID routing - try priority fields first
                                        dealer_id_fields = ["Dealer ID", "Dealership ID", "Dealer", "ID"]
                                        
                                        field_selected = False
                                        for dealer_field in dealer_id_fields:
                                            try:
                                                Select(if_dropdown).select_by_visible_text(dealer_field)
                                                field_selected = True
                                                print(f"  ✓ Selected dealer field: {dealer_field}")
                                                break
                                            except:
                                                continue
                                    
                                    is_dropdown = driver.find_element(By.ID, f"routing_operator_{new_rule_index}")
                                    Select(is_dropdown).select_by_visible_text("is")
                                    
                                    value_field = driver.find_element(By.ID, f"routing_value_{new_rule_index}")
                                    
                                    if use_location_routing:
                                        # For location routing, use dealership name from Google Sheet
                                        dealership_name = row['DEALERSHIP NAME']
                                        corresponding_email = row[email_column]
                                        
                                        print(f"  Looking for dealership: '{dealership_name}' (email: {corresponding_email})")
                                        
                                        # Ensure the value field is visible and interactable
                                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", value_field)
                                        time.sleep(0.5)
                                        
                                        # Try to select the dealership name from dropdown
                                        try:
                                            # Wait for element to be clickable and check if it's a select element
                                            wait.until(EC.element_to_be_clickable(value_field))
                                            
                                            if value_field.tag_name.lower() == 'select':
                                                # It's a dropdown - use Select
                                                value_dropdown = Select(value_field)
                                                available_options = []
                                                
                                                # Get all option texts safely
                                                for option in value_dropdown.options:
                                                    option_text = option.text.strip()
                                                    if option_text:  # Only add non-empty options
                                                        available_options.append(option_text)
                                                
                                                print(f"  Available location options ({len(available_options)}): {available_options[:10]}{'...' if len(available_options) > 10 else ''}")
                                                
                                                # First priority: Try to find exact dealership name match
                                                dealership_found = False
                                                for option_text in available_options:
                                                    if option_text == dealership_name:
                                                        try:
                                                            value_dropdown.select_by_visible_text(option_text)
                                                            print(f"  ✓ Selected exact dealership match: '{option_text}'")
                                                            dealership_found = True
                                                            break
                                                        except Exception as select_error:
                                                            print(f"  ! Error selecting exact match '{option_text}': {select_error}")
                                                            continue
                                                
                                                # Second priority: Try partial dealership name match
                                                if not dealership_found:
                                                    for option_text in available_options:
                                                        if (dealership_name.lower() in option_text.lower() or 
                                                            option_text.lower() in dealership_name.lower()):
                                                            try:
                                                                value_dropdown.select_by_visible_text(option_text)
                                                                print(f"  ✓ Selected partial dealership match: '{option_text}' (for '{dealership_name}')")
                                                                dealership_found = True
                                                                break
                                                            except Exception as select_error:
                                                                print(f"  ! Error selecting partial match '{option_text}': {select_error}")
                                                                continue
                                                
                                                # Third priority: Try to find the corresponding email in dropdown
                                                if not dealership_found:
                                                    for option_text in available_options:
                                                        if corresponding_email.lower() in option_text.lower():
                                                            try:
                                                                value_dropdown.select_by_visible_text(option_text)
                                                                print(f"  ✓ Selected email match in dropdown: '{option_text}'")
                                                                dealership_found = True
                                                                break
                                                            except Exception as select_error:
                                                                print(f"  ! Error selecting email match '{option_text}': {select_error}")
                                                                continue
                                                
                                                # If nothing found, warn user but don't change selection
                                                if not dealership_found:
                                                    print(f"  ⚠️  WARNING: Could not find '{dealership_name}' in dropdown options")
                                                    print(f"  ⚠️  Available options (first 10): {available_options[:10]}")
                                                    print(f"  ⚠️  Leaving current selection unchanged")
                                                    
                                            else:
                                                # It's a text field, not dropdown - clear and type the dealership name
                                                value_field.clear()
                                                value_field.send_keys(dealership_name)
                                                print(f"  ✓ Entered dealership name in text field: '{dealership_name}'")
                                                
                                        except Exception as dropdown_error:
                                            print(f"  ! Error interacting with value field: {dropdown_error}")
                                            # Try fallback approach - clear and type
                                            try:
                                                value_field.clear()
                                                value_field.send_keys(dealership_name)
                                                print(f"  ✓ Fallback: Entered dealership name as text: '{dealership_name}'")
                                            except Exception as fallback_error:
                                                print(f"  ✗ Fallback also failed: {fallback_error}")
                                    else:
                                        # Use Feed ID for Dealer ID routing
                                        value_field.clear()
                                        value_field.send_keys(row['FEED ID'])
                                    
                                    # Verify the new rule fields were actually populated
                                    time.sleep(0.2)  # Brief pause for field updates
                                    actual_email = email_field.get_attribute('value')
                                    actual_value = value_field.get_attribute('value')
                                    
                                    if actual_email != row[email_column]:
                                        print(f"  ! Warning: New rule email field shows '{actual_email}' instead of '{row[email_column]}'")
                                    
                                    expected_value = row['DEALERSHIP NAME'] if use_location_routing else row['FEED ID']
                                    if actual_value != expected_value:
                                        print(f"  ! Warning: New rule value field shows '{actual_value}' instead of '{expected_value}'")
                                        # Try again if it didn't work
                                        value_field.clear()
                                        if use_location_routing:
                                            value_field.send_keys(row['DEALERSHIP NAME'])
                                        else:
                                            value_field.send_keys(row['FEED ID'])
                                        time.sleep(0.1)
                                        actual_value = value_field.get_attribute('value')
                                        print(f"  ! Retry result: New rule value field now shows '{actual_value}'")
                                    
                                    print(f"  ✓ Created rule {new_rule_index}: Email='{actual_email}', Value='{actual_value}'")
                                    rules_configured += 1
                                    data_index += 1
                                else:
                                    print(f"  Could not click add button, stopping new rule creation")
                                    break
                                
                        except Exception as e:
                            print(f"  ✗ Error creating new rule: {e}")
                            data_index += 1
                            continue
                
                print(f"{notification_name} routing configuration complete! Configured {rules_configured} rules total")
                        
            except Exception as e:
                print(f"Error configuring {notification_name} routing rules: {e}")
                return "failed"

            # Save the notification settings
            print(f"Saving {notification_name} notification settings...")
            try:
                save_btn = driver.find_element(By.XPATH, "//input[@type='submit' and (@value='Update Notification' or @value='Save Notification')]")
                save_btn.click()
                time.sleep(2)  # Wait for save to complete
                print(f"{notification_name} notification saved successfully")
            except Exception as e:
                print(f"Could not find or click save button for {notification_name}: {e}")
                return "failed"
            
            logger.info(f"{notification_name} updated for form: {form_title}")
            
            # Navigate back to notifications list for this form
            if notification_name != "Text Formatted Notification":  # Don't navigate back after the last notification
                print(f"Returning to notifications list for {notification_name}...")
                driver.get(f"{self.wp_url.rstrip('/')}/wp/wp-admin/admin.php?page=gf_edit_forms&view=settings&subview=notification&id={form_id}")
                wait.until(EC.presence_of_element_located((By.LINK_TEXT, "Notifications")))
            
            return "success"
                
        except Exception as e:
            print(f"Error processing {notification_name}: {e}")
            logger.error(f"Error processing {notification_name}: {e}")
            return "failed"

    def run(self):
        try:
            # Read data from Google Sheet
            sheet_data = self.read_google_sheet()
            if not sheet_data:
                print("Error: Missing or empty values detected in the sheet. Please check your data and try again.")
                logger.error("Aborting due to missing or empty values in the sheet.")
                return
            
            # Browser setup already navigated to WordPress admin and handled authentication
            print(f"\nFound {len(sheet_data)} rows of data to process.")
            
            # Automate Gravity Forms notification routing rules
            self.automate_form_notifications(sheet_data)
            
            print("\nAutomation completed successfully!")
            
        finally:
            if self.driver:
                input("\nPress Enter to close the browser and exit...")
                self.driver.quit()

if __name__ == "__main__":
    # Prompt user for Google Sheet URL or ID
    sheet_url = input("Enter the Google Sheet URL or ID: ").strip()
    sheet_id = get_sheet_id_from_url(sheet_url)
    # Prompt user for WordPress site URL
    wp_url = input("Enter the WordPress site URL (e.g., https://yoursite.com): ").strip()
    # Set headless=False for debugging, True for normal runs
    router = LeadRouter(sheet_id=sheet_id, wp_url=wp_url, headless=False)
    router.run() 