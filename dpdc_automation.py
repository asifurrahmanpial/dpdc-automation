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
        try:
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
        except Exception as e:
            print("Warning: could not inject anti-detect script:", e)

        # Set geolocation to Dhaka
        try:
            self.driver.execute_cdp_cmd('Emulation.setGeolocationOverride', {
                'latitude': 23.8103,
                'longitude': 90.4125,
                'accuracy': 100
            })
        except Exception:
            pass

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

    def random_delay(self, min_sec=0.5, max_sec=1.5):
        """Human-like random delays"""
        time.sleep(random.uniform(min_sec, max_sec))

    def human_type(self, element, text):
        """Type like a human with random delays"""
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.08, 0.18))

    def close_and_quit(self):
        try:
            self.driver.quit()
        except:
            pass

    def wait_for_page_ready(self, timeout=20):
        """Wait until document.readyState is complete"""
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except TimeoutException:
            pass

        # Wait briefly for JS loaders
        end = time.time() + timeout
        while time.time() < end:
            try:
                loaders = self.driver.find_elements(By.XPATH, "//*[contains(@class,'loader') or contains(@class,'progress') or @role='progressbar']")
                visible = False
                for l in loaders:
                    if l.is_displayed():
                        visible = True
                        break
                if not visible:
                    return True
            except:
                return True
            time.sleep(0.5)
        return True

    def solve_recaptcha_v2(self):
        """
        Solve reCAPTCHA v2 using audio challenge - IMPROVED VERSION
        """
        try:
            print("\n🔓 Attempting to solve reCAPTCHA...")
            self.driver.switch_to.default_content()
            
            # Find and switch to anchor iframe (checkbox)
            try:
                print("   Step 1: Looking for reCAPTCHA anchor iframe...")
                recaptcha_iframe = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//iframe[contains(@src, 'recaptcha/api2/anchor') or @title='reCAPTCHA']"))
                )
                self.driver.switch_to.frame(recaptcha_iframe)
                print("   ✓ Switched to anchor iframe")
                
                # Click checkbox
                try:
                    print("   Step 2: Clicking checkbox...")
                    checkbox = WebDriverWait(self.driver, 4).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, ".recaptcha-checkbox-border"))
                    )
                    self.driver.execute_script("arguments[0].click();", checkbox)
                    print("   ✓ Clicked checkbox")
                    self.random_delay(2, 3)
                except Exception as e:
                    print(f"   ⚠ Could not click checkbox: {e}")
                
                self.driver.switch_to.default_content()
                
            except TimeoutException:
                print("   ✓ No reCAPTCHA anchor iframe found")
                self.driver.switch_to.default_content()
                return True

            # Wait for challenge iframe
            self.random_delay(2, 3)

            # Find challenge iframe (bframe)
            try:
                print("   Step 3: Looking for challenge iframe...")
                challenge_iframe = WebDriverWait(self.driver, 8).until(
                    EC.presence_of_element_located((By.XPATH, "//iframe[contains(@src, 'recaptcha/api2/bframe') or contains(@title, 'recaptcha challenge')]"))
                )
                self.driver.switch_to.frame(challenge_iframe)
                print("   ✓ Switched to challenge iframe")
                self.driver.save_screenshot('captcha_challenge_frame.png')
            except TimeoutException:
                print("   ✓ No challenge appeared (auto-solved)")
                self.driver.switch_to.default_content()
                return True

            # Now find the audio button - CRITICAL FIX
            try:
                print("   Step 4: Looking for audio button...")
                
                # Wait for buttons to be present in the footer
                self.random_delay(1, 2)
                
                # Multiple strategies to find audio button
                audio_button = None
                
                # Strategy 1: By ID (most reliable)
                try:
                    audio_button = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.ID, "recaptcha-audio-button"))
                    )
                    print("   ✓ Found audio button by ID")
                except TimeoutException:
                    pass
                
                # Strategy 2: By class
                if not audio_button:
                    try:
                        audio_button = self.driver.find_element(By.CSS_SELECTOR, ".rc-button-audio")
                        print("   ✓ Found audio button by class")
                    except NoSuchElementException:
                        pass
                
                # Strategy 3: By xpath in button holder
                if not audio_button:
                    try:
                        audio_button = self.driver.find_element(By.XPATH, "//div[@class='button-holder audio-button-holder']//button")
                        print("   ✓ Found audio button by button-holder")
                    except NoSuchElementException:
                        pass
                
                # Strategy 4: Any button with audio in title
                if not audio_button:
                    try:
                        audio_button = self.driver.find_element(By.XPATH, "//button[contains(@title, 'audio') or contains(@title, 'Audio')]")
                        print("   ✓ Found audio button by title")
                    except NoSuchElementException:
                        pass
                
                if not audio_button:
                    print("   ✗ Could not find audio button at all")
                    self.driver.save_screenshot('no_audio_button.png')
                    with open('captcha_page_source.html', 'w', encoding='utf-8') as f:
                        f.write(self.driver.page_source)
                    self.driver.switch_to.default_content()
                    return False
                
                # Check if button is visible (might be hidden initially)
                if not audio_button.is_displayed():
                    print("   ⚠ Audio button is hidden, trying to make it visible...")
                    # Sometimes we need to click somewhere first
                    try:
                        # Scroll into view
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", audio_button)
                        self.random_delay(0.5, 1)
                    except:
                        pass
                
                # Click audio button using JS (more reliable)
                print("   Step 5: Clicking audio button...")
                try:
                    self.driver.execute_script("arguments[0].click();", audio_button)
                    print("   ✓ Clicked audio button (JS click)")
                except Exception as e:
                    # Fallback to regular click
                    try:
                        audio_button.click()
                        print("   ✓ Clicked audio button (regular click)")
                    except Exception as e2:
                        print(f"   ✗ Failed to click audio button: {e}, {e2}")
                        self.driver.switch_to.default_content()
                        return False
                
                self.random_delay(2, 3)
                self.driver.save_screenshot('after_audio_click.png')
                
            except Exception as e:
                print(f"   ✗ Error finding/clicking audio button: {e}")
                traceback.print_exc()
                self.driver.switch_to.default_content()
                return False

            # Get audio source URL
            try:
                print("   Step 6: Getting audio source...")
                
                # Wait for audio element to appear
                audio_source = WebDriverWait(self.driver, 8).until(
                    EC.presence_of_element_located((By.ID, "audio-source"))
                )
                audio_url = audio_source.get_attribute('src')
                
                if not audio_url:
                    print("   ✗ Audio source has no URL")
                    self.driver.switch_to.default_content()
                    return False
                
                print(f"   ✓ Got audio URL: {audio_url[:80]}...")
                
            except TimeoutException:
                print("   ✗ Audio source element not found")
                self.driver.save_screenshot('no_audio_source.png')
                self.driver.switch_to.default_content()
                return False
            except Exception as e:
                print(f"   ✗ Error getting audio source: {e}")
                self.driver.switch_to.default_content()
                return False

            # Download and process audio
            try:
                print("   Step 7: Downloading audio...")
                response = requests.get(audio_url, timeout=15)
                audio_data = response.content
                
                print("   Step 8: Converting audio to WAV...")
                audio = AudioSegment.from_file(io.BytesIO(audio_data))
                audio = audio.set_channels(1).set_frame_rate(16000)
                wav_data = io.BytesIO()
                audio.export(wav_data, format="wav")
                wav_data.seek(0)
                print("   ✓ Audio converted")
                
            except Exception as e:
                print(f"   ✗ Error downloading/converting audio: {e}")
                self.driver.switch_to.default_content()
                return False

            # Speech recognition
            try:
                print("   Step 9: Running speech recognition...")
                recognizer = sr.Recognizer()
                with sr.AudioFile(wav_data) as source:
                    audio_listened = recognizer.record(source)
                    recognized_text = recognizer.recognize_google(audio_listened)
                print(f"   ✓ Recognized text: '{recognized_text}'")
                
            except Exception as e:
                print(f"   ✗ Speech recognition failed: {e}")
                self.driver.switch_to.default_content()
                return False

            # Submit response
            try:
                print("   Step 10: Submitting answer...")
                
                # Find response input
                response_input = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.ID, "audio-response"))
                )
                response_input.clear()
                
                # Type the answer (human-like)
                self.human_type(response_input, recognized_text.lower())
                self.random_delay(1, 2)
                
                # Find and click verify button
                verify_button = self.driver.find_element(By.ID, "recaptcha-verify-button")
                self.driver.execute_script("arguments[0].click();", verify_button)
                print("   ✓ Clicked verify button")
                
                self.random_delay(3, 5)
                self.driver.save_screenshot('after_verify.png')
                
            except Exception as e:
                print(f"   ✗ Error submitting response: {e}")
                self.driver.switch_to.default_content()
                return False

            # Done
            self.driver.switch_to.default_content()
            print("   ✓ reCAPTCHA solving completed!")
            return True

        except Exception as e:
            print(f"   ✗ Unexpected error in solve_recaptcha_v2: {e}")
            traceback.print_exc()
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return False

    def find_quick_pay_and_click(self):
        """Find and click Quick Pay button"""
        try:
            self.wait_for_page_ready(timeout=20)
            self.random_delay(0.5, 1.2)

            # XPath strategies
            xpath_exact = "//button[.//span[normalize-space()='QUICK PAY']]"
            xpath_contains = "//button[.//span[contains(translate(normalize-space(.), 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'QUICK')]]"

            for xpath in (xpath_exact, xpath_contains):
                try:
                    quick_btn = WebDriverWait(self.driver, 8).until(
                        EC.presence_of_element_located((By.XPATH, xpath))
                    )
                    if quick_btn and quick_btn.is_displayed():
                        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", quick_btn)
                        self.random_delay(0.4, 1.0)
                        try:
                            quick_btn.click()
                            print("✓ Clicked Quick Pay (direct)")
                            return True
                        except (ElementClickInterceptedException, Exception):
                            try:
                                self.driver.execute_script("arguments[0].click();", quick_btn)
                                print("✓ Clicked Quick Pay (JS)")
                                return True
                            except Exception as e:
                                print(f"   ✗ Failed to click: {e}")
                except TimeoutException:
                    continue
                except Exception as e:
                    print(f"   Error with xpath {xpath}: {e}")
                    continue

            # Fallback: direct navigation
            print("   ⚠ Quick Pay button not found - navigating directly")
            self.driver.get("https://amiapp.dpdc.org.bd/quick-pay")
            self.wait_for_page_ready(timeout=12)
            self.random_delay(1, 2)
            return True

        except Exception as e:
            print(f"   ✗ find_quick_pay_and_click error: {e}")
            traceback.print_exc()
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return False

    def fetch_usage_data(self, customer_number):
        """Fetch data with captcha solving"""
        try:
            print(f"\n📡 Fetching data for customer: {customer_number}")

            # Go to login page
            print("   Step 1: Loading login page...")
            self.driver.get('https://amiapp.dpdc.org.bd/login')
            self.wait_for_page_ready(timeout=20)
            self.random_delay(1.5, 3.0)
            self.driver.save_screenshot('step1_login_page.png')

            # Find and click Quick Pay
            print("   Step 2: Finding Quick Pay...")
            self.find_quick_pay_and_click()
            self.random_delay(2, 4)
            self.driver.save_screenshot('step2_quick_pay_page.png')

            self.wait_for_page_ready(timeout=12)

            # Find customer input
            print("   Step 3: Looking for customer number input...")
            customer_input = None
            possible_selectors = [
                "//input[@placeholder='Enter your Customer Number']",
                "//input[contains(@placeholder, 'Customer')]",
                "//input[contains(@placeholder, 'customer')]",
                "//input[@name='accountId' or @name='customerNumber']",
                "//input[@type='text']",
                "//input[@type='number']"
            ]
            
            for selector in possible_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed():
                            customer_input = element
                            print(f"   ✓ Found input with: {selector}")
                            break
                    if customer_input:
                        break
                except Exception:
                    continue

            if not customer_input:
                with open('page_source_quickpay.html', 'w', encoding='utf-8') as f:
                    f.write(self.driver.page_source)
                raise Exception("Could not find customer input")

            # Enter customer number
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", customer_input)
            self.random_delay(0.4, 0.8)
            try:
                customer_input.click()
            except:
                pass
            self.random_delay(0.2, 0.4)
            
            try:
                customer_input.clear()
            except:
                pass
            
            self.human_type(customer_input, customer_number)
            self.random_delay(0.6, 1.2)
            self.driver.save_screenshot('step3_after_input.png')
            print("   ✓ Entered customer number")

            # Check for and solve captcha
            try:
                self.driver.switch_to.default_content()
                try:
                    rc_frame = WebDriverWait(self.driver, 4).until(
                        EC.presence_of_element_located((By.XPATH, "//iframe[contains(@src,'recaptcha') or @title='reCAPTCHA']"))
                    )
                    print("   ⚠ reCAPTCHA detected, attempting to solve...")
                    solved = self.solve_recaptcha_v2()
                    if not solved:
                        print("   ⚠ Failed to solve reCAPTCHA")
                    self.random_delay(1.2, 2.0)
                except TimeoutException:
                    print("   ✓ No reCAPTCHA detected")
            except Exception as e:
                print(f"   Error checking captcha: {e}")
                self.driver.switch_to.default_content()

            # Find and click submit
            print("   Step 4: Looking for Submit button...")
            submit_btn = None
            
            try:
                btns = self.driver.find_elements(By.XPATH, "//button[contains(., 'Submit') or contains(translate(., 'abcdefghijklmnopqrstuvwxyz','ABCDEFGHIJKLMNOPQRSTUVWXYZ'),'SUBMIT')]")
                for btn in btns:
                    if btn.is_displayed():
                        submit_btn = btn
                        break
            except:
                pass

            if not submit_btn:
                try:
                    candidates = self.driver.find_elements(By.XPATH, "//button[@type='submit']")
                    for c in candidates:
                        if c.is_displayed():
                            submit_btn = c
                            break
                except:
                    pass

            if not submit_btn:
                print("   ⚠ Submit button not found - pressing ENTER")
                self.driver.save_screenshot('no_submit_found.png')
                try:
                    customer_input.send_keys(Keys.RETURN)
                except:
                    pass
            else:
                # Wait for button to be enabled
                enabled = False
                for _ in range(12):
                    try:
                        is_disabled = submit_btn.get_attribute('disabled')
                        if not is_disabled:
                            enabled = True
                            break
                    except:
                        enabled = True
                        break
                    time.sleep(1)
                
                if enabled:
                    try:
                        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", submit_btn)
                        self.random_delay(0.3, 0.6)
                        try:
                            submit_btn.click()
                        except:
                            self.driver.execute_script("arguments[0].click();", submit_btn)
                        print("   ✓ Clicked Submit")
                    except Exception as e:
                        print(f"   ✗ Could not click submit: {e}")
                        try:
                            customer_input.send_keys(Keys.RETURN)
                        except:
                            pass
                else:
                    print("   ⚠ Submit button disabled - pressing ENTER")
                    try:
                        customer_input.send_keys(Keys.RETURN)
                    except:
                        pass

            # Wait for results
            print("   Step 5: Waiting for results...")
            self.random_delay(6, 10)
            self.driver.save_screenshot('step4_results.png')

            # Scrape data
            data = self.scrape_page_data()
            return data

        except Exception as e:
            print(f"✗ Error in fetch_usage_data: {e}")
            self.driver.save_screenshot('error_screenshot.png')
            with open('error_page_source.html', 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            traceback.print_exc()
            raise

    def scrape_page_data(self):
        """Extract data from page"""
        try:
            print("   Step 6: Extracting data...")

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

            print("   ✓ Data extraction finished")
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
            if data:
                self.update_google_sheet(spreadsheet_id, data)
            else:
                print("⚠ No data scraped")

            print("\n" + "="*60)
            print("✓ Automation completed!")
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
