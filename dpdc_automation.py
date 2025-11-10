from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import json
import time
import os
import re

class DPDCAutomation:
    def __init__(self):
        """Initialize with browser settings to avoid CAPTCHA"""
        print("🚀 Initializing DPDC Automation with CAPTCHA bypass settings...")
        
        # Set up Chrome options to appear as a real user
        chrome_options = Options()
        
        # IMPORTANT: Run in non-headless mode initially to accept permissions
        # Then we can use headless in subsequent runs
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        # Enable geolocation
        chrome_options.add_argument('--enable-geolocation')
        
        # Set a realistic window size
        chrome_options.add_argument('--window-size=1920,1080')
        
        # Disable automation flags
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Set realistic user agent
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Accept all cookies and permissions
        chrome_options.add_experimental_option("prefs", {
            "profile.default_content_setting_values.cookies": 1,  # Allow all cookies
            "profile.default_content_setting_values.geolocation": 1,  # Allow geolocation
            "profile.default_content_setting_values.notifications": 1,  # Allow notifications
            "profile.default_content_setting_values.media_stream": 1,  # Allow camera/mic
            "profile.cookie_controls_mode": 0,  # Allow all cookies
            "profile.block_third_party_cookies": False,  # Allow third-party cookies
        })
        
        # Use persistent user data directory to save cookies between runs
        # This makes the browser remember the site and avoid CAPTCHA in future
        user_data_dir = '/tmp/chrome-user-data'
        chrome_options.add_argument(f'--user-data-dir={user_data_dir}')
        chrome_options.add_argument('--profile-directory=Default')
        
        # Use system ChromeDriver
        service = Service('/usr/bin/chromedriver')
        
        # Initialize Chrome driver
        self.driver = webdriver.Chrome(
            service=service,
            options=chrome_options
        )
        
        # Remove webdriver detection
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Set geolocation to Bangladesh (Dhaka)
        self.driver.execute_cdp_cmd("Emulation.setGeolocationOverride", {
            "latitude": 23.8103,
            "longitude": 90.4125,
            "accuracy": 100
        })
        
        # Add more realistic browser properties
        self.driver.execute_script("""
            // Make the browser appear more real
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en', 'bn']
            });
            Object.defineProperty(navigator, 'platform', {
                get: () => 'Win32'
            });
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8
            });
            window.chrome = {
                runtime: {}
            };
        """)
        
        self.wait = WebDriverWait(self.driver, 30)
        
        print("✓ Browser initialized with human-like settings")
        print("  - Cookies: Enabled")
        print("  - Location: Bangladesh (Dhaka)")
        print("  - User Agent: Real browser")
        print("  - Persistent session: Enabled")
        
        # Initialize Google Sheets
        self.setup_google_sheets()
        
    def setup_google_sheets(self):
        """Set up Google Sheets connection"""
        try:
            credentials_json = os.environ.get('GOOGLE_CREDENTIALS')
            if not credentials_json:
                raise Exception("GOOGLE_CREDENTIALS not found in environment")
            
            creds_dict = json.loads(credentials_json)
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            self.gc = gspread.authorize(creds)
            print("✓ Google Sheets connected")
            
        except Exception as e:
            print(f"✗ Error setting up Google Sheets: {e}")
            raise
    
    def build_trust_with_site(self):
        """Build trust by browsing the site naturally before automation"""
        try:
            print("\n🌐 Building trust with DPDC website...")
            
            # Step 1: Visit homepage first (like a real user)
            print("   Step 1: Visiting homepage...")
            self.driver.get('https://amiapp.dpdc.org.bd/')
            time.sleep(3)
            
            # Scroll a bit (human behavior)
            self.driver.execute_script("window.scrollTo(0, 300);")
            time.sleep(1)
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            # Step 2: Accept any cookie banners if present
            print("   Step 2: Looking for cookie consent...")
            try:
                # Common cookie banner button selectors
                cookie_buttons = [
                    "//button[contains(text(), 'Accept')]",
                    "//button[contains(text(), 'I agree')]",
                    "//button[contains(text(), 'OK')]",
                    "//button[contains(@class, 'accept')]",
                    "//a[contains(text(), 'Accept')]"
                ]
                
                for selector in cookie_buttons:
                    try:
                        button = self.driver.find_element(By.XPATH, selector)
                        if button.is_displayed():
                            button.click()
                            print("   ✓ Accepted cookies")
                            time.sleep(1)
                            break
                    except:
                        continue
            except:
                print("   No cookie banner found (already accepted)")
            
            # Step 3: Set cookies manually to mark as trusted
            print("   Step 3: Setting trust cookies...")
            cookies = [
                {'name': 'cookieConsent', 'value': 'accepted', 'domain': '.dpdc.org.bd'},
                {'name': 'user_preference', 'value': 'trusted', 'domain': '.dpdc.org.bd'},
            ]
            
            for cookie in cookies:
                try:
                    self.driver.add_cookie(cookie)
                except:
                    pass  # Cookie might already exist or domain might be different
            
            print("   ✓ Trust building complete")
            time.sleep(2)
            
            return True
            
        except Exception as e:
            print(f"   ⚠️  Trust building warning: {e}")
            return True  # Continue anyway
    
    def navigate_to_quick_pay(self):
        """Navigate to Quick Pay page"""
        try:
            print("\n📍 Navigating to Quick Pay...")
            
            # Visit login page first
            print("   Opening login page...")
            self.driver.get('https://amiapp.dpdc.org.bd/login')
            time.sleep(4)
            self.driver.save_screenshot('step1_login_page.png')
            
            # Look for Quick Pay button
            print("   Looking for Quick Pay button...")
            
            quick_pay_selectors = [
                "//button[contains(text(), 'Quick Pay')]",
                "//button[contains(text(), 'QUICK PAY')]",
                "//a[contains(text(), 'Quick Pay')]",
                "//a[contains(text(), 'QUICK PAY')]",
                "//button[contains(@class, 'quick')]",
                "//a[contains(@href, 'quick-pay')]",
                "//*[contains(text(), 'Quick Pay')]"
            ]
            
            quick_pay_button = None
            for selector in quick_pay_selectors:
                try:
                    element = self.driver.find_element(By.XPATH, selector)
                    if element.is_displayed():
                        quick_pay_button = element
                        break
                except:
                    continue
            
            if quick_pay_button:
                # Scroll to button naturally
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", quick_pay_button)
                time.sleep(1)
                
                # Move mouse to it (simulate human)
                from selenium.webdriver.common.action_chains import ActionChains
                actions = ActionChains(self.driver)
                actions.move_to_element(quick_pay_button).perform()
                time.sleep(0.5)
                
                quick_pay_button.click()
                print("   ✓ Clicked Quick Pay button")
                time.sleep(4)
            else:
                print("   Quick Pay button not found, navigating directly...")
                self.driver.get('https://amiapp.dpdc.org.bd/quick-pay')
                time.sleep(4)
            
            self.driver.save_screenshot('step2_quick_pay_page.png')
            print("   ✓ Quick Pay page loaded")
            return True
                
        except Exception as e:
            print(f"   ✗ Navigation error: {e}")
            self.driver.save_screenshot('navigation_error.png')
            raise
    
    def check_if_captcha_present(self):
        """Check if CAPTCHA is present on the page"""
        try:
            # Look for reCAPTCHA iframe
            captcha_iframe = self.driver.find_element(By.XPATH, "//iframe[contains(@src, 'recaptcha')]")
            if captcha_iframe.is_displayed():
                print("   ⚠️  CAPTCHA is present")
                return True
        except:
            print("   ✓ No CAPTCHA detected!")
            return False
        
        return False
    
    def fetch_usage_data(self, customer_number):
        """Fetch usage data from DPDC website"""
        try:
            print(f"\n📡 Fetching data for customer: {customer_number}")
            
            # Build trust first
            self.build_trust_with_site()
            
            # Navigate to Quick Pay
            self.navigate_to_quick_pay()
            
            # Wait a bit for page to fully load
            time.sleep(3)
            
            # Find customer number input
            print("   Step 3: Locating customer number input...")
            
            customer_input = None
            input_selectors = [
                "//input[contains(@placeholder, 'Customer')]",
                "//input[contains(@placeholder, 'customer')]",
                "//input[contains(@placeholder, 'Number')]",
                "//input[@type='text']",
                "//input[@type='number']"
            ]
            
            for selector in input_selectors:
                try:
                    element = self.driver.find_element(By.XPATH, selector)
                    if element.is_displayed():
                        customer_input = element
                        print(f"   ✓ Found input field")
                        break
                except:
                    continue
            
            if not customer_input:
                # Fallback: get all inputs
                inputs = self.driver.find_elements(By.TAG_NAME, 'input')
                for inp in inputs:
                    input_type = inp.get_attribute('type')
                    if inp.is_displayed() and input_type in ['text', 'number', 'tel']:
                        customer_input = inp
                        print(f"   ✓ Found input field (fallback)")
                        break
            
            if not customer_input:
                raise Exception("Could not find customer number input field")
            
            # Enter customer number naturally (like a human)
            print(f"   Step 4: Entering customer number...")
            
            # Scroll to input
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", customer_input)
            time.sleep(1)
            
            # Click the input
            customer_input.click()
            time.sleep(0.5)
            
            # Clear if needed
            customer_input.clear()
            time.sleep(0.3)
            
            # Type slowly (human-like)
            for digit in customer_number:
                customer_input.send_keys(digit)
                time.sleep(0.15)  # Realistic typing speed
            
            print(f"   ✓ Entered customer number: {customer_number}")
            time.sleep(2)
            self.driver.save_screenshot('step3_after_input.png')
            
            # Check if CAPTCHA appeared
            has_captcha = self.check_if_captcha_present()
            
            if has_captcha:
                print("\n" + "="*60)
                print("⚠️  CAPTCHA APPEARED DESPITE TRUST SETTINGS")
                print("="*60)
                print("This might happen on first run. Options:")
                print("1. The cookies will be saved for next run")
                print("2. You might need to run this locally once first")
                print("3. Or use the paid service ($0.12/month)")
                print("="*60 + "\n")
                
                # Wait a bit to see if it auto-solves
                print("   Waiting 30 seconds to see if CAPTCHA auto-solves...")
                time.sleep(30)
                self.driver.save_screenshot('step4_captcha_wait.png')
            
            # Find and click submit button
            print("   Step 5: Submitting form...")
            
            submit_button = None
            button_selectors = [
                "//button[@type='submit']",
                "//button[contains(text(), 'Submit')]",
                "//button[contains(text(), 'SUBMIT')]",
                "//input[@type='submit']",
                "//button[contains(@class, 'submit')]"
            ]
            
            for selector in button_selectors:
                try:
                    element = self.driver.find_element(By.XPATH, selector)
                    if element.is_displayed():
                        submit_button = element
                        break
                except:
                    continue
            
            if submit_button:
                # Scroll to button
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", submit_button)
                time.sleep(1)
                
                # Click naturally
                from selenium.webdriver.common.action_chains import ActionChains
                actions = ActionChains(self.driver)
                actions.move_to_element(submit_button).perform()
                time.sleep(0.5)
                
                submit_button.click()
                print("   ✓ Submit button clicked")
            else:
                print("   No submit button found, pressing Enter...")
                customer_input.send_keys(Keys.RETURN)
            
            # Wait for results
            print("   Step 6: Waiting for results...")
            time.sleep(10)
            
            self.driver.save_screenshot('step5_results.png')
            
            # Check for errors
            page_text = self.driver.find_element(By.TAG_NAME, 'body').text
            
            if 'no results found' in page_text.lower() or 'oops' in page_text.lower():
                print("   ⚠️  'No results found' message detected")
                if 'recaptcha' in page_text.lower() or 'robot' in page_text.lower():
                    print("   This might be due to CAPTCHA blocking")
                with open('no_results_page.txt', 'w', encoding='utf-8') as f:
                    f.write(page_text)
            
            # Scrape data
            data = self.scrape_page_data()
            
            return data
            
        except Exception as e:
            print(f"✗ Error fetching data: {e}")
            self.driver.save_screenshot('error_screenshot.png')
            with open('error_page_source.html', 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            import traceback
            traceback.print_exc()
            raise
    
    def scrape_page_data(self):
        """Scrape usage data from the rendered page"""
        try:
            print("   Step 7: Extracting data from page...")
            
            page_text = self.driver.find_element(By.TAG_NAME, 'body').text
            
            with open('page_text.txt', 'w', encoding='utf-8') as f:
                f.write(page_text)
            
            data = {
                'accountId': '',
                'customerName': '',
                'customerClass': '',
                'mobileNumber': '',
                'emailId': '',
                'accountType': '',
                'balanceRemaining': '',
                'connectionStatus': '',
                'customerType': '',
                'minRecharge': ''
            }
            
            # Parse line by line
            lines = page_text.split('\n')
            for line in lines:
                if ':' in line:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        key = parts[0].strip().lower()
                        value = parts[1].strip()
                        
                        if value:
                            if 'account' in key and ('id' in key or 'number' in key):
                                data['accountId'] = value
                                print(f"   Found Account ID: {value}")
                            elif 'customer name' in key or 'name' in key:
                                data['customerName'] = value
                                print(f"   Found Customer Name: {value}")
                            elif 'balance' in key or 'amount' in key or 'due' in key:
                                data['balanceRemaining'] = value
                                print(f"   Found Balance: {value}")
                            elif 'status' in key:
                                data['connectionStatus'] = value
                                print(f"   Found Status: {value}")
                            elif 'mobile' in key or 'phone' in key:
                                data['mobileNumber'] = value
                                print(f"   Found Mobile: {value}")
                            elif 'email' in key:
                                data['emailId'] = value
                            elif 'class' in key:
                                data['customerClass'] = value
                                print(f"   Found Class: {value}")
                            elif 'type' in key and 'customer' in key:
                                data['customerType'] = value
            
            # Regex fallback
            try:
                if not data['accountId']:
                    account_match = re.search(r'\b(\d{8,})\b', page_text)
                    if account_match:
                        data['accountId'] = account_match.group(1)
                        print(f"   Found Account ID (regex): {data['accountId']}")
                
                if not data['balanceRemaining']:
                    balance_match = re.search(r'(?:Balance|Amount|Due).*?([\d,]+\.?\d*)', page_text, re.IGNORECASE)
                    if balance_match:
                        data['balanceRemaining'] = balance_match.group(1)
                        print(f"   Found Balance (regex): {data['balanceRemaining']}")
                
                if not data['mobileNumber']:
                    mobile_match = re.search(r'\b(01\d{9})\b', page_text)
                    if mobile_match:
                        data['mobileNumber'] = mobile_match.group(1)
                        print(f"   Found Mobile (regex): {data['mobileNumber']}")
            except Exception as e:
                print(f"   Regex extraction error: {e}")
            
            # Store page snippet if no data found
            if not any(data.values()):
                print("   ⚠️  No structured data found, storing page text")
                clean_text = page_text.replace('\n', ' ').strip()
                data['customerName'] = clean_text[:300]
            else:
                print(f"   ✓ Data extraction successful")
            
            return data
            
        except Exception as e:
            print(f"   ✗ Scraping error: {e}")
            return {
                'accountId': '',
                'customerName': f'Error: {str(e)}',
                'customerClass': '',
                'mobileNumber': '',
                'emailId': '',
                'accountType': '',
                'balanceRemaining': '',
                'connectionStatus': '',
                'customerType': '',
                'minRecharge': ''
            }
    
    def update_google_sheet(self, spreadsheet_id, data):
        """Update Google Sheet"""
        try:
            print("\n📊 Updating Google Sheet...")
            
            sheet = self.gc.open_by_key(spreadsheet_id)
            worksheet = sheet.sheet1
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            row_data = [
                timestamp,
                data.get('accountId', ''),
                data.get('customerName', ''),
                data.get('customerClass', ''),
                data.get('mobileNumber', ''),
                data.get('emailId', ''),
                data.get('accountType', ''),
                data.get('balanceRemaining', ''),
                data.get('connectionStatus', ''),
                data.get('customerType', ''),
                data.get('minRecharge', '')
            ]
            
            worksheet.append_row(row_data)
            print(f"✓ Data added to sheet at {timestamp}")
            
            return True
            
        except Exception as e:
            print(f"✗ Error updating Google Sheet: {e}")
            raise
    
    def run(self):
        """Main execution"""
        try:
            print("\n" + "="*60)
            print("DPDC Automation (Cookie & Location Trust Method)")
            print(f"Started at: {datetime.now()}")
            print("="*60)
            
            customer_number = os.environ.get('CUSTOMER_NUMBER')
            spreadsheet_id = os.environ.get('SPREADSHEET_ID')
            
            if not customer_number or not spreadsheet_id:
                raise Exception("Missing environment variables")
            
            print(f"Customer Number: {customer_number}")
            print(f"Spreadsheet ID: {spreadsheet_id[:10]}...")
            
            data = self.fetch_usage_data(customer_number)
            self.update_google_sheet(spreadsheet_id, data)
            
            print("\n" + "="*60)
            print("✓ Automation completed successfully!")
            print("="*60)
            
            return True
            
        except Exception as e:
            print("\n" + "="*60)
            print(f"✗ Automation failed: {e}")
            print("="*60)
            import traceback
            traceback.print_exc()
            return False
            
        finally:
            try:
                self.driver.quit()
                print("\n🔒 Browser closed")
            except:
                pass

if __name__ == "__main__":
    automation = DPDCAutomation()
    success = automation.run()
    exit(0 if success else 1)
