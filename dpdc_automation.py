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
                'images': 2,  # Don't load images for faster execution
                'javascript': 1,
                'plugins': 1,
                'popups': 0,
                'geolocation': 1,
                'notifications': 1,
                'media_stream': 1,
            },
            'profile.managed_default_content_settings.images': 2,
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
                'images': 2,
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
        
        # Sometimes backspace and retype (human error simulation)
        if random.random() > 0.9 and len(text) > 3:
            time.sleep(random.uniform(0.2, 0.5))
            element.send_keys(Keys.BACK_SPACE)
            time.sleep(random.uniform(0.1, 0.3))
            element.send_keys(text[-1])

    def wait_for_captcha_to_solve_itself(self, max_wait=30):
        """
        Wait for reCAPTCHA to auto-solve (many times it does with good fingerprint)
        Returns True if solved, False if still waiting
        """
        print("   → Waiting for reCAPTCHA auto-solve...")
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                # Check if we're back to main content (captcha solved)
                self.driver.switch_to.default_content()
                
                # Look for success indicators on the page
                page_text = self.driver.find_element(By.TAG_NAME, 'body').text.lower()
                
                if any(indicator in page_text for indicator in ['account', 'balance', 'customer', 'mobile']):
                    print("   ✓ CAPTCHA appears to be solved (found data)")
                    return True
                
                # Check if captcha checkbox is checked
                try:
                    checkbox_iframe = self.driver.find_element(By.CSS_SELECTOR, "iframe[src*='recaptcha/api2/anchor']")
                    self.driver.switch_to.frame(checkbox_iframe)
                    checkbox = self.driver.find_element(By.ID, "recaptcha-anchor")
                    aria_checked = checkbox.get_attribute("aria-checked")
                    self.driver.switch_to.default_content()
                    
                    if aria_checked == "true":
                        print("   ✓ CAPTCHA checkbox is checked!")
                        return True
                except:
                    pass
                
                time.sleep(2)
                
            except Exception as e:
                time.sleep(1)
        
        print("   ⚠ CAPTCHA did not auto-solve")
        return False

    def handle_captcha_smartly(self):
        """
        Smart CAPTCHA handling - wait first, only try to solve if needed
        """
        try:
            print("\n🔐 Handling reCAPTCHA...")
            self.driver.switch_to.default_content()
            
            # Check if captcha exists
            try:
                checkbox_iframe = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='recaptcha/api2/anchor']"))
                )
                print("   ✓ reCAPTCHA detected")
            except TimeoutException:
                print("   ✓ No reCAPTCHA found")
                return True
            
            # Click the checkbox
            self.driver.switch_to.frame(checkbox_iframe)
            self.human_delay(1, 2)
            
            checkbox = self.driver.find_element(By.ID, "recaptcha-anchor")
            checkbox.click()
            print("   ✓ Clicked checkbox")
            
            self.driver.switch_to.default_content()
            
            # Wait longer to see if it auto-solves
            if self.wait_for_captcha_to_solve_itself(max_wait=45):
                return True
            
            print("   ⚠ CAPTCHA did not auto-solve, may need manual intervention")
            print("   → Continuing anyway to check for data...")
            return True
            
        except Exception as e:
            print(f"   ⚠ CAPTCHA handling error: {e}")
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return True  # Continue anyway

    def fetch_usage_data(self, customer_number):
        try:
            print(f"\n📡 Fetching data for customer: {customer_number}")
            
            # Navigate to login with realistic behavior
            print("   → Loading website...")
            self.driver.get('https://amiapp.dpdc.org.bd/')
            self.human_delay(3, 5)  # Longer initial delay
            
            # Scroll a bit (human behavior)
            self.driver.execute_script("window.scrollTo(0, 300);")
            self.human_delay(1, 2)
            self.driver.execute_script("window.scrollTo(0, 0);")
            
            self.driver.save_screenshot('01_homepage.png')
            
            # Navigate to quick pay
            print("   → Navigating to Quick Pay...")
            try:
                quick_pay_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'QUICK PAY')]"))
                )
                self.human_delay(1, 2)
                quick_pay_btn.click()
            except:
                print("   → Direct navigation to Quick Pay page...")
                self.driver.get('https://amiapp.dpdc.org.bd/quick-pay')
            
            self.human_delay(3, 5)
            self.driver.save_screenshot('02_quick_pay.png')
            
            # Enter customer number with human-like typing
            print("   → Entering customer number (human-like)...")
            try:
                customer_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//input[@type='text' or @type='number']"))
                )
                
                # Click and focus
                customer_input.click()
                self.human_delay(0.5, 1)
                
                # Type like a human
                self.human_type(customer_input, customer_number)
                
                print("   ✓ Entered customer number")
                self.human_delay(2, 3)
                self.driver.save_screenshot('03_after_input.png')
            except Exception as e:
                print(f"   ✗ Could not enter customer number: {e}")
                raise
            
            # Handle CAPTCHA smartly
            self.handle_captcha_smartly()
            
            # Submit form
            print("   → Submitting form...")
            try:
                submit_btn = self.driver.find_element(By.XPATH, "//button[@type='submit']")
                
                # Wait for button to be enabled
                for _ in range(10):
                    if not submit_btn.get_attribute('disabled'):
                        break
                    time.sleep(1)
                
                self.human_delay(1, 2)
                self.driver.execute_script("arguments[0].click();", submit_btn)
                print("   ✓ Form submitted")
            except:
                customer_input.send_keys(Keys.RETURN)
                print("   ✓ Pressed Enter")
            
            # Wait for results with patience
            print("   → Waiting for results...")
            self.human_delay(10, 15)
            self.driver.save_screenshot('04_results.png')
            
            # Try multiple times to get data
            data = None
            for attempt in range(3):
                print(f"   → Extraction attempt {attempt + 1}/3...")
                page_text = self.driver.find_element(By.TAG_NAME, 'body').text
                
                # Save for debugging
                with open(f'page_text_attempt_{attempt + 1}.txt', 'w', encoding='utf-8') as f:
                    f.write(page_text)
                
                data = self.extract_data_from_text(page_text)
                
                if data and any(data.values()):
                    print("   ✓ Data found!")
                    break
                
                if attempt < 2:
                    print("   ⚠ No data yet, waiting longer...")
                    self.human_delay(5, 8)
            
            if not data or not any(data.values()):
                print("   ⚠ Could not extract data, saving page source...")
                with open('final_page.html', 'w', encoding='utf-8') as f:
                    f.write(self.driver.page_source)
                
                # Return partial data anyway
                data = {
                    'accountId': customer_number,
                    'customerName': 'Data extraction failed',
                    'customerClass': '',
                    'mobileNumber': '',
                    'emailId': '',
                    'accountType': '',
                    'balanceRemaining': 'Check manually',
                    'connectionStatus': '',
                    'customerType': '',
                    'minRecharge': ''
                }
            
            return data
            
        except Exception as e:
            print(f"✗ Error: {e}")
            traceback.print_exc()
            self.driver.save_screenshot('error.png')
            raise

    def extract_data_from_text(self, page_text):
        """Enhanced data extraction with multiple patterns"""
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
            if 'account' in key and 'id' in key:
                data['accountId'] = value
            elif 'account' in key and not data['accountId']:
                data['accountId'] = value
            elif 'name' in key or 'customer name' in key:
                data['customerName'] = value
            elif 'balance' in key or 'remaining' in key:
                data['balanceRemaining'] = value
            elif 'mobile' in key or 'phone' in key:
                data['mobileNumber'] = value
            elif 'email' in key:
                data['emailId'] = value
            elif 'class' in key:
                data['customerClass'] = value
            elif 'type' in key and 'account' in key:
                data['accountType'] = value
            elif 'status' in key:
                data['connectionStatus'] = value
            elif 'minimum' in key or 'min' in key:
                data['minRecharge'] = value
        
        # Extract using regex patterns as fallback
        if not data['balanceRemaining']:
            balance_match = re.search(r'(?:balance|remaining)[:\s]+([0-9,.]+)', page_text, re.IGNORECASE)
            if balance_match:
                data['balanceRemaining'] = balance_match.group(1)
        
        if not data['mobileNumber']:
            mobile_match = re.search(r'(?:mobile|phone)[:\s]+([\d\-+]+)', page_text, re.IGNORECASE)
            if mobile_match:
                data['mobileNumber'] = mobile_match.group(1)
        
        return data

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
            print(f"✓ Updated at {timestamp}")
            return True
        except Exception as e:
            print(f"✗ Error: {e}")
            raise

    def run(self):
        try:
            print("\n" + "="*60)
            print("DPDC Automation - Advanced Anti-Detection")
            print(f"Started: {datetime.now()}")
            print("="*60)

            customer_number = os.environ.get('CUSTOMER_NUMBER')
            spreadsheet_id = os.environ.get('SPREADSHEET_ID')

            if not customer_number or not spreadsheet_id:
                raise Exception("Missing environment variables")

            print(f"Customer: {customer_number}")
            print(f"Sheet: {spreadsheet_id[:10]}...")

            data = self.fetch_usage_data(customer_number)
            self.update_google_sheet(spreadsheet_id, data)

            print("\n" + "="*60)
            print("✓ Completed Successfully!")
            print("="*60)
            return True

        except Exception as e:
            print("\n" + "="*60)
            print(f"✗ Failed: {e}")
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
