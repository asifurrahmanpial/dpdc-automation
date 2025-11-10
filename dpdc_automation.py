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
import random
import requests
import speech_recognition as sr
from pydub import AudioSegment
import io

class DPDCAutomation:
    def __init__(self):
        """Initialize with anti-detection and captcha solving"""
        print("🚀 Initializing DPDC Automation with Captcha Solver...")
        
        # Rotating user agents
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
        user_agent = random.choice(self.user_agents)
        
        # Chrome options with anti-detection
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument(f'user-agent={user_agent}')
        
        # Anti-detection
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Enable audio for captcha solving
        chrome_options.add_argument('--use-fake-ui-for-media-stream')
        chrome_options.add_argument('--use-fake-device-for-media-stream')
        
        # Permissions
        prefs = {
            'profile.default_content_setting_values': {
                'cookies': 1,
                'geolocation': 1,
                'notifications': 1,
                'media_stream': 1,
                'media_stream_mic': 1
            }
        }
        chrome_options.add_experimental_option('prefs', prefs)
        
        service = Service('/usr/bin/chromedriver')
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Anti-detection script
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                window.chrome = {runtime: {}};
                Object.defineProperty(navigator, 'permissions', {
                    get: () => ({query: () => Promise.resolve({ state: 'granted' })})
                });
            '''
        })
        
        # Set geolocation to Dhaka
        self.driver.execute_cdp_cmd('Emulation.setGeolocationOverride', {
            'latitude': 23.8103,
            'longitude': 90.4125,
            'accuracy': 100
        })
        
        self.wait = WebDriverWait(self.driver, 30)
        self.setup_google_sheets()
        
    def setup_google_sheets(self):
        """Set up Google Sheets"""
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
    
    def random_delay(self, min_sec=1, max_sec=3):
        """Human-like random delays"""
        time.sleep(random.uniform(min_sec, max_sec))
    
    def human_type(self, element, text):
        """Type like a human with random delays"""
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.1, 0.3))
    
    def solve_recaptcha_v2(self):
        """
        Solve reCAPTCHA v2 using audio challenge method
        This is a FREE method that uses speech recognition
        """
        try:
            print("\n🔓 Attempting to solve reCAPTCHA...")
            
            # Switch to reCAPTCHA iframe
            print("   Step 1: Finding reCAPTCHA iframe...")
            self.driver.switch_to.default_content()
            
            # Find the reCAPTCHA checkbox iframe
            recaptcha_iframe = self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//iframe[contains(@src, 'recaptcha/api2/anchor')]"))
            )
            self.driver.switch_to.frame(recaptcha_iframe)
            print("   ✓ Switched to reCAPTCHA iframe")
            
            # Click the checkbox
            print("   Step 2: Clicking reCAPTCHA checkbox...")
            checkbox = self.wait.until(
                EC.element_to_be_clickable((By.CLASS_NAME, "recaptcha-checkbox-border"))
            )
            checkbox.click()
            print("   ✓ Clicked checkbox")
            self.random_delay(2, 4)
            
            # Switch back and check if challenge appears
            self.driver.switch_to.default_content()
            
            try:
                # Find the challenge iframe
                print("   Step 3: Looking for challenge iframe...")
                challenge_iframe = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, "//iframe[contains(@src, 'recaptcha/api2/bframe')]"))
                )
                self.driver.switch_to.frame(challenge_iframe)
                print("   ✓ Challenge appeared, switching to audio...")
                
                # Click audio button
                audio_button = self.wait.until(
                    EC.element_to_be_clickable((By.ID, "recaptcha-audio-button"))
                )
                audio_button.click()
                print("   ✓ Clicked audio button")
                self.random_delay(2, 3)
                
                # Get audio download link
                print("   Step 4: Downloading audio challenge...")
                audio_source = self.wait.until(
                    EC.presence_of_element_located((By.ID, "audio-source"))
                )
                audio_url = audio_source.get_attribute('src')
                print(f"   ✓ Got audio URL")
                
                # Download audio
                response = requests.get(audio_url)
                audio_data = response.content
                
                # Convert to WAV for speech recognition
                print("   Step 5: Converting audio...")
                audio = AudioSegment.from_mp3(io.BytesIO(audio_data))
                audio = audio.set_channels(1).set_frame_rate(16000)
                wav_data = io.BytesIO()
                audio.export(wav_data, format="wav")
                wav_data.seek(0)
                
                # Use speech recognition to solve
                print("   Step 6: Recognizing speech...")
                recognizer = sr.Recognizer()
                with sr.AudioFile(wav_data) as source:
                    audio_listened = recognizer.record(source)
                    text = recognizer.recognize_google(audio_listened)
                
                print(f"   ✓ Recognized text: {text}")
                
                # Enter the solution
                print("   Step 7: Submitting solution...")
                response_input = self.driver.find_element(By.ID, "audio-response")
                response_input.clear()
                self.human_type(response_input, text.lower())
                self.random_delay(1, 2)
                
                # Click verify
                verify_button = self.driver.find_element(By.ID, "recaptcha-verify-button")
                verify_button.click()
                print("   ✓ Clicked verify")
                
                self.random_delay(3, 5)
                
                # Switch back to main content
                self.driver.switch_to.default_content()
                
                print("   ✓ reCAPTCHA solved successfully!")
                return True
                
            except TimeoutException:
                # No challenge appeared, captcha auto-solved
                print("   ✓ reCAPTCHA auto-solved (no challenge)")
                self.driver.switch_to.default_content()
                return True
                
        except Exception as e:
            print(f"   ✗ Error solving reCAPTCHA: {e}")
            self.driver.switch_to.default_content()
            return False
    
    def navigate_to_quick_pay(self):
        """Navigate to Quick Pay page"""
        try:
            print("\n🌐 Navigating to DPDC website...")
            
            # Visit homepage first
            print("   Step 1: Loading homepage...")
            self.driver.get('https://amiapp.dpdc.org.bd/')
            self.random_delay(3, 5)
            
            # Random scrolling to appear human
            self.driver.execute_script("window.scrollTo(0, 300);")
            self.random_delay(1, 2)
            self.driver.execute_script("window.scrollTo(0, 0);")
            
            # Go to login page
            print("   Step 2: Opening login page...")
            self.driver.get('https://amiapp.dpdc.org.bd/login')
            self.random_delay(3, 5)
            self.driver.save_screenshot('step1_login_page.png')
            
            # Find Quick Pay button
            print("   Step 3: Looking for Quick Pay button...")
            
            quick_pay_button = None
            selectors = [
                "//button[contains(text(), 'QUICK PAY')]",
                "//a[contains(text(), 'QUICK PAY')]"
            ]
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed():
                            quick_pay_button = element
                            break
                    if quick_pay_button:
                        break
                except:
                    continue
            
            if quick_pay_button:
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", quick_pay_button)
                self.random_delay(1, 2)
                quick_pay_button.click()
                print("   ✓ Clicked Quick Pay")
            else:
                self.driver.get('https://amiapp.dpdc.org.bd/quick-pay')
                print("   ✓ Navigated directly")
            
            self.random_delay(3, 5)
            self.driver.save_screenshot('step2_quick_pay_page.png')
            
            return True
            
        except Exception as e:
            print(f"   ✗ Navigation error: {e}")
            raise
    
    def fetch_usage_data(self, customer_number):
        """Fetch data with captcha solving"""
        try:
            print(f"\n📡 Fetching data for customer: {customer_number}")
            
            # Navigate
            self.navigate_to_quick_pay()
            
            # Check for captcha and solve if present
            try:
                self.driver.find_element(By.XPATH, "//iframe[contains(@src, 'recaptcha')]")
                print("   reCAPTCHA detected, solving...")
                if not self.solve_recaptcha_v2():
                    print("   ⚠ Failed to solve captcha, continuing anyway...")
            except NoSuchElementException:
                print("   ✓ No reCAPTCHA detected")
            
            # Find input field
            print("   Step 4: Entering customer number...")
            
            customer_input = None
            possible_selectors = [
                "//input[@type='text']",
                "//input[@type='number']",
                "//input[contains(@placeholder, 'Customer')]"
            ]
            
            for selector in possible_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed():
                            customer_input = element
                            break
                    if customer_input:
                        break
                except:
                    continue
            
            if not customer_input:
                raise Exception("Could not find input field")
            
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", customer_input)
            self.random_delay(1, 2)
            customer_input.click()
            self.random_delay(0.5, 1)
            
            # Type like human
            self.human_type(customer_input, customer_number)
            self.random_delay(1, 2)
            
            self.driver.save_screenshot('step3_after_input.png')
            print("   ✓ Entered customer number")
            
            # Check for captcha again after input
            try:
                self.driver.find_element(By.XPATH, "//iframe[contains(@src, 'recaptcha')]")
                print("   reCAPTCHA appeared after input, solving...")
                if not self.solve_recaptcha_v2():
                    print("   ⚠ Failed to solve captcha")
            except NoSuchElementException:
                pass
            
            # Submit
            print("   Step 5: Submitting...")
            
            submit_button = None
            try:
                buttons = self.driver.find_elements(By.TAG_NAME, 'button')
                for btn in buttons:
                    if btn.is_displayed():
                        btn_type = btn.get_attribute('type')
                        if btn_type == 'submit':
                            submit_button = btn
                            break
            except:
                pass
            
            if submit_button:
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", submit_button)
                self.random_delay(1, 2)
                submit_button.click()
                print("   ✓ Clicked submit")
            else:
                customer_input.send_keys(Keys.RETURN)
                print("   ✓ Pressed Enter")
            
            # Wait for results
            print("   Step 6: Waiting for results...")
            self.random_delay(8, 12)
            
            self.driver.save_screenshot('step4_results.png')
            
            # Scrape data
            data = self.scrape_page_data()
            return data
            
        except Exception as e:
            print(f"✗ Error: {e}")
            self.driver.save_screenshot('error_screenshot.png')
            import traceback
            traceback.print_exc()
            raise
    
    def scrape_page_data(self):
        """Extract data from page"""
        try:
            print("   Step 7: Extracting data...")
            
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
            
            for line in page_text.split('\n'):
                if ':' in line:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        key = parts[0].strip().lower()
                        value = parts[1].strip()
                        
                        if value:
                            if 'account' in key:
                                data['accountId'] = value
                            elif 'name' in key:
                                data['customerName'] = value
                            elif 'balance' in key:
                                data['balanceRemaining'] = value
                            elif 'status' in key:
                                data['connectionStatus'] = value
                            elif 'mobile' in key:
                                data['mobileNumber'] = value
                            elif 'email' in key:
                                data['emailId'] = value
            
            if not any(data.values()):
                data['customerName'] = page_text[:300].replace('\n', ' ')
            
            print("   ✓ Data extracted")
            return data
            
        except Exception as e:
            print(f"✗ Scraping error: {e}")
            return None
    
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
            print(f"✓ Updated at {timestamp}")
            return True
            
        except Exception as e:
            print(f"✗ Error updating sheet: {e}")
            raise
    
    def run(self):
        """Main execution"""
        try:
            print("\n" + "="*60)
            print("DPDC Usage Data Automation with Captcha Solver")
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
            print("✓ Automation completed!")
            print("="*60)
            
            return True
            
        except Exception as e:
            print("\n" + "="*60)
            print(f"✗ Failed: {e}")
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
