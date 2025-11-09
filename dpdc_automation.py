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
        """Initialize the automation"""
        print("🚀 Initializing DPDC Automation...")
        
        # Set up Chrome options for headless mode
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Use system ChromeDriver (installed by GitHub Actions)
        service = Service('/usr/bin/chromedriver')
        
        # Initialize Chrome driver
        self.driver = webdriver.Chrome(
            service=service,
            options=chrome_options
        )
        
        # Remove webdriver flag
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        self.wait = WebDriverWait(self.driver, 30)
        
        # Initialize Google Sheets
        self.setup_google_sheets()
        
    def setup_google_sheets(self):
        """Set up Google Sheets connection"""
        try:
            # Create credentials from JSON stored in secrets
            credentials_json = os.environ.get('GOOGLE_CREDENTIALS')
            if not credentials_json:
                raise Exception("GOOGLE_CREDENTIALS not found in environment")
            
            # Parse JSON and create credentials
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
    
    def navigate_to_quick_pay(self):
        """Navigate through login page to Quick Pay"""
        try:
            print("\n🌐 Navigating to DPDC website...")
            
            # Step 1: Go to login page (which is the landing page)
            print("   Step 1: Opening login page...")
            self.driver.get('https://amiapp.dpdc.org.bd/login')
            time.sleep(5)
            self.driver.save_screenshot('step1_login_page.png')
            print(f"   ✓ Login page loaded. Current URL: {self.driver.current_url}")
            
            # Step 2: Find and click Quick Pay button
            print("   Step 2: Looking for Quick Pay button...")
            
            quick_pay_button = None
            
            # Try multiple selectors for Quick Pay button
            selectors = [
                "//button[contains(text(), 'Quick Pay')]",
                "//button[contains(text(), 'QUICK PAY')]",
                "//a[contains(text(), 'Quick Pay')]",
                "//a[contains(text(), 'QUICK PAY')]",
                "//button[contains(@class, 'quick')]",
                "//a[contains(@class, 'quick')]",
                "//div[contains(text(), 'Quick Pay')]",
                "//span[contains(text(), 'Quick Pay')]"
            ]
            
            for selector in selectors:
                try:
                    element = self.driver.find_element(By.XPATH, selector)
                    if element.is_displayed():
                        quick_pay_button = element
                        print(f"   ✓ Found Quick Pay button with selector: {selector}")
                        break
                except:
                    continue
            
            if not quick_pay_button:
                # Try to find it by looking at all clickable elements
                print("   Looking through all buttons and links...")
                buttons = self.driver.find_elements(By.TAG_NAME, 'button')
                links = self.driver.find_elements(By.TAG_NAME, 'a')
                
                for element in buttons + links:
                    text = element.text.lower()
                    if 'quick' in text and 'pay' in text:
                        quick_pay_button = element
                        print(f"   ✓ Found Quick Pay button: {element.text}")
                        break
            
            if quick_pay_button:
                # Scroll to button and click
                self.driver.execute_script("arguments[0].scrollIntoView(true);", quick_pay_button)
                time.sleep(1)
                quick_pay_button.click()
                print("   ✓ Clicked Quick Pay button")
                time.sleep(5)
                
                self.driver.save_screenshot('step2_quick_pay_page.png')
                print(f"   ✓ Quick Pay page loaded. Current URL: {self.driver.current_url}")
                return True
            else:
                # If button not found, try to navigate directly
                print("   ⚠ Quick Pay button not found, trying direct navigation...")
                self.driver.get('https://amiapp.dpdc.org.bd/quick-pay')
                time.sleep(5)
                self.driver.save_screenshot('step2_direct_navigation.png')
                print(f"   ✓ Navigated directly. Current URL: {self.driver.current_url}")
                return True
                
        except Exception as e:
            print(f"   ✗ Error navigating: {e}")
            self.driver.save_screenshot('navigation_error.png')
            raise
    
    def fetch_usage_data(self, customer_number):
        """Fetch usage data from DPDC website"""
        try:
            print(f"\n📡 Fetching data for customer: {customer_number}")
            
            # Navigate to Quick Pay page
            self.navigate_to_quick_pay()
            
            # Now we should be on the Quick Pay page
            time.sleep(3)
            
            # Try to find customer number input field
            print("   Step 3: Looking for customer number input field...")
            
            customer_input = None
            
            # Strategy 1: Try by placeholder text
            try:
                customer_input = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, "//input[contains(@placeholder, 'Customer') or contains(@placeholder, 'customer') or contains(@placeholder, 'Account') or contains(@placeholder, 'account') or contains(@placeholder, 'Number') or contains(@placeholder, 'number')]"))
                )
                print("   ✓ Found input by placeholder")
            except:
                pass
            
            # Strategy 2: Try all visible text/number inputs
            if not customer_input:
                try:
                    inputs = self.driver.find_elements(By.TAG_NAME, 'input')
                    print(f"   Found {len(inputs)} input fields")
                    
                    for inp in inputs:
                        if not inp.is_displayed():
                            continue
                            
                        input_type = inp.get_attribute('type')
                        input_name = inp.get_attribute('name')
                        input_id = inp.get_attribute('id')
                        input_placeholder = inp.get_attribute('placeholder')
                        
                        print(f"   Input: type={input_type}, name={input_name}, id={input_id}, placeholder={input_placeholder}")
                        
                        # Look for text or number inputs
                        if input_type in ['text', 'number', 'tel']:
                            customer_input = inp
                            print(f"   ✓ Using input: {input_name or input_id or input_placeholder}")
                            break
                except Exception as e:
                    print(f"   Could not find input: {e}")
            
            if not customer_input:
                # Save page source for debugging
                with open('page_source.html', 'w', encoding='utf-8') as f:
                    f.write(self.driver.page_source)
                self.driver.save_screenshot('no_input_found.png')
                raise Exception("Could not find customer number input field")
            
            # Clear and enter customer number
            print(f"   Step 4: Entering customer number: {customer_number}")
            self.driver.execute_script("arguments[0].scrollIntoView(true);", customer_input)
            time.sleep(1)
            customer_input.click()
            time.sleep(1)
            customer_input.clear()
            time.sleep(1)
            
            # Type slowly to mimic human behavior
            for digit in customer_number:
                customer_input.send_keys(digit)
                time.sleep(0.1)
            
            time.sleep(2)
            self.driver.save_screenshot('step3_after_input.png')
            print("   ✓ Customer number entered")
            
            # Find and click search/submit button
            print("   Step 5: Looking for search/submit button...")
            
            button_clicked = False
            
            # Try to find submit button
            try:
                buttons = self.driver.find_elements(By.TAG_NAME, 'button')
                print(f"   Found {len(buttons)} buttons")
                
                for btn in buttons:
                    if not btn.is_displayed():
                        continue
                        
                    btn_text = btn.text.lower()
                    btn_type = btn.get_attribute('type')
                    
                    print(f"   Button: text='{btn.text}', type={btn_type}")
                    
                    if btn_type == 'submit' or any(word in btn_text for word in ['search', 'submit', 'find', 'get', 'go']):
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                        time.sleep(1)
                        btn.click()
                        print(f"   ✓ Clicked button: {btn.text}")
                        button_clicked = True
                        break
            except Exception as e:
                print(f"   Button click attempt failed: {e}")
            
            # If no button found, press Enter
            if not button_clicked:
                print("   No button found, pressing Enter...")
                customer_input.send_keys(Keys.RETURN)
                print("   ✓ Pressed Enter")
            
            # Wait for results to load
            print("   Step 6: Waiting for results...")
            time.sleep(10)
            
            # Take screenshot of results
            self.driver.save_screenshot('step4_results.png')
            
            # Check current URL
            print(f"   Current URL after search: {self.driver.current_url}")
            
            # Check for error messages
            page_text = self.driver.find_element(By.TAG_NAME, 'body').text
            print(f"   Page text length: {len(page_text)} characters")
            
            if 'no results found' in page_text.lower() or 'oops' in page_text.lower():
                print("   ⚠ Warning: 'No results found' message detected")
                with open('error_page_text.txt', 'w', encoding='utf-8') as f:
                    f.write(page_text)
            
            # Try to scrape data from the page
            data = self.scrape_page_data()
            
            return data
            
        except Exception as e:
            print(f"✗ Error fetching data: {e}")
            # Save screenshot on error
            self.driver.save_screenshot('error_screenshot.png')
            # Save page source for debugging
            with open('error_page_source.html', 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            import traceback
            traceback.print_exc()
            raise
    
    def scrape_page_data(self):
        """Scrape usage data from the rendered page"""
        try:
            print("   Step 7: Extracting data from page...")
            
            # Get page source
            page_source = self.driver.page_source
            page_text = self.driver.find_element(By.TAG_NAME, 'body').text
            
            # Save for debugging
            with open('page_text.txt', 'w', encoding='utf-8') as f:
                f.write(page_text)
            
            # Initialize data structure
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
            
            # Strategy 1: Look for label-value pairs with colons
            lines = page_text.split('\n')
            for line in lines:
                if ':' in line:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        key = parts[0].strip().lower()
                        value = parts[1].strip()
                        
                        if value:  # Only store non-empty values
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
                                print(f"   Found Email: {value}")
                            elif 'class' in key:
                                data['customerClass'] = value
                                print(f"   Found Class: {value}")
                            elif 'type' in key:
                                data['customerType'] = value
                                print(f"   Found Type: {value}")
            
            # Strategy 2: Use regex to extract patterns
            try:
                # Account numbers (8+ digits)
                account_match = re.search(r'\b(\d{8,})\b', page_text)
                if account_match and not data['accountId']:
                    data['accountId'] = account_match.group(1)
                    print(f"   Found Account ID via regex: {data['accountId']}")
                
                # Balance amounts (numbers with optional decimal)
                balance_match = re.search(r'(?:Balance|Amount|Due).*?([\d,]+\.?\d*)', page_text, re.IGNORECASE)
                if balance_match and not data['balanceRemaining']:
                    data['balanceRemaining'] = balance_match.group(1)
                    print(f"   Found Balance via regex: {data['balanceRemaining']}")
                
                # Mobile numbers (11 digits for Bangladesh)
                mobile_match = re.search(r'\b(01\d{9})\b', page_text)
                if mobile_match and not data['mobileNumber']:
                    data['mobileNumber'] = mobile_match.group(1)
                    print(f"   Found Mobile via regex: {data['mobileNumber']}")
                    
            except Exception as e:
                print(f"   Error in regex extraction: {e}")
            
            # If no data found, store snippet for debugging
            if not any(data.values()):
                print("   ⚠ No structured data found")
                # Store first 300 chars of relevant text (skip headers/footers)
                clean_text = page_text.replace('\n', ' ').strip()
                data['customerName'] = clean_text[:300]
            else:
                print(f"   ✓ Successfully extracted data")
            
            return data
            
        except Exception as e:
            print(f"   ✗ Error scraping page: {e}")
            import traceback
            traceback.print_exc()
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
        """Update Google Sheet with the fetched data"""
        try:
            print("\n📊 Updating Google Sheet...")
            
            # Open the spreadsheet
            sheet = self.gc.open_by_key(spreadsheet_id)
            worksheet = sheet.sheet1  # Use first sheet
            
            # Prepare row data
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
            
            # Append to sheet
            worksheet.append_row(row_data)
            print(f"✓ Data added to sheet at {timestamp}")
            
            return True
            
        except Exception as e:
            print(f"✗ Error updating Google Sheet: {e}")
            raise
    
    def run(self):
        """Main execution method"""
        try:
            print("\n" + "="*60)
            print("DPDC Usage Data Automation")
            print(f"Started at: {datetime.now()}")
            print("="*60)
            
            # Get configuration from environment
            customer_number = os.environ.get('CUSTOMER_NUMBER')
            spreadsheet_id = os.environ.get('SPREADSHEET_ID')
            
            if not customer_number or not spreadsheet_id:
                raise Exception("Missing required environment variables")
            
            print(f"Customer Number: {customer_number}")
            print(f"Spreadsheet ID: {spreadsheet_id[:10]}...")
            
            # Fetch data
            data = self.fetch_usage_data(customer_number)
            
            # Update sheet
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
            # Clean up
            try:
                self.driver.quit()
                print("\n🔒 Browser closed")
            except:
                pass

# Run the automation
if __name__ == "__main__":
    automation = DPDCAutomation()
    success = automation.run()
    exit(0 if success else 1)
