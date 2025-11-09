from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import json
import time
import os

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
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        # Initialize Chrome driver
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
        self.wait = WebDriverWait(self.driver, 20)
        
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
            time.sleep(5)  # Wait for page to load
            
            # Try to find and fill customer number input
            print("   Looking for customer number input...")
            
            # Multiple possible selectors for the input field
            possible_selectors = [
                'input[placeholder*="Customer"]',
                'input[placeholder*="customer"]',
                'input[name*="customer"]',
                'input[name*="accountNo"]',
                'input[type="text"]',
                'input[type="number"]'
            ]
            
            customer_input = None
            for selector in possible_selectors:
                try:
                    customer_input = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if customer_input:
                        print(f"   ✓ Found input field with selector: {selector}")
                        break
                except:
                    continue
            
            if not customer_input:
                raise Exception("Could not find customer number input field")
            
            # Clear and enter customer number
            customer_input.clear()
            customer_input.send_keys(customer_number)
            print(f"   ✓ Entered customer number")
            time.sleep(2)
            
            # Find and click search/submit button
            print("   Looking for search button...")
            
            possible_button_selectors = [
                'button[type="submit"]',
                'button:contains("Search")',
                'button:contains("Submit")',
                'button.btn-primary',
                'button[class*="search"]',
                'input[type="submit"]'
            ]
            
            search_button = None
            for selector in possible_button_selectors:
                try:
                    search_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if search_button:
                        print(f"   ✓ Found button with selector: {selector}")
                        break
                except:
                    continue
            
            if search_button:
                search_button.click()
                print("   ✓ Clicked search button")
            else:
                # Try pressing Enter on input field
                from selenium.webdriver.common.keys import Keys
                customer_input.send_keys(Keys.RETURN)
                print("   ✓ Pressed Enter")
            
            # Wait for results
            print("   Waiting for results...")
            time.sleep(8)
            
            # Take screenshot for debugging
            self.driver.save_screenshot('debug_screenshot.png')
            
            # Try to scrape data from the page
            data = self.scrape_page_data()
            
            return data
            
        except Exception as e:
            print(f"✗ Error fetching data: {e}")
            # Save screenshot on error
            self.driver.save_screenshot('error_screenshot.png')
            raise
    
    def scrape_page_data(self):
        """Scrape usage data from the rendered page"""
        try:
            print("   Extracting data from page...")
            
            # Get all text from page
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
            
            # Try to find specific elements (you may need to adjust these selectors)
            selectors = {
                'accountId': ['[class*="account"]', '[data-testid*="account"]', 'span:contains("Account")'],
                'customerName': ['[class*="name"]', '[data-testid*="name"]'],
                'balanceRemaining': ['[class*="balance"]', '[class*="amount"]', '[data-testid*="balance"]'],
                'connectionStatus': ['[class*="status"]', '[data-testid*="status"]'],
            }
            
            for field, selector_list in selectors.items():
                for selector in selector_list:
                    try:
                        element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if element and element.text:
                            data[field] = element.text.strip()
                            break
                    except:
                        continue
            
            # If we couldn't find specific elements, try to extract from page text
            if not any(data.values()):
                print("   ⚠ Could not find specific elements, using page text")
                # This is a fallback - page text will be stored
                data['customerName'] = page_text[:100]  # Store first 100 chars as a record
            
            print(f"   ✓ Data extracted: {data}")
            return data
            
        except Exception as e:
            print(f"   ⚠ Error scraping page: {e}")
            # Return empty data rather than failing
            return {
                'accountId': '',
                'customerName': 'Error extracting data',
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
