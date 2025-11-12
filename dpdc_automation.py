from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
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
import traceback

class DPDCAutomation:
    def __init__(self):
        """Initialize with proxy rotation and captcha solving"""
        print("🚀 Initializing DPDC Automation with Proxy Rotation...")
        
        # Get working proxy first
        self.proxy = self.get_working_proxy()
        if self.proxy:
            print(f"✓ Using proxy: {self.proxy}")
        else:
            print("⚠ No working proxy found, using direct connection")
        
        # Create driver with proxy
        self.driver = self.create_driver_with_proxy(self.proxy)
        self.wait = WebDriverWait(self.driver, 30)
        self.setup_google_sheets()
    
    def fetch_proxy_list(self):
        """Fetch proxies from multiple reliable sources"""
        proxies = []
        
        print("   Fetching proxy lists...")
        
        # Source 1: ProxyScrape (most reliable)
        try:
            url = 'https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=elite'
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                proxy_list = [p.strip() for p in response.text.split('\n') if p.strip()]
                proxies.extend(proxy_list)
                print(f"   ✓ ProxyScrape: {len(proxy_list)} proxies")
        except Exception as e:
            print(f"   ⚠ ProxyScrape failed: {e}")
        
        # Source 2: GitHub - TheSpeedX (updated frequently)
        try:
            url = 'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt'
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                proxy_list = [p.strip() for p in response.text.split('\n') if p.strip() and ':' in p]
                proxies.extend(proxy_list)
                print(f"   ✓ TheSpeedX: {len(proxy_list)} proxies")
        except Exception as e:
            print(f"   ⚠ TheSpeedX failed: {e}")
        
        # Source 3: proxy-list (clarketm)
        try:
            url = 'https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt'
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                proxy_list = [p.strip() for p in response.text.split('\n') if p.strip() and ':' in p]
                proxies.extend(proxy_list)
                print(f"   ✓ clarketm: {len(proxy_list)} proxies")
        except Exception as e:
            print(f"   ⚠ clarketm failed: {e}")
        
        # Source 4: Free-Proxy-List
        try:
            url = 'https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt'
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                proxy_list = [p.strip() for p in response.text.split('\n') if p.strip() and ':' in p]
                proxies.extend(proxy_list)
                print(f"   ✓ ShiftyTR: {len(proxy_list)} proxies")
        except Exception as e:
            print(f"   ⚠ ShiftyTR failed: {e}")
        
        # Remove duplicates and shuffle
        proxies = list(set(proxies))
        random.shuffle(proxies)
        
        print(f"   → Total unique proxies: {len(proxies)}")
        return proxies
    
    def test_proxy(self, proxy, timeout=8):
        """Test if proxy is working"""
        try:
            proxies_dict = {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }
            # Test with a simple endpoint
            response = requests.get('http://httpbin.org/ip', proxies=proxies_dict, timeout=timeout)
            if response.status_code == 200:
                # Also check if it can reach Google
                response2 = requests.get('https://www.google.com', proxies=proxies_dict, timeout=timeout)
                return response2.status_code == 200
        except:
            pass
        return False
    
    def get_working_proxy(self):
        """Find a working proxy from available sources"""
        print("🔍 Finding working proxy...")
        
        proxies = self.fetch_proxy_list()
        
        if not proxies:
            print("   ✗ No proxies available")
            return None
        
        # Test up to 30 proxies (increased from 20)
        max_tests = min(30, len(proxies))
        print(f"   Testing up to {max_tests} proxies...")
        
        for i, proxy in enumerate(proxies[:max_tests], 1):
            print(f"   [{i}/{max_tests}] Testing {proxy}...", end=' ')
            if self.test_proxy(proxy):
                print("✓ WORKS!")
                return proxy
            else:
                print("✗")
        
        print("   ✗ No working proxy found")
        return None
    
    def create_driver_with_proxy(self, proxy=None):
        """Create Chrome driver with optional proxy"""
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
        user_agent = random.choice(self.user_agents)
        
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument(f'user-agent={user_agent}')
        
        # Add proxy if available
        if proxy:
            chrome_options.add_argument(f'--proxy-server=http://{proxy}')
            print(f"   ✓ Configured Chrome with proxy: {proxy}")
        
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        prefs = {
            'profile.default_content_setting_values': {
                'cookies': 1,
                'geolocation': 1,
                'notifications': 1
            }
        }
        chrome_options.add_experimental_option('prefs', prefs)
        
        service = Service('/usr/bin/chromedriver')
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        try:
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                    Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                    window.chrome = {runtime: {}};
                '''
            })
            driver.execute_cdp_cmd('Emulation.setGeolocationOverride', {
                'latitude': 23.8103,
                'longitude': 90.4125,
                'accuracy': 100
            })
        except Exception:
            pass
        
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

    def delay(self, min_sec=1.5, max_sec=3.0):
        time.sleep(random.uniform(min_sec, max_sec))

    def solve_recaptcha_audio(self):
        """
        Enhanced audio captcha solver based on successful implementations
        """
        try:
            print("\n🔓 Solving reCAPTCHA v2 (Enhanced Method)...")
            self.driver.switch_to.default_content()
            
            # Find and switch to checkbox iframe
            print("   [1/9] Finding checkbox iframe...")
            try:
                checkbox_iframe = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='recaptcha/api2/anchor']"))
                )
                self.driver.switch_to.frame(checkbox_iframe)
                print("   ✓ Found checkbox iframe")
            except TimeoutException:
                print("   ✓ No reCAPTCHA found")
                return True
            
            # Click checkbox
            print("   [2/9] Clicking checkbox...")
            try:
                checkbox = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.ID, "recaptcha-anchor"))
                )
                checkbox.click()
                print("   ✓ Clicked checkbox")
                self.delay(2, 4)
            except Exception as e:
                print(f"   ⚠ Checkbox click failed: {e}")
            
            self.driver.switch_to.default_content()
            
            # Wait and find challenge iframe
            print("   [3/9] Looking for challenge iframe...")
            try:
                challenge_iframe = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='recaptcha/api2/bframe']"))
                )
                self.driver.switch_to.frame(challenge_iframe)
                print("   ✓ Found challenge iframe")
                self.driver.save_screenshot('challenge_iframe.png')
            except TimeoutException:
                print("   ✓ No challenge appeared (auto-solved)")
                self.driver.switch_to.default_content()
                return True
            
            # Click audio button
            print("   [4/9] Clicking audio button...")
            try:
                audio_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "recaptcha-audio-button"))
                )
                audio_btn.click()
                print("   ✓ Clicked audio button")
                self.delay(3, 5)
                self.driver.save_screenshot('after_audio_click.png')
            except Exception as e:
                print(f"   ✗ Failed to click audio button: {e}")
                self.driver.switch_to.default_content()
                return False
            
            # Critical: Wait for audio challenge to fully load
            print("   [5/9] Waiting for audio challenge to load...")
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "rc-audiochallenge-tdownload-link"))
                )
                print("   ✓ Audio challenge loaded")
            except TimeoutException:
                print("   ⚠ Audio challenge not detected, checking for blocking...")
                page_text = self.driver.find_element(By.TAG_NAME, 'body').text
                if 'try again later' in page_text.lower():
                    print("   ❌ Google blocked audio challenge")
                    self.driver.save_screenshot('blocked_by_google.png')
                    self.driver.switch_to.default_content()
                    return False
            
            # Get audio source URL - Enhanced method
            print("   [6/9] Getting audio URL...")
            audio_url = None
            
            # Method 1: Check download link (most reliable)
            try:
                download_link = self.driver.find_element(By.CLASS_NAME, "rc-audiochallenge-tdownload-link")
                audio_url = download_link.get_attribute("href")
                if audio_url:
                    print(f"   ✓ Got audio URL from download link")
            except NoSuchElementException:
                pass
            
            # Method 2: Check audio source element
            if not audio_url:
                try:
                    audio_source = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.ID, "audio-source"))
                    )
                    # Wait for src to be populated
                    for attempt in range(20):
                        src = audio_source.get_attribute("src")
                        if src and len(src) > 0:
                            audio_url = src
                            print(f"   ✓ Got audio URL from source (attempt {attempt + 1})")
                            break
                        time.sleep(0.5)
                except Exception as e:
                    print(f"   ⚠ Could not get audio source: {e}")
            
            if not audio_url:
                print("   ✗ No audio URL found")
                with open('no_audio_page.html', 'w') as f:
                    f.write(self.driver.page_source)
                self.driver.switch_to.default_content()
                return False
            
            # Download audio
            print("   [7/9] Downloading audio...")
            try:
                # Use proxy for audio download if available
                proxies_dict = None
                if hasattr(self, 'proxy') and self.proxy:
                    proxies_dict = {
                        'http': f'http://{self.proxy}',
                        'https': f'http://{self.proxy}'
                    }
                    print(f"   → Using proxy for download: {self.proxy}")
                
                response = requests.get(audio_url, proxies=proxies_dict, timeout=30)
                if response.status_code != 200:
                    print(f"   ✗ Download failed: {response.status_code}")
                    self.driver.switch_to.default_content()
                    return False
                
                audio_data = response.content
                print(f"   ✓ Downloaded {len(audio_data)} bytes")
                
                # Convert to WAV
                audio = AudioSegment.from_file(io.BytesIO(audio_data))
                audio = audio.set_channels(1).set_frame_rate(16000)
                wav_io = io.BytesIO()
                audio.export(wav_io, format="wav")
                wav_io.seek(0)
                print("   ✓ Converted to WAV")
            except Exception as e:
                print(f"   ✗ Audio processing failed: {e}")
                self.driver.switch_to.default_content()
                return False
            
            # Speech recognition
            print("   [8/9] Running speech recognition...")
            try:
                recognizer = sr.Recognizer()
                recognizer.energy_threshold = 300
                
                with sr.AudioFile(wav_io) as source:
                    audio_data = recognizer.record(source)
                    text = recognizer.recognize_google(audio_data)
                
                text = text.lower().strip()
                print(f"   ✓ Recognized: '{text}'")
            except sr.UnknownValueError:
                print("   ✗ Could not understand audio")
                self.driver.switch_to.default_content()
                return False
            except Exception as e:
                print(f"   ✗ Recognition failed: {e}")
                self.driver.switch_to.default_content()
                return False
            
            # Submit answer
            print("   [9/9] Submitting answer...")
            try:
                response_input = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.ID, "audio-response"))
                )
                response_input.clear()
                response_input.send_keys(text)
                self.delay(1, 2)
                
                verify_btn = self.driver.find_element(By.ID, "recaptcha-verify-button")
                verify_btn.click()
                print("   ✓ Submitted answer")
                self.delay(3, 5)
                
                self.driver.switch_to.default_content()
                print("   ✓ reCAPTCHA solved successfully!")
                return True
                
            except Exception as e:
                print(f"   ✗ Submit failed: {e}")
                self.driver.switch_to.default_content()
                return False
            
        except Exception as e:
            print(f"   ✗ Unexpected error: {e}")
            traceback.print_exc()
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return False

    def find_and_click_element(self, by, selector, name="element"):
        """Helper to find and click elements reliably"""
        try:
            element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((by, selector))
            )
            if element.is_displayed():
                self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
                self.delay(0.5, 1)
                try:
                    element.click()
                except:
                    self.driver.execute_script("arguments[0].click();", element)
                print(f"   ✓ Clicked {name}")
                return True
        except Exception as e:
            print(f"   ✗ Failed to click {name}: {e}")
            return False

    def fetch_usage_data(self, customer_number):
        try:
            print(f"\n📡 Fetching data for customer: {customer_number}")
            
            # Navigate to login
            print("   → Loading login page...")
            self.driver.get('https://amiapp.dpdc.org.bd/login')
            self.delay(2, 4)
            self.driver.save_screenshot('01_login_page.png')
            
            # Click Quick Pay
            print("   → Finding Quick Pay...")
            if self.find_and_click_element(By.XPATH, "//button[contains(., 'QUICK PAY')]", "Quick Pay"):
                self.delay(2, 3)
            else:
                self.driver.get('https://amiapp.dpdc.org.bd/quick-pay')
                self.delay(2, 3)
            
            self.driver.save_screenshot('02_quick_pay_page.png')
            
            # Find customer input
            print("   → Entering customer number...")
            try:
                customer_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//input[@type='text' or @type='number']"))
                )
                customer_input.clear()
                for char in customer_number:
                    customer_input.send_keys(char)
                    time.sleep(random.uniform(0.1, 0.2))
                print("   ✓ Entered customer number")
                self.delay(1, 2)
                self.driver.save_screenshot('03_after_input.png')
            except Exception as e:
                print(f"   ✗ Could not enter customer number: {e}")
                raise
            
            # Solve captcha if present
            try:
                self.driver.switch_to.default_content()
                captcha_iframe = self.driver.find_elements(By.CSS_SELECTOR, "iframe[src*='recaptcha']")
                if captcha_iframe:
                    print("   ⚠ reCAPTCHA detected")
                    solved = self.solve_recaptcha_audio()
                    if solved:
                        print("   ✓ Captcha solved")
                    else:
                        print("   ⚠ Captcha not solved, continuing...")
                    self.delay(1, 2)
            except Exception as e:
                print(f"   Note: {e}")
            
            # Submit form
            print("   → Submitting...")
            try:
                submit_btn = self.driver.find_element(By.XPATH, "//button[@type='submit']")
                
                # Wait for button to be enabled
                for _ in range(10):
                    if not submit_btn.get_attribute('disabled'):
                        break
                    time.sleep(1)
                
                self.driver.execute_script("arguments[0].click();", submit_btn)
                print("   ✓ Clicked submit")
            except:
                customer_input.send_keys(Keys.RETURN)
                print("   ✓ Pressed Enter")
            
            # Wait for results
            print("   → Waiting for results...")
            self.delay(8, 12)
            self.driver.save_screenshot('04_results.png')
            
            # Extract data
            page_text = self.driver.find_element(By.TAG_NAME, 'body').text
            with open('page_text.txt', 'w', encoding='utf-8') as f:
                f.write(page_text)
            
            data = {'accountId': '', 'customerName': '', 'customerClass': '',
                    'mobileNumber': '', 'emailId': '', 'accountType': '',
                    'balanceRemaining': '', 'connectionStatus': '',
                    'customerType': '', 'minRecharge': ''}
            
            for line in page_text.split('\n'):
                if ':' in line:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        key, value = parts[0].strip().lower(), parts[1].strip()
                        if 'account' in key and value:
                            data['accountId'] = value
                        elif 'name' in key and value:
                            data['customerName'] = value
                        elif 'balance' in key and value:
                            data['balanceRemaining'] = value
                        elif 'mobile' in key and value:
                            data['mobileNumber'] = value
            
            if not any(data.values()):
                data['customerName'] = page_text[:300].replace('\n', ' ')
            
            print("   ✓ Data extracted")
            return data
            
        except Exception as e:
            print(f"✗ Error: {e}")
            traceback.print_exc()
            self.driver.save_screenshot('error.png')
            raise

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
            print("DPDC Automation with Enhanced Captcha Solver")
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
            print("✓ Completed!")
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
