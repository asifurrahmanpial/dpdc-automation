import os
import json
import random
import time
import io
import traceback
from datetime import datetime

import requests
import gspread
import speech_recognition as sr
from pydub import AudioSegment

from google.oauth2.service_account import Credentials

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Using Selenium Wire for better proxy control
from seleniumwire import webdriver
import undetected_chromedriver as uc
from selenium_stealth import stealth

class DPDCAutomation:
    def __init__(self):
        print("🚀 Initializing DPDC Automation with Proxy Rotation & Stealth Driver…")
        
        self.proxy = self.get_working_proxy_with_retry()
        if self.proxy:
            print(f"✓ Using proxy: {self.proxy}")
        else:
            print("⚠ No working proxy found, using direct connection")
        
        self.driver = self.create_driver_with_proxy(self.proxy)
        self.wait = WebDriverWait(self.driver, 30)
        self.setup_google_sheets()

    def fetch_proxy_list(self):
        """Fetch proxies from Geonode free proxy list."""
        proxies = []
        print("   Fetching proxy list from Geonode…")
        try:
            url = "https://proxylist.geonode.com/api/proxy-list?limit=100&page=1&sort_by=lastChecked&sort_type=desc"
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                data = response.json()
                for item in data.get('data', []):
                    ip = item.get('ip')
                    port = item.get('port')
                    if ip and port:
                        proxies.append(f"{ip}:{port}")
                print(f"   ✓ Geonode: {len(proxies)} proxies fetched")
            else:
                print(f"   ✗ Failed to fetch from Geonode: {response.status_code}")
        except Exception as e:
            print(f"   ⚠ Geonode fetch failed: {e}")
        
        if proxies:
            proxies = list(set(proxies))
            random.shuffle(proxies)
            print(f"   → Total unique proxies: {len(proxies)}")
        else:
            print("   ✗ No proxies found from Geonode")
        return proxies

    def test_proxy(self, proxy, timeout=8):
        """Test if a given proxy is working."""
        try:
            proxies_dict = {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }
            r = requests.get('http://httpbin.org/ip', proxies=proxies_dict, timeout=timeout)
            if r.status_code == 200:
                r2 = requests.get('https://www.google.com', proxies=proxies_dict, timeout=timeout)
                return r2.status_code == 200
        except Exception:
            pass
        return False

    def get_working_proxy_with_retry(self, max_batches=3, fallback_list=None):
        """
        Attempts multiple batches to find a working proxy.
        If free list fails, uses fallback list of proxies (if supplied).
        """
        # First try free list
        for batch in range(1, max_batches+1):
            print(f"🔍 Finding working proxy (batch {batch}/{max_batches}) …")
            proxies = self.fetch_proxy_list()
            if not proxies:
                print("   ✗ No proxies available in this batch")
                continue
            max_tests = min(30, len(proxies))
            print(f"   Testing up to {max_tests} proxies in this batch…")
            for i, proxy in enumerate(proxies[:max_tests], 1):
                print(f"   [{i}/{max_tests}] Testing {proxy} …", end=' ')
                if self.test_proxy(proxy):
                    print("✓ WORKS!")
                    return proxy
                else:
                    print("✗")
            print(f"   ✗ No working proxy found in batch {batch}")
            time.sleep(2)
        # Fallback phase
        if fallback_list:
            print("🔁 Free list failed — trying fallback proxies…")
            for i, proxy in enumerate(fallback_list, 1):
                print(f"   [Fallback {i}/{len(fallback_list)}] Testing {proxy} …", end=' ')
                if self.test_proxy(proxy):
                    print("✓ WORKS (fallback)!")
                    return proxy
                else:
                    print("✗")
        print("   ✗ All proxy attempts failed, no working proxy found")
        return None

    def create_driver_with_proxy(self, proxy=None):
        """
        Create a stealth Chrome driver via Selenium Wire + undetected-chromedriver.
        Applies user-agent rotation, uses stealth library, simulates human behaviour.
        """
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        user_agent = random.choice(user_agents)
        
        chrome_options = uc.ChromeOptions()
        # For better stealth, run headed or use xvfb if headless
        # chrome_options.headless = False
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument(f'user-agent={user_agent}')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option('excludeSwitches', ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # Setup Selenium Wire options for proxy
        seleniumwire_options = {}
        if proxy:
            seleniumwire_options['proxy'] = {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}',
                # optionally: 'no_proxy': 'localhost,127.0.0.1'
            }
            print(f"   ✓ Configured proxy for Selenium Wire: {proxy}")
        
        driver = webdriver.Chrome(options=chrome_options, seleniumwire_options=seleniumwire_options)

        # Apply selenium-stealth to further mask automation
        try:
            stealth(driver,
                    languages=["en-US", "en"],
                    vendor="Google Inc.",
                    platform="Win32",
                    webgl_vendor="Intel Inc.",
                    renderer="Intel Iris OpenGL Engine",
                    fix_hairline=True)
            print("   ✓ Applied selenium-stealth settings")
        except Exception as e:
            print(f"   ⚠ selenium-stealth not applied: {e}")
        
        # Simulate human-like behaviour: scrolls, slight pauses
        try:
            driver.execute_script("window.scrollTo(0, 200);")
            self.delay(0.5, 1.5)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            self.delay(0.5, 1.5)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            self.delay(0.5, 2.0)
        except Exception:
            pass
        
        # Optional: set geolocation to Bangladesh (example)
        try:
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

    # ... (keep your solve_recaptcha_audio, find_and_click_element, fetch_usage_data, update_google_sheet, run methods unchanged) ...

    # (For brevity I’m not duplicating the entire long methods here — assume they remain same as before.)

if __name__ == "__main__":
    automation = DPDCAutomation()
    success = automation.run()
    exit(0 if success else 1)
