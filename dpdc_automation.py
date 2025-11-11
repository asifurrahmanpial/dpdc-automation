#!/usr/bin/env python3
# dpdc_automation.py
# DPDC automation: Quick Pay -> customer lookup -> cookie-based audio reCAPTCHA solver -> Google Sheets
# Designed to run non-headless (use Xvfb in CI). Requires ffmpeg, chromedriver, chrome.

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

# ---------------------------
# Configuration defaults
# ---------------------------
CHROMEDRIVER_PATH = os.environ.get('CHROMEDRIVER_PATH', '/usr/bin/chromedriver')
DEFAULT_TIMEOUT = 30

# ---------------------------
# Main class
# ---------------------------
class DPDCAutomation:
    def __init__(self, chromedriver_path=CHROMEDRIVER_PATH, headless=False):
        print("🚀 Initializing DPDC Automation with Captcha Solver...")

        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]

        user_agent = random.choice(self.user_agents)

        chrome_options = Options()
        # default: non-headless (better for audio captcha). If you want headless, pass headless=True to constructor
        if headless:
            chrome_options.add_argument('--headless=new')

        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument(f'user-agent={user_agent}')

        # anti-detection (best-effort)
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # try to enable audio permissions (best-effort)
        chrome_options.add_argument('--use-fake-ui-for-media-stream')
        chrome_options.add_argument('--use-fake-device-for-media-stream')

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

        service = Service(chromedriver_path)
        self.driver = webdriver.Chrome(service=service, options=chrome_options)

        # inject lightweight anti-detect script (best effort)
        try:
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
                    Object.defineProperty(navigator, 'languages', {get: () => ['en-US','en']});
                    window.chrome = window.chrome || { runtime: {} };
                '''
            })
        except Exception:
            pass

        # Optional: set geolocation (Dhaka)
        try:
            self.driver.execute_cdp_cmd('Emulation.setGeolocationOverride', {
                'latitude': 23.8103,
                'longitude': 90.4125,
                'accuracy': 100
            })
        except Exception:
            pass

        self.wait = WebDriverWait(self.driver, DEFAULT_TIMEOUT)
        self.setup_google_sheets()

    # ---------------------------
    # Google Sheets setup
    # ---------------------------
    def setup_google_sheets(self):
        try:
            credentials_json = os.environ.get('GOOGLE_CREDENTIALS')
            if not credentials_json:
                raise Exception("GOOGLE_CREDENTIALS not found in environment")

            creds_dict = json.loads(credentials_json)
            scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            self.gc = gspread.authorize(creds)
            print("✓ Google Sheets connected")
        except Exception as e:
            print(f"✗ Error setting up Google Sheets: {e}")
            raise

    # ---------------------------
    # Utility helpers
    # ---------------------------
    def random_delay(self, min_sec=0.5, max_sec=1.5):
        time.sleep(random.uniform(min_sec, max_sec))

    def human_type(self, element, text):
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.06, 0.16))

    def wait_for_page_ready(self, timeout=20):
        try:
            WebDriverWait(self.driver, timeout).until(lambda d: d.execute_script("return document.readyState") == "complete")
        except TimeoutException:
            pass

        end = time.time() + timeout
        while time.time() < end:
            try:
                loaders = self.driver.find_elements(By.XPATH, "//*[contains(@class,'loader') or contains(@class,'progress') or @role='progressbar']")
                visible = any(l.is_displayed() for l in loaders)
                if not visible:
                    return True
            except Exception:
                return True
            time.sleep(0.4)
        return True

    # ---------------------------
    # Cookie-based audio download helper
    # ---------------------------
    def download_audio_using_browser_cookies(self, audio_url, timeout=20):
        try:
            sess = requests.Session()
            for c in self.driver.get_cookies():
                try:
                    sess.cookies.set(c['name'], c['value'], domain=c.get('domain'))
                except:
                    sess.cookies.set(c['name'], c['value'])
            headers = {
                'User-Agent': self.driver.execute_script("return navigator.userAgent;"),
                'Accept': '*/*',
                'Referer': 'https://www.google.com/recaptcha/api2/bframe',
                'DNT': '1',
                'Connection': 'keep-alive',
            }
            fixed = audio_url.replace('&amp;', '&')
            resp = sess.get(fixed, headers=headers, timeout=timeout, stream=True)
            ctype = resp.headers.get('content-type', '')
            if resp.status_code != 200 or ('audio' not in ctype and 'mpeg' not in ctype and 'octet' not in ctype):
                snippet = resp.content[:800].decode('utf-8', errors='replace')
                print(f"   ✗ Audio download rejected (HTTP {resp.status_code}, content-type: {ctype})")
                print("   Preview:", snippet[:600])
                return None
            data = resp.content
            if len(data) < 100:
                print(f"   ✗ Audio file too small ({len(data)} bytes) - likely error")
                return None
            return data
        except Exception as e:
            print("   ✗ Exception while downloading audio:", e)
            return None

    # ---------------------------
    # reCAPTCHA v2 solver (cookie-based audio approach)
    # ---------------------------
    def solve_recaptcha_v2(self):
        driver = self.driver
        wait = self.wait

        try:
            print("\n🔓 Attempting to solve reCAPTCHA (cookie-based audio)...")
            driver.switch_to.default_content()

            # Step 1: anchor iframe -> checkbox
            try:
                anchor_iframe = wait.until(EC.presence_of_element_located((By.XPATH, "//iframe[contains(@src,'recaptcha/api2/anchor') or @title='reCAPTCHA']")))
                driver.switch_to.frame(anchor_iframe)
                try:
                    checkbox = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".recaptcha-checkbox-border, #recaptcha-anchor, .recaptcha-checkbox")))
                    driver.execute_script("arguments[0].click();", checkbox)
                    print("   ✓ Clicked recaptcha checkbox (anchor)")
                except Exception as e:
                    print("   ⚠ Could not click checkbox inside anchor iframe:", e)
                driver.switch_to.default_content()
            except TimeoutException:
                print("   ✓ No anchor iframe found (maybe auto-solved)")
                driver.switch_to.default_content()
                return True

            self.random_delay(1.5, 3.0)

            # Step 2: challenge iframe
            try:
                challenge_iframe = wait.until(EC.presence_of_element_located((By.XPATH, "//iframe[contains(@src,'recaptcha/api2/bframe') or contains(@title,'recaptcha challenge') or contains(@name,'a-')]")))
                driver.switch_to.frame(challenge_iframe)
                print("   ✓ Switched to challenge iframe")
            except TimeoutException:
                print("   ✓ No challenge iframe (auto-solved).")
                driver.switch_to.default_content()
                return True

            # Step 3: find and click audio button
            self.random_delay(0.6, 1.5)
            audio_button = None
            try:
                audio_button = driver.find_element(By.ID, "recaptcha-audio-button")
                print("   ✓ Found audio button by ID")
            except Exception:
                try:
                    audio_button = driver.find_element(By.CSS_SELECTOR, ".rc-button-audio")
                    print("   ✓ Found audio button by class")
                except Exception:
                    audio_button = None

            if not audio_button:
                print("   ✗ Audio button not found in challenge iframe")
                driver.switch_to.default_content()
                return False

            try:
                driver.execute_script("arguments[0].click();", audio_button)
                print("   ✓ Clicked audio button")
            except Exception:
                try:
                    audio_button.click()
                    print("   ✓ Clicked audio button (regular)")
                except Exception as e:
                    print("   ✗ Failed to click audio button:", e)
                    driver.switch_to.default_content()
                    return False

            # wait for audio UI
            self.random_delay(2.0, 4.0)

            # Step 4: locate audio source (multiple strategies)
            audio_url = None
            for attempt in range(12):
                try:
                    try:
                        audio_elem = driver.find_element(By.ID, "audio-source")
                        src = audio_elem.get_attribute("src")
                        if src and 'payload' in src:
                            audio_url = src
                            break
                    except Exception:
                        pass

                    try:
                        auds = driver.find_elements(By.TAG_NAME, "audio")
                        for a in auds:
                            s = a.get_attribute("src")
                            if s and 'payload' in s:
                                audio_url = s
                                break
                        if audio_url:
                            break
                    except:
                        pass

                    try:
                        dl = driver.find_element(By.CSS_SELECTOR, ".rc-audiochallenge-tdownload-link, .rc-audiochallenge-tdownload a")
                        href = dl.get_attribute("href")
                        if href:
                            audio_url = href
                            break
                    except:
                        pass
                except:
                    pass
                time.sleep(1)

            if not audio_url:
                try:
                    page = driver.page_source
                    import re
                    matches = re.findall(r'https://www\.google\.com/recaptcha/api2/payload\?[^"\'>\s]+', page)
                    if matches:
                        audio_url = matches[0].replace('&amp;', '&')
                except Exception:
                    audio_url = None

            if not audio_url:
                print("   ✗ Could not find audio URL after retries")
                driver.save_screenshot('no_audio_source_debug.png')
                with open('audio_challenge_page.html', 'w', encoding='utf-8') as f:
                    f.write(driver.page_source)
                driver.switch_to.default_content()
                return False

            print("   ✓ Found audio URL")

            # Step 5: download with browser cookies
            audio_bytes = self.download_audio_using_browser_cookies(audio_url)
            if not audio_bytes:
                print("   ✗ Download of audio failed (server rejected request).")
                driver.switch_to.default_content()
                return False

            # Step 6: convert + transcribe
            try:
                audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes))
                audio_segment = audio_segment.set_channels(1).set_frame_rate(16000)
                wav_io = io.BytesIO()
                audio_segment.export(wav_io, format="wav")
                wav_io.seek(0)

                recognizer = sr.Recognizer()
                with sr.AudioFile(wav_io) as source:
                    recorded = recognizer.record(source)
                recognized_text = recognizer.recognize_google(recorded)
                print(f"   ✓ Transcribed audio: {recognized_text}")
            except Exception as e:
                print("   ✗ Speech recognition failed:", e)
                driver.switch_to.default_content()
                return False

            # Step 7: enter and submit
            try:
                input_field = driver.find_element(By.ID, "audio-response")
                input_field.clear()
                self.human_type(input_field, recognized_text.lower())
                self.random_delay(0.6, 1.2)
                verify_btn = driver.find_element(By.ID, "recaptcha-verify-button")
                driver.execute_script("arguments[0].click();", verify_btn)
                print("   ✓ Submitted audio answer")
            except Exception as e:
                print("   ✗ Could not submit audio response:", e)
                driver.switch_to.default_content()
                return False

            self.random_delay(2.5, 5.0)
            driver.switch_to.default_content()
            print("   ✓ reCAPTCHA attempt finished (verify on page if succeeded)")
            return True

        except Exception as e:
            print("   ✗ Unexpected error in solve_recaptcha_v2:", e)
            traceback.print_exc()
            try:
                driver.switch_to.default_content()
            except:
                pass
            return False

    # ---------------------------
    # Quick Pay detection & click
    # ---------------------------
    def find_quick_pay_and_click(self):
        try:
            self.wait_for_page_ready(timeout=20)
            self.random_delay(0.5, 1.2)

            xpath_exact = "//button[.//span[normalize-space()='QUICK PAY']]"
            xpath_contains = "//button[.//span[contains(translate(normalize-space(.), 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'QUICK')]]"

            for xpath in (xpath_exact, xpath_contains):
                try:
                    quick_btn = WebDriverWait(self.driver, 8).until(EC.presence_of_element_located((By.XPATH, xpath)))
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
                                print("   ✗ Failed to click:", e)
                except TimeoutException:
                    continue
                except Exception as e:
                    print(f"   Error with xpath {xpath}: {e}")
                    continue

            print("   ⚠ Quick Pay button not found - navigating directly")
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

    # ---------------------------
    # Fetch usage data flow
    # ---------------------------
    def fetch_usage_data(self, customer_number):
        try:
            print(f"\n📡 Fetching data for customer: {customer_number}")

            # Step 1: load login page
            print("   Step 1: Loading login page...")
            self.driver.get('https://amiapp.dpdc.org.bd/login')
            self.wait_for_page_ready(timeout=20)
            self.random_delay(1.5, 3.0)
            self.driver.save_screenshot('step1_login_page.png')

            # Step 2: open Quick Pay
            print("   Step 2: Finding Quick Pay...")
            self.find_quick_pay_and_click()
            self.random_delay(2, 4)
            self.driver.save_screenshot('step2_quick_pay_page.png')

            self.wait_for_page_ready(timeout=12)

            # Step 3: find customer input
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

            # Step 4: captcha detection & solve
            try:
                self.driver.switch_to.default_content()
                try:
                    rc_frame = WebDriverWait(self.driver, 4).until(EC.presence_of_element_located((By.XPATH, "//iframe[contains(@src,'recaptcha') or @title='reCAPTCHA']")))
                    print("   ⚠ reCAPTCHA detected, attempting to solve...")
                    solved = self.solve_recaptcha_v2()
                    if not solved:
                        print("   ⚠ Failed to solve reCAPTCHA automatically")
                    self.random_delay(1.2, 2.0)
                except TimeoutException:
                    print("   ✓ No reCAPTCHA detected")
            except Exception as e:
                print(f"   Error checking captcha: {e}")
                self.driver.switch_to.default_content()

            # Step 5: find & click submit
            print("   Step 5: Finding Submit button...")
            submit_btn = None
            try:
                btns = self.driver.find_elements(By.XPATH, "//button[contains(translate(normalize-space(.),'abcdefghijklmnopqrstuvwxyz','ABCDEFGHIJKLMNOPQRSTUVWXYZ'),'SUBMIT') or contains(., 'Submit')]")
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
                        print("   ✗ Could not click submit:", e)
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

            # Step 6: wait & scrape
            print("   Step 6: Waiting for results...")
            self.random_delay(6, 10)
            self.driver.save_screenshot('step4_results.png')
            data = self.scrape_page_data()
            return data

        except Exception as e:
            print(f"✗ Error in fetch_usage_data: {e}")
            self.driver.save_screenshot('error_screenshot.png')
            with open('error_page_source.html', 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            traceback.print_exc()
            raise

    # ---------------------------
    # Scraper
    # ---------------------------
    def scrape_page_data(self):
        try:
            print("   Extracting data from results page...")
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

    # ---------------------------
    # Google Sheets update
    # ---------------------------
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
            print(f"✗ Error updating sheet: {e}")
            raise

    # ---------------------------
    # Runner
    # ---------------------------
    def run(self):
        try:
            print("\n" + "="*60)
            print("DPDC Usage Data Automation with Captcha Solver")
            print(f"Started at: {datetime.now()}")
            print("="*60)

            customer_number = os.environ.get('CUSTOMER_NUMBER')
            spreadsheet_id = os.environ.get('SPREADSHEET_ID')
            if not customer_number or not spreadsheet_id:
                raise Exception("Missing environment variables: CUSTOMER_NUMBER and/or SPREADSHEET_ID")

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

# ---------------------------
# Entrypoint
# ---------------------------
if __name__ == "__main__":
    automation = DPDCAutomation(headless=False)  # headless=False -> uses visible browser (works with Xvfb)
    success = automation.run()
    exit(0 if success else 1)
