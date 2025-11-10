from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import json
import time
import os
import re

class DPDCAutomation:
    def __init__(self):
        """Initialize the automation"""
        print("🚀 Initializing DPDC Automation...")
        
        # Set up Chrome options to avoid reCAPTCHA
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')  # Use new headless mode
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        # Anti-detection measures
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Set realistic user agent
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Enable cookies and geolocation
        chrome_options.add_argument('--enable-features=NetworkService,NetworkServiceInProcess')
        chrome_options.add_argument('--disable-features=VizDisplayCompositor')
        
        # Set permissions for location and cookies
        prefs = {
            'profile.default_content_setting_values': {
                'cookies': 1,  # Allow cookies
                'geolocation': 1,  # Allow location
                'notifications': 1
            },
            'profile.managed_default_content_settings': {
                'geolocation': 1
            }
        }
        chrome_options.add_experimental_option('prefs', prefs)
        
        # Use system ChromeDriver
        service = Service('/usr/bin/chromedriver')
        
        # Initialize Chrome driver
        self.driver = webdriver.Chrome(
            service=service,
            options=chrome_options
        )
        
        # Override navigator properties to avoid detection
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
                window.chrome = {
                    runtime: {}
                };
                Object.defineProperty(navigator, 'permissions', {
                    get: () => ({
                        query: () => Promise.resolve({ state: 'granted' })
                    })
                });
            '''
        })
        
        # Set geolocation (Dhaka, Bangladesh coordinates)
        self.driver.execute_cdp_cmd('Emulation.setGeolocationOverride', {
            'latitude': 23.8103,
            'longitude': 90.4125,
            'accuracy': 100
        })
        
        self.wait = WebDriverWait(self.driver, 30)
        
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
    
    def check_and_handle_captcha(self):
        """Check if reCAPTCHA is present and wait for it"""
        try:
            print("   Checking for reCAPTCHA...")
            
            # Check if reCAPTCHA iframe is present
            try:
                captcha_frame = self.driver.find_element(By.XPATH, "//iframe[contains(@src, 'recaptcha')]")
                print("   ⚠ reCAPTCHA detected!")
                
                # Wait a bit to see if it auto-solves (sometimes happens with proper settings)
                time.sleep(5)
                
                # Check if captcha is still there
                try:
                    captcha_frame = self.driver.find_element(By.XPATH, "//iframe[contains(@src, 'recaptcha')]")
                    print("   ⚠ reCAPTCHA still present - waiting longer...")
                    
                    # Wait up to 30 seconds for auto-solve
                    for i in range(6):
                        time.sleep(5)
                        try:
                            # Check if captcha disappeared
                            self.driver.find_element(By.XPATH, "//iframe[contains(@src, 'recaptcha')]")
                            print(f"   Still waiting... ({(i+1)*5}s)")
                        except NoSuchElementException:
                            print("   ✓ reCAPTCHA appears to be solved!")
                            return True
                    
                    print("   ⚠ reCAPTCHA did not auto-solve")
                    return False
                    
                except NoSuchElementException:
                    print("   ✓ reCAPTCHA auto-solved!")
                    return True
                    
            except NoSuchElementException:
                print("   ✓ No reCAPTCHA found")
                return True
                
        except Exception as e:
            print(f"   Error checking captcha: {e}")
            return True  # Continue anyway
    
    def navigate_to_quick_pay(self):
        """Navigate through login page to Quick Pay"""
        try:
            print("\n🌐 Navigating to DPDC website...")
            
            # Step 1: Go to the main page first to establish cookies
            print("   Step 1: Loading homepage to establish session...")
            self.driver.get('https://amiapp.dpdc.org.bd/')
            time.sleep(5)
            
            # Add some random mouse movements to look more human
            self.driver.execute_script("window.scrollTo(0, 100);")
            time.sleep(1)
            
            # Step 2: Now go to login page
            print("   Step 2: Opening login page...")
            self.driver.get('https://amiapp.dpdc.org.bd/login')
            time.sleep(5)
            self.driver.save_screenshot('step1_login_page.png')
            
            # Check for captcha on login page
            self.check_and_handle_captcha()
            
            # Step 3: Find and click Quick Pay button
            print("   Step 3: Looking for Quick Pay button...")
            
            quick_pay_button = None
            
            # Try to find Quick Pay button
            selectors = [
                "//button[contains(text(), 'QUICK PAY')]",
                "//button[contains(text(), 'Quick Pay')]",
                "//a[contains(text(), 'QUICK PAY')]",
                "//a[contains(text(), 'Quick Pay')]",
                "//div[contains(text(), 'QUICK PAY')]",
                "//span[contains(text(), 'QUICK PAY')]"
            ]
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed():
                            quick_pay_button = element
                            print(f"   ✓ Found Quick Pay button: '{element.text}'")
                            break
                    if quick_pay_button:
                        break
                except:
                    continue
            
            if quick_pay_button:
                # Scroll and click
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", quick_pay_button)
                time.sleep(2)
                quick_pay_button.click()
                print("   ✓ Clicked Quick Pay button")
            else:
                # Direct navigation fallback
                print("   Button not found, navigating directly to quick-pay...")
                self.driver.get('https://amiapp.dpdc.org.bd/quick-pay')
            
            time.sleep(5)
            self.driver.save_screenshot('step2_quick_pay_page.png')
            print(f"   ✓ Quick Pay page loaded. URL: {self.driver.current_url}")
            
            # Check for captcha on quick pay page
            self.check_and_handle_captcha()
            
            return True
                
        except Exception as e:
            print(f"   ✗ Navigation error: {e}")
            self.driver.save_screenshot('navigation_error.png')
            raise
    
    def fetch_usage_data(self, customer_number):
        """Fetch usage data from DPDC website"""
        try:
            print(f"\n📡 Fetching data for customer: {customer_number}")
            
            # Navigate to Quick Pay
            self.navigate_to_quick_pay()
            
            time.sleep(3)
            
            # Find customer number input
            print("   Step 4: Looking for customer number input...")
            
            customer_input = None
            
            # Try multiple strategies
            try:
                # Look for input with specific placeholder or name
                possible_selectors = [
                    "//input[@placeholder='Enter your Customer Number']",
                    "//input[contains(@placeholder, 'Customer')]",
                    "//input[contains(@placeholder, 'customer')]",
                    "//input[@name='customerNumber']",
                    "//input[@type='text']",
                    "//input[@type='number']"
                ]
                
                for selector in possible_selectors:
                    try:
                        elements = self.driver.find_elements(By.XPATH, selector)
                        for element in elements:
                            if element.is_displayed():
                                customer_input = element
                                print(f"   ✓ Found input field")
                                break
                        if customer_input:
                            break
                    except:
                        continue
                        
            except Exception as e:
                print(f"   Error finding input: {e}")
            
            if not customer_input:
                with open('page_source.html', 'w', encoding='utf-8') as f:
                    f.write(self.driver.page_source)
                raise Exception("Could not find customer number input")
            
            # Enter customer number slowly (human-like)
            print(f"   Step 5: Entering customer number...")
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", customer_input)
            time.sleep(1)
            customer_input.click()
            time.sleep(1)
            
            # Type each digit with small delay
            for digit in customer_number:
                customer_input.send_keys(digit)
                time.sleep(0.15)  # Human-like typing speed
            
            time.sleep(2)
            self.driver.save_screenshot('step3_after_input.png')
            print("   ✓ Customer number entered")
            
            # Handle reCAPTCHA if it appears after typing
            captcha_solved = self.check_and_handle_captcha()
            
            # Find and click submit button
            print("   Step 6: Looking for Submit button...")
            
            submit_button = None
            
            try:
                buttons = self.driver.find_elements(By.TAG_NAME, 'button')
                for btn in buttons:
                    if btn.is_displayed():
                        btn_text = btn.text.strip().lower()
                        btn_type = btn.get_attribute('type')
                        
                        if btn_type == 'submit' or 'submit' in btn_text:
                            submit_button = btn
                            print(f"   ✓ Found Submit button")
                            break
            except:
                pass
            
            if submit_button:
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", submit_button)
                time.sleep(1)
                
                # Try regular click first
                try:
                    submit_button.click()
                    print("   ✓ Clicked Submit button")
                except:
                    # Fallback to JavaScript click
                    self.driver.execute_script("arguments[0].click();", submit_button)
                    print("   ✓ Clicked Submit (via JavaScript)")
            else:
                # Press Enter as fallback
                customer_input.send_keys(Keys.RETURN)
                print("   ✓ Pressed Enter")
            
            # Wait for results
            print("   Step 7: Waiting for results...")
            time.sleep(10)
            
            self.driver.save_screenshot('step4_results.png')
            
            # Check if we got results or errors
            page_text = self.driver.find_element(By.TAG_NAME, 'body').text
            
            if 'no results found' in page_text.lower():
                print("   ⚠ Warning: No results found")
            
            # Scrape the data
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
        """Scrape usage data from results page"""
        try:
            print("   Step 8: Extracting data...")
            
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
            for i, line in enumerate(lines):
                line = line.strip()
                if ':' in line:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        key = parts[0].strip().lower()
                        value = parts[1].strip()
                        
                        if value:
                            if 'account' in key and ('id' in key or 'number' in key):
                                data['accountId'] = value
                            elif 'customer name' in key or 'name' in key:
                                data['customerName'] = value
                            elif 'balance' in key or 'amount' in key or 'due' in key:
                                data['balanceRemaining'] = value
                            elif 'status' in key:
                                data['connectionStatus'] = value
                            elif 'mobile' in key or 'phone' in key:
                                data['mobileNumber'] = value
                            elif 'email' in key:
                                data['emailId'] = value
                            elif 'class' in key:
                                data['customerClass'] = value
                            elif 'type' in key:
                                data['customerType'] = value
            
            # If no structured data found
            if not any(data.values()):
                print("   ⚠ No structured data found")
                data['customerName'] = page_text[:300].replace('\n', ' ').strip()
            else:
                print("   ✓ Data extracted successfully")
            
            return data
            
        except Exception as e:
            print(f"   ✗ Error scraping: {e}")
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
        """Update Google Sheet with data"""
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
            print(f"✓ Data added at {timestamp}")
            
            return True
            
        except Exception as e:
            print(f"✗ Error updating sheet: {e}")
            raise
    
    def run(self):
        """Main execution"""
        try:
            print("\n" + "="*60)
            print("DPDC Usage Data Automation")
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
