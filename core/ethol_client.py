# -*- coding: utf-8 -*-
"""
ETHOL PENS Client
Mengurus otentikasi CAS SSO, Fast API monitoring, dan eksekusi presensi via browser.
"""

import os
import time
import datetime
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

from core.config import (
    BASE_URL, LOGIN_URL, PENS_USERNAME, PENS_PASSWORD, PENS_NETID,
    OPERA_GX_PATH, load_matkul_list, LOG_FILE
)


def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


class EtholClient:
    def __init__(self):
        self.cached_cookies = {}

    def make_driver(self):
        options = Options()
        if os.name == 'nt' and os.path.exists(OPERA_GX_PATH):
            options.binary_location = OPERA_GX_PATH
        
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1280,900")
        options.add_argument("--log-level=3")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])

        try:
            if os.name == 'nt':
                # Driver untuk Opera GX lokal
                service = Service(ChromeDriverManager(driver_version="155.0.8059.85").install())
            else:
                service = Service(ChromeDriverManager().install())
        except Exception:
            service = Service()

        driver = webdriver.Chrome(service=service, options=options)
        driver.implicitly_wait(5)
        return driver

    def refresh_session(self):
        """Melakukan login ke CAS SSO PENS dan memperbarui cookie session"""
        log("Memperbarui sesi login CAS PENS...")
        driver = self.make_driver()
        try:
            driver.get(LOGIN_URL)
            wait = WebDriverWait(driver, 20)

            # 1. Klik Masuk/Login di landing
            try:
                masuk_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(
                    (By.XPATH, '//a[contains(text(),"Masuk") or contains(text(),"Login")]'
                               '| //button[contains(text(),"Masuk") or contains(text(),"Login")]')
                ))
                masuk_btn.click()
                time.sleep(2)
            except Exception:
                pass

            # 2. Opsi SSO Mahasiswa
            try:
                sso_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(
                    (By.XPATH, '//*[contains(text(),"Dosen / Staff / Mahasiswa") or contains(text(),"SSO PENS")]'
                               '/ancestor-or-self::a | //*[contains(text(),"Dosen / Staff / Mahasiswa")]'
                               '/ancestor-or-self::button')
                ))
                sso_btn.click()
                time.sleep(3)
            except Exception:
                pass

            # 3. Form CAS
            netid_field = WebDriverWait(driver, 20).until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'input[name="username"], input[id="username"], '
                                  'input[name="netid"], input[id="netid"], '
                                  'input[type="text"]:not([name="lt"])')
            ))
            netid_field.clear()
            netid_field.send_keys(PENS_NETID)

            pass_field = driver.find_element(By.CSS_SELECTOR, 'input[name="password"], input[type="password"]')
            pass_field.clear()
            pass_field.send_keys(PENS_PASSWORD)

            try:
                submit_btn = driver.find_element(By.CSS_SELECTOR, 'input[type="submit"], button[type="submit"]')
            except NoSuchElementException:
                submit_btn = driver.find_element(By.XPATH, '//button | //input[@value="LOGIN"]')
            submit_btn.click()

            WebDriverWait(driver, 30).until(EC.url_contains("/mahasiswa"))
            log("Login CAS berhasil!")

            cookies = driver.get_cookies()
            self.cached_cookies = {c['name']: c['value'] for c in cookies}
            return self.cached_cookies
        except Exception as e:
            log(f"Login gagal: {e}")
            return None
        finally:
            driver.quit()

    def check_active_attendance(self):
        """Memeriksa semua matkul via Fast API (0.5 detik). Return list matkul yang terbuka."""
        if not self.cached_cookies or 'token' not in self.cached_cookies:
            if not self.refresh_session():
                return []

        matkul_list = load_matkul_list()
        if not matkul_list:
            return []

        session = requests.Session()
        for k, v in self.cached_cookies.items():
            session.cookies.set(k, v)

        opened_courses = []

        for item in matkul_list:
            url = item["url"]
            title = item["title"]
            kuliah_id = url.rstrip("/").split("/")[-1]

            api_url = f"{BASE_URL}/api/presensi/aktif-kuliah?kuliah={kuliah_id}&jenis_schema=4"
            try:
                r = session.get(api_url, timeout=5)
                if r.status_code in [401, 403]:
                    self.refresh_session()
                    return []

                data = r.json()
                if isinstance(data, list) and len(data) > 0:
                    session_id = data[0].get("nomor", str(kuliah_id))
                    opened_courses.append({
                        "id": kuliah_id,
                        "session_id": session_id,
                        "title": title,
                        "url": url,
                        "raw_data": data[0]
                    })
            except Exception:
                pass

        return opened_courses

    def execute_attendance(self, url_matkul, nama_matkul):
        """Membuka halaman matkul via browser dan mengklik tombol presensi"""
        log(f"Mengeksekusi presensi untuk: {nama_matkul}...")
        driver = self.make_driver()
        try:
            driver.get(BASE_URL)
            for k, v in self.cached_cookies.items():
                driver.add_cookie({"name": k, "value": v, "domain": "ethol.pens.ac.id"})

            driver.get(url_matkul)
            time.sleep(3)

            buttons = driver.find_elements(By.XPATH, "//button[contains(normalize-space(), 'Presensi') and not(contains(., 'Aturan'))]")
            if not buttons:
                log("Tombol presensi tidak ditemukan.")
                return False

            btn = buttons[0]
            disabled = btn.get_attribute("disabled")
            btn_class = (btn.get_attribute("class") or "").lower()

            if (disabled is not None and str(disabled).lower() in ["true", "disabled"]) or ("lock" in btn_class):
                log(f"Presensi untuk {nama_matkul} masih terkunci.")
                return False

            btn.click()
            time.sleep(3)

            # Konfirmasi modal jika ada
            try:
                dialog_btns = driver.find_elements(By.CSS_SELECTOR, ".swal2-confirm, .btn-primary, button[type='submit']")
                for c_btn in dialog_btns:
                    if c_btn.is_displayed() and c_btn.is_enabled():
                        teks_btn = c_btn.text.strip().lower()
                        if any(k in teks_btn for k in ["ya", "ok", "simpan", "hadir", "submit", "konfirmasi", "confirm"]):
                            c_btn.click()
                            time.sleep(2)
                            break
            except Exception:
                pass

            log(f"Presensi BERHASIL dilakukan untuk: {nama_matkul}!")
            return True
        except Exception as e:
            log(f"Gagal melakukan presensi: {e}")
            return False
        finally:
            driver.quit()
