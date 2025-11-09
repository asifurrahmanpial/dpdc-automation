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
    
    def fetch_usage_data(self, customer_number):
        """Fetch usage data from DPDC website"""
        try:
            print(f"\n📡 Fetching data for customer: {customer_number}")
            
            # Navigate to DPDC website
            print("   Opening DPDC website...")
            self.driver.get('https://amiapp.dpdc.org.bd/quick-pay')
            
            # Wait longer for page to fully load
            time.sleep(8)
            
            # Save initial page screenshot
            self.driver.save_screenshot('page_loaded.png')
            print("   ✓ Page loaded, screenshot saved")
            
            # Print page source for debugging
            page_source = self.driver.page_source
            print(f"   Page title: {self.driver.title}")
            
            # Try to find customer number input with multiple strategies
            print("   Looking for customer number input field...")
            
            customer_input = None
            
            # Strategy 1: Try by placeholder text
            try:
                customer_input = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, "//input[contains(@placeholder, 'Customer') or contains(@placeholder, 'customer') or contains(@placeholder, 'Account') or contains(@placeholder, 'account')]"))
                )
                print("   ✓ Found input by placeholder")
            except:
                pass
            
            # Strategy 2: Try by input type and attributes
            if not customer_input:
                try:
                    inputs = self.driver.find_elements(By.TAG_NAME, 'input')
                    for inp in inputs:
                        input_type = inp.get_attribute('type')
                        input_name = inp.get_attribute('name')
                        input_id = inp.get_attribute('id')
                        
                        print(f"   Found input: type={input_type}, name={input_name}, id={input_id}")
                        
                        # Look for text or number inputs
                        if input_type in ['text', 'number', 'tel']:
                            if inp.is_displayed():
                                customer_input = inp
                                print(f"   ✓ Using input: {input_name or input_id}")
                                break
                except Exception as e:
                    print(f"   Could not find input: {e}")
            
            if not customer_input:
                # Save page source for debugging
                with open('page_source.html', 'w', encoding='utf-8') as f:
                    f.write(page_source)
                raise Exception("Could not find customer number input field. Check page_source.html for debugging")
            
            # Clear and enter customer number
            print(f"   Entering customer number: {customer_number}")
            customer_input.click()
            time.sleep(1)
            customer_input.clear()
            time.sleep(1)
            customer_input.send_keys(customer_number)
            time.sleep(2)
            
            # Take screenshot after entering
            self.driver.save_screenshot('after_input.png')
            print("   ✓ Customer number entered")
            
            # Find and click search/submit button
            print("   Looking for search/submit button...")
            
            button_clicked = False
            
            # Try to find button by text
            try:
                buttons = self.driver.find_elements(By.TAG_NAME, 'button')
                for btn in buttons:
                    btn_text = btn.text.lower()
                    print(f"   Found button: {btn.text}")
                    if any(word in btn_text for word in ['search', 'submit', 'find', 'get']):
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
            print("   Waiting for results...")
            time.sleep(10)
            
            # Take screenshot of results
            self.driver.save_screenshot('results.png')
            
            # Check for error messages
            page_text = self.driver.find_element(By.TAG_NAME, 'body').text
            if 'no results found' in page_text.lower() or 'oops' in page_text.lower():
                print("   ⚠ Warning: 'No results found' message detected")
                print(f"   Page text snippet: {page_text[:200]}")
            
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
            raise
    
    def scrape_page_data(self):
        """Scrape usage data from the rendered page"""
        try:
            print("   Extracting data from page...")
            
            # Get page source
            page_source = self.driver.page_source
            page_text = self.driver.find_element(By.TAG_NAME, 'body').text
            
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
            
            # Try multiple strategies to find data
            
            # Strategy 1: Look for common label-value patterns
            try:
                # Find all divs, spans, paragraphs that might contain data
                elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Account') or contains(text(), 'Balance') or contains(text(), 'Name') or contains(text(), 'Status')]")
                
                for element in elements:
                    text = element.text
                    print(f"   Found element with text: {text[:100]}")
                    
                    # Try to extract key-value pairs
                    if ':' in text:
                        parts = text.split(':')
                        if len(parts) == 2:
                            key = parts[0].strip().lower()
                            value = parts[1].strip()
                            
                            if 'account' in key and 'id' in key:
                                data['accountId'] = value
                            elif 'name' in key:
                                data['customerName'] = value
                            elif 'balance' in key:
                                data['balanceRemaining'] = value
                            elif 'status' in key:
                                data['connectionStatus'] = value
                            elif 'mobile' in key or 'phone' in key:
                                data['mobileNumber'] = value
                            elif 'email' in key:
                                data['emailId'] = value
            except Exception as e:
                print(f"   Error in strategy 1: {e}")
            
            # Strategy 2: Look for specific CSS classes or IDs
            try:
                # Common class patterns
                class_patterns = [
                    'account', 'customer', 'balance', 'amount', 
                    'status', 'name', 'mobile', 'email'
                ]
                
                for pattern in class_patterns:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, f'[class*="{pattern}"]')
                    for element in elements:
                        if element.text and len(element.text) > 0:
                            print(f"   Found {pattern}: {element.text[:50]}")
            except Exception as e:
                print(f"   Error in strategy 2: {e}")
            
            # Strategy 3: Use regex to extract common patterns
            try:
                # Look for account numbers (usually numeric)
                account_match = re.search(r'Account.*?:?\s*(\d{8,})', page_text, re.IGNORECASE)
                if account_match:
                    data['accountId'] = account_match.group(1)
                
                # Look for balance amounts
                balance_match = re.search(r'Balance.*?:?\s*([\d,]+\.?\d*)', page_text, re.IGNORECASE)
                if balance_match:
                    data['balanceRemaining'] = balance_match.group(1)
                
                # Look for mobile numbers
                mobile_match = re.search(r'Mobile.*?:?\s*(\d{11})', page_text, re.IGNORECASE)
                if mobile_match:
                    data['mobileNumber'] = mobile_match.group(1)
                    
            except Exception as e:
                print(f"   Error in strategy 3: {e}")
            
            # If no data found, store page text for manual inspection
            if not any(data.values()):
                print("   ⚠ Could not find structured data, storing page text")
                # Store snippet of page text
                data['customerName'] = page_text[:200].replace('\n', ' ').strip()
                
                # Save full page text to file for debugging
                with open('page_text.txt', 'w', encoding='utf-8') as f:
                    f.write(page_text)
                print("   Full page text saved to page_text.txt")
            
            print(f"   ✓ Data extracted: {json.dumps(data, indent=2)}")
            return data
            
        except Exception as e:
            print(f"   ✗ Error scraping page: {e}")
            # Return error data rather than failing
            return {
                'accountId': '',
                'customerName': f'Error extracting data: {str(e)}',
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
