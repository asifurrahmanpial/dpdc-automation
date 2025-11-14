from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import undetected_chromedriver as uc
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import json
import time
import os
import random
import requests
import traceback
import re

class DPDCAutomation:
    def __init__(self):
        """Initialize with advanced anti-detection measures"""
        print("🚀 Initializing DPDC Automation (Anti-Detection Mode)...")
        
        # Use undetected-chromedriver instead of regular selenium
        self.driver = self.create_undetected_driver()
        self.wait = WebDriverWait(self.driver, 30)
        self.setup_google_sheets()
    
    def create_undetected_driver(self):
        """Create an undetected Chrome driver that bypasses most bot detection"""
        print("   → Creating undetected Chrome driver...")
        
        options = uc.ChromeOptions()
        
        # Essential options for GitHub Actions
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        # Anti-detection measures
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-features=IsolateOrigins,site-per-process')
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        
        # Realistic browser profile
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Language and timezone
        options.add_argument('--lang=en-US')
        options.add_argument('--accept-lang=en-US,en;q=0.9')
        
        # Preferences to appear more human
        prefs = {
            'profile.default_content_setting_values': {
                'cookies': 1,
                'images': 1,  # Load images to see what's happening
                'javascript': 1,
                'plugins': 1,
                'popups': 0,
                'geolocation': 1,
                'notifications': 1,
                'media_stream': 1,
            }
        }
        options.add_experimental_option('prefs', prefs)
        
        try:
            # Create driver with undetected-chromedriver
            driver = uc.Chrome(
                options=options,
                driver_executable_path='/usr/bin/chromedriver',
                version_main=None,  # Auto-detect Chrome version
                use_subprocess=True
            )
            
            # Additional stealth JavaScript
            stealth_js = """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
                Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
                Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});
                window.chrome = {runtime: {}, loadTimes: function(){}, csi: function(){}, app: {}};
                Object.defineProperty(navigator, 'permissions', {
                    get: () => ({
                        query: () => Promise.resolve({state: 'granted'})
                    })
                });
            """
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {'source': stealth_js})
            
            # Set geolocation to Bangladesh
            driver.execute_cdp_cmd('Emulation.setGeolocationOverride', {
                'latitude': 23.8103,
                'longitude': 90.4125,
                'accuracy': 100
            })
            
            print("   ✓ Undetected Chrome driver created")
            return driver
            
        except Exception as e:
            print(f"   ⚠ Error creating undetected driver: {e}")
            print("   → Falling back to regular Chrome with stealth")
            return self.create_stealth_driver()
    
    def create_stealth_driver(self):
        """Fallback: Regular Chrome with maximum stealth"""
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        prefs = {
            'profile.default_content_setting_values': {
                'cookies': 1,
                'images': 1,
                'geolocation': 1,
                'notifications': 1
            }
        }
        chrome_options.add_experimental_option('prefs', prefs)
        
        service = Service('/usr/bin/chromedriver')
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Inject stealth scripts
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                window.chrome = {runtime: {}};
            '''
        })
        
        return driver

    def setup_google_sheets(self):
        try:
            credentials_json = os.environ.get('GOOGLE_CREDENTIALS')
            if not credentials_json:
                raise Exception("GOOGLE_CREDENTIALS not found")

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

    def human_delay(self, min_sec=1.5, max_sec=4.0):
        """More realistic human-like delays"""
        delay = random.uniform(min_sec, max_sec)
        # Add micro-pauses to simulate reading/thinking
        if random.random() > 0.7:
            delay += random.uniform(0.5, 2.0)
        time.sleep(delay)

    def human_type(self, element, text):
        """Type like a human with variable speed and occasional mistakes"""
        for i, char in enumerate(text):
            element.send_keys(char)
            # Variable typing speed
            delay = random.uniform(0.05, 0.25)
            # Occasionally pause longer (thinking)
            if random.random() > 0.85:
                delay += random.uniform(0.3, 0.8)
            time.sleep(delay)

    def wait_for_captcha_solution(self, max_wait=60):
        """
        Wait for reCAPTCHA to be solved (either auto-solve or manual)
        Returns True if appears solved, False if timeout
        """
        print(f"   → Waiting up to {max_wait}s for CAPTCHA resolution...")
        start_time = time.time()
        last_check = ""
        
        while time.time() - start_time < max_wait:
            try:
                self.driver.switch_to.default_content()
                
                # Method 1: Check if submit button is enabled (captcha solved)
                try:
                    submit_btn = self.driver.find_element(By.XPATH, "//button[@type='submit']")
                    if not submit_btn.get_attribute('disabled'):
                        print("   ✓ Submit button is enabled!")
                        return True
                except:
                    pass
                
                # Method 2: Check captcha checkbox state
                try:
                    checkbox_iframe = self.driver.find_element(By.CSS_SELECTOR, "iframe[src*='recaptcha/api2/anchor']")
                    self.driver.switch_to.frame(checkbox_iframe)
                    checkbox = self.driver.find_element(By.ID, "recaptcha-anchor")
                    aria_checked = checkbox.get_attribute("aria-checked")
                    self.driver.switch_to.default_content()
                    
                    if aria_checked == "true":
                        current_check = "✓ Checkbox checked"
                        if current_check != last_check:
                            print(f"   {current_check}")
                            last_check = current_check
                        return True
                except:
                    pass
                
                # Method 3: Check for error/success messages
                page_text = self.driver.find_element(By.TAG_NAME, 'body').text.lower()
                if 'account' in page_text or 'balance' in page_text or 'customer' in page_text:
                    print("   ✓ Data appears on page!")
                    return True
                
                # Progress indicator
                elapsed = int(time.time() - start_time)
                if elapsed % 10 == 0 and elapsed > 0:
                    print(f"   ... still waiting ({elapsed}s/{max_wait}s)")
                
                time.sleep(2)
                
            except Exception as e:
                time.sleep(1)
        
        print(f"   ⚠ Timeout after {max_wait}s")
        return False

    def click_captcha_checkbox(self):
        """Click the reCAPTCHA checkbox"""
        try:
            self.driver.switch_to.default_content()
            
            # Find checkbox iframe
            checkbox_iframe = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='recaptcha/api2/anchor']"))
            )
            
            self.driver.switch_to.frame(checkbox_iframe)
            self.human_delay(1, 2)
            
            # Click checkbox
            checkbox = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.ID, "recaptcha-anchor"))
            )
            checkbox.click()
            print("   ✓ Clicked CAPTCHA checkbox")
            
            self.driver.switch_to.default_content()
            return True
            
        except TimeoutException:
            print("   ✓ No CAPTCHA found")
            return True
        except Exception as e:
            print(f"   ⚠ Error clicking checkbox: {e}")
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return False

    def extract_data_from_page(self):
        """Extract data using multiple methods"""
        print("   → Extracting data from page...")
        
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
        
        # Save page for debugging
        page_source = self.driver.page_source
        with open('final_page.html', 'w', encoding='utf-8') as f:
            f.write(page_source)
        
        page_text = self.driver.find_element(By.TAG_NAME, 'body').text
        with open('final_page_text.txt', 'w', encoding='utf-8') as f:
            f.write(page_text)
        
        print(f"   → Page text length: {len(page_text)} characters")
        
        # Method 1: Look for specific elements by class/id
        try:
            # Try to find data in common element structures
            elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), ':')]")
            for elem in elements:
                text = elem.text
                if ':' in text:
                    parts = text.split(':', 1)
                    if len(parts) == 2:
                        key = parts[0].strip().lower()
                        value = parts[1].strip()
                        
                        if value:
                            if 'account' in key and ('id' in key or 'number' in key):
                                data['accountId'] = value
                            elif 'name' in key:
                                data['customerName'] = value
                            elif 'balance' in key:
                                data['balanceRemaining'] = value
                            elif 'mobile' in key or 'phone' in key:
                                data['mobileNumber'] = value
                            elif 'email' in key:
                                data['emailId'] = value
                            elif 'class' in key:
                                data['customerClass'] = value
                            elif 'status' in key:
                                data['connectionStatus'] = value
        except Exception as e:
            print(f"   ⚠ Element extraction error: {e}")
        
        # Method 2: Parse the text content line by line
        for line in page_text.split('\n'):
            line = line.strip()
            if ':' not in line:
                continue
            
            parts = line.split(':', 1)
            if len(parts) != 2:
                continue
            
            key = parts[0].strip().lower()
            value = parts[1].strip()
            
            if not value:
                continue
            
            # Map keys to data fields
            if ('account' in key or 'customer' in key) and 'number' in key and not data['accountId']:
                data['accountId'] = value
            elif 'name' in key and not data['customerName']:
                data['customerName'] = value
            elif 'balance' in key and not data['balanceRemaining']:
                data['balanceRemaining'] = value
            elif ('mobile' in key or 'phone' in key) and not data['mobileNumber']:
                data['mobileNumber'] = value
            elif 'email' in key and not data['emailId']:
                data['emailId'] = value
            elif 'class' in key and not data['customerClass']:
                data['customerClass'] = value
            elif 'type' in key and not data['accountType']:
                data['accountType'] = value
            elif 'status' in key and not data['connectionStatus']:
                data['connectionStatus'] = value
            elif 'minimum' in key or 'min' in key:
                data['minRecharge'] = value
        
        # Method 3: Regex patterns
        if not data['balanceRemaining']:
            balance_patterns = [
                r'balance[:\s]+([0-9,.]+)',
                r'remaining[:\s]+([0-9,.]+)',
                r'due[:\s]+([0-9,.]+)',
                r'tk[:\s]+([0-9,.]+)',
                r'৳[:\s]*([0-9,.]+)'
            ]
            for pattern in balance_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    data['balanceRemaining'] = match.group(1)
                    break
        
        if not data['mobileNumber']:
            mobile_match = re.search(r'(?:mobile|phone)[:\s]+([\d\-+]+)', page_text, re.IGNORECASE)
            if mobile_match:
                data['mobileNumber'] = mobile_match.group(1)
        
        # Print what we found
        found_fields = [k for k, v in data.items() if v]
        print(f"   ✓ Found {len(found_fields)} fields: {', '.join(found_fields)}")
        
        return data

    def fetch_usage_data(self, customer_number):
        try:
            print(f"\n📡 Fetching data for customer: {customer_number}")
            
            # Navigate to homepage
            print("   → Loading DPDC website...")
            self.driver.get('https://amiapp.dpdc.org.bd/')
            self.human_delay(3, 5)
            self.driver.save_screenshot('01_homepage.png')
            
            # Click QUICK PAY button
            print("   → Clicking QUICK PAY button...")
            try:
                # Try multiple selectors for the Quick Pay button
                quick_pay_clicked = False
                
                # Method 1: Look for button with text "QUICK PAY"
                try:
                    quick_pay_btn = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'QUICK PAY')]"))
                    )
                    self.human_delay(1, 2)
                    quick_pay_btn.click()
                    quick_pay_clicked = True
                    print("   ✓ Clicked QUICK PAY button (method 1)")
                except:
                    pass
                
                # Method 2: Look for any element with "QUICK PAY" text
                if not quick_pay_clicked:
                    try:
                        quick_pay_elem = self.driver.find_element(By.XPATH, "//*[contains(text(), 'QUICK PAY')]")
                        quick_pay_elem.click()
                        quick_pay_clicked = True
                        print("   ✓ Clicked QUICK PAY element (method 2)")
                    except:
                        pass
                
                # Method 3: Direct navigation as fallback
                if not quick_pay_clicked:
                    print("   → Direct navigation to Quick Pay page...")
                    self.driver.get('https://amiapp.dpdc.org.bd/quick-pay')
                
                self.human_delay(4, 6)
                self.driver.save_screenshot('02_quick_pay.png')
                
            except Exception as e:
                print(f"   ⚠ Error navigating to Quick Pay: {e}")
                print("   → Trying direct URL...")
                self.driver.get('https://amiapp.dpdc.org.bd/quick-pay')
                self.human_delay(4, 6)
                self.driver.save_screenshot('02_quick_pay_fallback.png')
            
            # Enter customer number
            print("   → Entering customer number...")
            try:
                # Wait for page to be fully loaded
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # Wait a bit more for any JS to finish
                self.human_delay(2, 3)
                
                # Find the input field - be more specific to avoid search bar
                customer_input = None
                
                # Method 1: Look for input in the Quick Pay form area
                try:
                    customer_input = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//input[@type='text' and not(contains(@placeholder, 'Search'))]"))
                    )
                    print("   ✓ Found customer input field (method 1)")
                except:
                    pass
                
                # Method 2: Look for input by placeholder containing "customer" or "account"
                if not customer_input:
                    try:
                        customer_input = self.driver.find_element(By.XPATH, "//input[contains(@placeholder, 'ustomer') or contains(@placeholder, 'ccount') or contains(@placeholder, 'umber')]")
                        print("   ✓ Found customer input field (method 2)")
                    except:
                        pass
                
                # Method 3: Get all inputs and use the first one that's not a search box
                if not customer_input:
                    inputs = self.driver.find_elements(By.XPATH, "//input[@type='text' or @type='number']")
                    for inp in inputs:
                        placeholder = inp.get_attribute('placeholder') or ''
                        if 'search' not in placeholder.lower():
                            customer_input = inp
                            print("   ✓ Found customer input field (method 3)")
                            break
                
                if not customer_input:
                    raise Exception("Could not find customer number input field")
                
                # Clear and focus
                customer_input.clear()
                customer_input.click()
                self.human_delay(0.5, 1)
                
                # Type customer number
                self.human_type(customer_input, customer_number)
                
                print(f"   ✓ Entered: {customer_number}")
                self.human_delay(2, 3)
                self.driver.save_screenshot('03_after_input.png')
                
            except Exception as e:
                print(f"   ✗ Could not enter customer number: {e}")
                self.driver.save_screenshot('03_error_input.png')
                raise
            
            # Handle CAPTCHA
            print("\n🔐 Handling reCAPTCHA...")
            self.click_captcha_checkbox()
            self.human_delay(2, 3)
            
            # Wait for CAPTCHA to resolve
            captcha_solved = self.wait_for_captcha_solution(max_wait=60)
            
            if captcha_solved:
                print("   ✓ CAPTCHA appears resolved")
            else:
                print("   ⚠ CAPTCHA may not be solved, trying anyway...")
            
            self.driver.save_screenshot('04_after_captcha.png')
            
            # Submit the form
            print("\n📤 Submitting form...")
            try:
                submit_btn = self.driver.find_element(By.XPATH, "//button[@type='submit' or contains(text(), 'Submit') or contains(text(), 'SUBMIT')]")
                
                self.human_delay(1, 2)
                
                # Try clicking
                try:
                    submit_btn.click()
                except:
                    self.driver.execute_script("arguments[0].click();", submit_btn)
                
                print("   ✓ Submit clicked")
                
            except Exception as e:
                print(f"   ⚠ Could not find submit button, trying Enter key: {e}")
                customer_input.send_keys(Keys.RETURN)
            
            # Wait for results
            print("\n⏳ Waiting for results...")
            self.human_delay(8, 12)
            self.driver.save_screenshot('05_after_submit.png')
            
            # Additional wait to ensure data loads
            self.human_delay(5, 8)
            self.driver.save_screenshot('06_final_wait.png')
            
            # Extract data
            print("\n📊 Extracting data...")
            data = self.extract_data_from_page()
            
            # Check if we got any data
            if not any(data.values()):
                print("   ⚠ No data extracted, check screenshots and HTML files")
                data['accountId'] = customer_number
                data['customerName'] = 'Data extraction failed - check artifacts'
                data['balanceRemaining'] = 'N/A'
            else:
                print("   ✓ Data successfully extracted!")
            
            return data
            
        except Exception as e:
            print(f"\n✗ Error during fetch: {e}")
            traceback.print_exc()
            self.driver.save_screenshot('error_final.png')
            
            # Return error data
            return {
                'accountId': customer_number,
                'customerName': f'Error: {str(e)[:100]}',
                'customerClass': '',
                'mobileNumber': '',
                'emailId': '',
                'accountType': '',
                'balanceRemaining': 'Error - check artifacts',
                'connectionStatus': '',
                'customerType': '',
                'minRecharge': ''
            }

    def update_google_sheet(self, spreadsheet_id, data):
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
            print(f"✓ Sheet updated at {timestamp}")
            print(f"   Data: {data}")
            return True
        except Exception as e:
            print(f"✗ Sheet update error: {e}")
            traceback.print_exc()
            return False

    def run(self):
        try:
            print("\n" + "="*60)
            print("DPDC Automation - Enhanced Version")
            print(f"Started: {datetime.now()}")
            print("="*60)

            customer_number = os.environ.get('CUSTOMER_NUMBER')
            spreadsheet_id = os.environ.get('SPREADSHEET_ID')

            if not customer_number or not spreadsheet_id:
                raise Exception("Missing environment variables")

            print(f"Customer: {customer_number}")
            print(f"Sheet ID: {spreadsheet_id[:10]}...")

            data = self.fetch_usage_data(customer_number)
            self.update_google_sheet(spreadsheet_id, data)

            print("\n" + "="*60)
            print("✓ Process Completed!")
            print("="*60)
            return True

        except Exception as e:
            print("\n" + "="*60)
            print(f"✗ Process Failed: {e}")
            print("="*60)
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
