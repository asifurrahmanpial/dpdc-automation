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

        # Enable audio for captcha solving (best-effort)
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

        # Set geolocation to Dhaka (best-effort)
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
        """Wait until document.readyState is complete and no visible loader/progress shows"""
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except TimeoutException:
            pass

        # Wait briefly for possible JS loaders to finish
        end = time.time() + timeout
        while time.time() < end:
            try:
                # common progress indicators
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
        Solve reCAPTCHA v2 using audio challenge method (best-effort).
        Returns True on success or if no challenge detected. Always switches back to default content.
        """
        try:
            print("\n🔓 Attempting to solve reCAPTCHA (best-effort)...")
            self.driver.switch_to.default_content()
            # Look for reCAPTCHA anchor iframe
            try:
                recaptcha_iframe = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//iframe[contains(@src, 'recaptcha') or @title='reCAPTCHA']"))
                )
                # switch to the anchor frame (checkbox)
                self.driver.switch_to.frame(recaptcha_iframe)
                print("   ✓ In reCAPTCHA anchor iframe")
                # try clicking the checkbox
                try:
                    checkbox = WebDriverWait(self.driver, 4).until(
                        EC.element_to_be_clickable((By.XPATH, "//div[contains(@class,'recaptcha-checkbox')] | //div[contains(@class,'recaptcha-checkbox-border')] | //span[contains(@class,'recaptcha-checkbox')]"))
                    )
                    self.driver.execute_script("arguments[0].click();", checkbox)
                    print("   ✓ Clicked checkbox (anchor)")
                except Exception as e:
                    print("   Could not click anchor checkbox:", e)
                finally:
                    self.driver.switch_to.default_content()
            except TimeoutException:
                # no recaptcha iframe found
                print("   ✓ No reCAPTCHA anchor iframe found")
                self.driver.switch_to.default_content()
                return True

            # Allow time for challenge iframe to appear
            self.random_delay(1.5, 3)

            # Try to find the challenge frame (bframe)
            try:
                challenge_iframe = WebDriverWait(self.driver, 6).until(
                    EC.presence_of_element_located((By.XPATH, "//iframe[contains(@src, 'bframe') or contains(@title, 'reCAPTCHA') or contains(@name,'a-')]"))
                )
                self.driver.switch_to.frame(challenge_iframe)
                print("   ✓ Switched to challenge iframe")
            except TimeoutException:
                print("   ✓ No challenge iframe appeared (checkbox click may have auto-solved)")
                self.driver.switch_to.default_content()
                return True

            # Try switching to audio challenge
            try:
                audio_button = WebDriverWait(self.driver, 6).until(
                    EC.element_to_be_clickable((By.ID, "recaptcha-audio-button"))
                )
                self.driver.execute_script("arguments[0].click();", audio_button)
                self.random_delay(1.2, 2.0)
                print("   ✓ Clicked audio challenge button")
            except TimeoutException:
                print("   ✗ No audio button available in challenge iframe")
                self.driver.switch_to.default_content()
                return False
            except Exception as e:
                print("   ✗ Error clicking audio button:", e)
                self.driver.switch_to.default_content()
                return False

            # get audio source
            try:
                audio_source = WebDriverWait(self.driver, 6).until(
                    EC.presence_of_element_located((By.ID, "audio-source"))
                )
                audio_url = audio_source.get_attribute('src')
                print("   ✓ Got audio source URL")
            except Exception as e:
                print("   ✗ Could not get audio source:", e)
                self.driver.switch_to.default_content()
                return False

            # download audio
            try:
                response = requests.get(audio_url, timeout=15)
                audio_data = response.content
                # convert mp3 to wav
                audio = AudioSegment.from_file(io.BytesIO(audio_data))
                audio = audio.set_channels(1).set_frame_rate(16000)
                wav_data = io.BytesIO()
                audio.export(wav_data, format="wav")
                wav_data.seek(0)
                print("   ✓ Downloaded and converted audio")
            except Exception as e:
                print("   ✗ Error downloading/converting audio:", e)
                self.driver.switch_to.default_content()
                return False

            # use speech recognition
            try:
                recognizer = sr.Recognizer()
                with sr.AudioFile(wav_data) as source:
                    audio_listened = recognizer.record(source)
                    recognized_text = recognizer.recognize_google(audio_listened)
                print(f"   ✓ Recognized text: {recognized_text}")
            except Exception as e:
                print("   ✗ Speech recognition failed:", e)
                self.driver.switch_to.default_content()
                return False

            # fill response
            try:
                response_input = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.ID, "audio-response"))
                )
                response_input.clear()
                self.human_type(response_input, recognized_text.lower())
                self.random_delay(0.8, 1.5)
                verify_button = self.driver.find_element(By.ID, "recaptcha-verify-button")
                self.driver.execute_script("arguments[0].click();", verify_button)
                print("   ✓ Submitted audio response")
                self.random_delay(2.5, 4.0)
            except Exception as e:
                print("   ✗ Could not submit audio response:", e)
                self.driver.switch_to.default_content()
                return False

            # done
            self.driver.switch_to.default_content()
            print("   ✓ reCAPTCHA attempt finished (verify on page if succeeded)")
            return True

        except Exception as e:
            print("   ✗ Error solving reCAPTCHA:", e)
            traceback.print_exc()
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return False

    def find_quick_pay_and_click(self):
        """
        Robust method to find and click Quick Pay.
        - waits for page to be ready / loaders to disappear
        - searches for the button by span text (QUICK PAY) — resilient to class changes
        - handles iframe wrapping and JS fallback click
        """
        try:
            self.wait_for_page_ready(timeout=20)
            self.random_delay(0.5, 1.2)

            # Strategy 1: find a button with a span text QUICK PAY (exact)
            xpath_exact = "//button[.//span[normalize-space()='QUICK PAY']]"
            xpath_contains_quick = "//button[.//span[contains(translate(normalize-space(.), 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'QUICK')]]"

            # Try exact match first, then case-insensitive contains
            for xpath in (xpath_exact, xpath_contains_quick):
                try:
                    # Wait for presence in DOM
                    quick_btn = WebDriverWait(self.driver, 8).until(
                        EC.presence_of_element_located((By.XPATH, xpath))
                    )
                    # ensure visible/clickable - try to click, if not clickable try other ways
                    if quick_btn and quick_btn.is_displayed():
                        # scroll into view
                        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", quick_btn)
                        self.random_delay(0.4, 1.0)
                        try:
                            quick_btn.click()
                            print("✓ Clicked Quick Pay (direct click)")
                            return True
                        except (ElementClickInterceptedException, Exception):
                            try:
                                self.driver.execute_script("arguments[0].click();", quick_btn)
                                print("✓ Clicked Quick Pay (JS click fallback)")
                                return True
                            except Exception as e:
                                print("   ✗ Failed to click quick btn:", e)
                                # fallback to continue searching (maybe inside iframe)
                    else:
                        continue
                except TimeoutException:
                    continue
                except Exception as e:
                    print("   Error while trying xpath:", xpath, e)
                    continue

            # If not found, check if button might be inside an iframe
            try:
                iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                print(f"   Found {len(iframes)} iframes, scanning for quick-pay inside them...")
                for idx, frame in enumerate(iframes):
                    try:
                        # switch to frame and check presence
                        self.driver.switch_to.default_content()
                        self.random_delay(0.2, 0.4)
                        self.driver.switch_to.frame(frame)
                        # try to find button here
                        try:
                            quick_in_frame = self.driver.find_element(By.XPATH, xpath_exact)
                        except:
                            try:
                                quick_in_frame = self.driver.find_element(By.XPATH, xpath_contains_quick)
                            except:
                                quick_in_frame = None
                        if quick_in_frame and quick_in_frame.is_displayed():
                            # click it
                            try:
                                self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", quick_in_frame)
                                self.random_delay(0.2, 0.6)
                                try:
                                    quick_in_frame.click()
                                except:
                                    self.driver.execute_script("arguments[0].click();", quick_in_frame)
                                print(f"✓ Clicked Quick Pay inside iframe idx={idx}")
                                self.driver.switch_to.default_content()
                                return True
                            except Exception as e:
                                print("   ✗ Error clicking quick in iframe:", e)
                        # else continue
                    except Exception:
                        # can't switch to some frames due to cross-origin; continue scanning
                        continue
                # switch back
                self.driver.switch_to.default_content()
            except Exception as e:
                print("   ✗ Error scanning iframes for quick-pay:", e)

            # Final fallback: direct navigate to quick-pay URL
            print("   ⚠ Quick Pay button not found - navigating directly to quick-pay URL")
            self.driver.get("https://amiapp.dpdc.org.bd/quick-pay")
            self.wait_for_page_ready(timeout=12)
            self.random_delay(1, 2)
            return True

        except Exception as e:
            print("   ✗ find_quick_pay_and_click error:", e)
            traceback.print_exc()
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return False

    def fetch_usage_data(self, customer_number):
        """Fetch data with captcha solving and robust navigation"""
        try:
            print(f"\n📡 Fetching data for customer: {customer_number}")

            # Go to login page first (establish session)
            print("   Step 1: Loading login page...")
            self.driver.get('https://amiapp.dpdc.org.bd/login')
            self.wait_for_page_ready(timeout=20)
            self.random_delay(1.5, 3.0)
            self.driver.save_screenshot('step1_login_page.png')

            # Try to find and click quick pay
            print("   Step 2: Finding Quick Pay...")
            found_quick = self.find_quick_pay_and_click()
            if not found_quick:
                print("   ✗ Could not locate Quick Pay (but continuing to quick-pay page)")
            self.random_delay(2, 4)
            self.driver.save_screenshot('step2_quick_pay_page.png')

            # Ensure we are on quick-pay page (fallback returned true even if direct nav)
            try:
                # Wait until either the desired input or the quick-pay URL is present
                self.wait_for_page_ready(timeout=12)
            except:
                pass

            # Step: find customer input
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
                            break
                    if customer_input:
                        print(f"   ✓ Found input with selector: {selector}")
                        break
                except Exception:
                    continue

            if not customer_input:
                # save page source for debugging
                with open('page_source_quickpay.html', 'w', encoding='utf-8') as f:
                    f.write(self.driver.page_source)
                raise Exception("Could not find customer number input on quick-pay page")

            # focus and type customer number
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", customer_input)
            self.random_delay(0.4, 0.8)
            try:
                customer_input.click()
            except:
                pass
            self.random_delay(0.2, 0.4)
            # clear then type
            try:
                customer_input.clear()
            except:
                pass
            self.human_type(customer_input, customer_number)
            self.random_delay(0.6, 1.2)
            self.driver.save_screenshot('step3_after_input.png')
            print("   ✓ Entered customer number")

            # After entering, check for captcha frame and attempt solve
            try:
                self.driver.switch_to.default_content()
                # look for recaptcha iframe presence
                recaptcha_detected = False
                try:
                    rc_frame = WebDriverWait(self.driver, 4).until(
                        EC.presence_of_element_located((By.XPATH, "//iframe[contains(@src,'recaptcha') or @title='reCAPTCHA']"))
                    )
                    recaptcha_detected = True
                    print("   ⚠ reCAPTCHA detected, attempting solver...")
                except TimeoutException:
                    print("   ✓ No reCAPTCHA iframe detected after input")
                except Exception:
                    print("   ✓ No reCAPTCHA found (exception)")

                if recaptcha_detected:
                    solved = self.solve_recaptcha_v2()
                    if not solved:
                        print("   ⚠ Failed to auto-solve reCAPTCHA (continuing but captcha may block submit)")
                    self.random_delay(1.2, 2.0)
            except Exception as e:
                print("   Error checking/solving captcha:", e)
                self.driver.switch_to.default_content()

            # Find submit button and wait until it's enabled
            print("   Step 4: Looking for Submit button...")
            submit_btn = None
            try:
                # Common selectors for submit
                btns = self.driver.find_elements(By.XPATH, "//button[.//span[translate(normalize-space(.), 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ')='SUBMIT'] | //button[contains(., 'Submit') or contains(translate(., 'abcdefghijklmnopqrstuvwxyz','ABCDEFGHIJKLMNOPQRSTUVWXYZ'),'SUBMIT')]")
                for btn in btns:
                    # skip hidden or not displayed
                    if not btn.is_displayed():
                        continue
                    submit_btn = btn
                    break
            except Exception:
                submit_btn = None

            # If no submit button found using text, fallback to first visible button of type submit
            if not submit_btn:
                try:
                    candidates = self.driver.find_elements(By.XPATH, "//button[@type='submit']")
                    for c in candidates:
                        if c.is_displayed():
                            submit_btn = c
                            break
                except:
                    submit_btn = None

            if not submit_btn:
                print("   ⚠ Submit button not found - saving page and continuing with ENTER key")
                self.driver.save_screenshot('no_submit_found.png')
                try:
                    customer_input.send_keys(Keys.RETURN)
                except:
                    pass
            else:
                # Wait up to 12s for button to become enabled (Material UI sets disabled class)
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
                    # scroll and click (JS fallback)
                    try:
                        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", submit_btn)
                        self.random_delay(0.3, 0.6)
                        try:
                            submit_btn.click()
                        except:
                            self.driver.execute_script("arguments[0].click();", submit_btn)
                        print("   ✓ Clicked Submit")
                    except Exception as e:
                        print("   ✗ Could not click submit:", e)
                        try:
                            customer_input.send_keys(Keys.RETURN)
                        except:
                            pass
                else:
                    print("   ⚠ Submit button remained disabled after wait; sending ENTER as fallback")
                    try:
                        customer_input.send_keys(Keys.RETURN)
                    except:
                        pass

            # Wait for results to load
            print("   Step 5: Waiting for results...")
            self.random_delay(6, 10)
            self.driver.save_screenshot('step4_results.png')

            # Scrape the page data using your existing scraper
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
            print("   Step: Extracting data from results page...")

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
                print("⚠ No data scraped; skipping sheet update")

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
