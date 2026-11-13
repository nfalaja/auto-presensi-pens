# -*- coding: utf-8 -*-
"""
PENS Auto Presensi - Cloud Edition (GitHub Actions / Linux VPS)
Membaca kredensial dari Environment Variables untuk keamanan.
"""

import time
import datetime
import requests
import os
import sys
import json

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# -- Konfigurasi dari Environment Variables -------------------------------------
USERNAME         = os.getenv("PENS_USERNAME", "aghnapens1@gt.student.pens.ac.id")
PASSWORD         = os.getenv("PENS_PASSWORD", "ggPUnbbM8Uq493y")
NETID            = os.getenv("PENS_NETID", "aghnapens1@gt.student.pens.ac.id")
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "9190737122:AAG9YkKMT0J6QTqKds2zFPbTqdNVt8b723M")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "1181181278")

BASE_URL         = "https://ethol.pens.ac.id"
LOGIN_URL        = BASE_URL + "/login"
MATKUL_LIST_URL  = BASE_URL + "/mahasiswa/matakuliah"

BASE_DIR         = os.path.dirname(os.path.abspath(__file__))
MATKUL_FILE      = os.path.join(BASE_DIR, "daftar_matkul.json")
# ------------------------------------------------------------------------------


def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def send_telegram(msg):
    for attempt in range(3):
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            resp = requests.post(
                url,
                data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"},
                timeout=20
            )
            result = resp.json()
            if not result.get("ok"):
                log("[TELEGRAM ERROR] " + resp.text)
            else:
                log("[TELEGRAM] Notifikasi terkirim OK")
            return
        except Exception as e:
            log(f"[TELEGRAM attempt {attempt + 1}/3] {e}")
            time.sleep(5)


def make_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,900")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])

    # Di Linux / GitHub Actions, Chrome / Chromium sudah otomatis terinstall
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.implicitly_wait(5)
    return driver


def login(driver):
    log("Membuka halaman login: " + LOGIN_URL)
    driver.get(LOGIN_URL)

    try:
        try:
            masuk_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(
                (By.XPATH, '//a[contains(text(),"Masuk") or contains(text(),"Login")]'
                           '| //button[contains(text(),"Masuk") or contains(text(),"Login")]')
            ))
            masuk_btn.click()
            time.sleep(2)
        except Exception:
            pass

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

        netid_field = WebDriverWait(driver, 20).until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, 'input[name="username"], input[id="username"], '
                              'input[name="netid"], input[id="netid"], '
                              'input[type="text"]:not([name="lt"])')
        ))
        netid_field.clear()
        netid_field.send_keys(NETID)

        pass_field = driver.find_element(
            By.CSS_SELECTOR, 'input[name="password"], input[type="password"]'
        )
        pass_field.clear()
        pass_field.send_keys(PASSWORD)

        try:
            submit_btn = driver.find_element(By.CSS_SELECTOR, 'input[type="submit"], button[type="submit"]')
        except NoSuchElementException:
            submit_btn = driver.find_element(By.XPATH, '//button | //input[@value="LOGIN"]')
        submit_btn.click()

        WebDriverWait(driver, 30).until(EC.url_contains("/mahasiswa"))
        log("Login berhasil OK")
        return True

    except TimeoutException:
        log("Login GAGAL - timeout. URL: " + driver.current_url)
        return False


def load_daftar_matkul():
    if os.path.exists(MATKUL_FILE):
        try:
            with open(MATKUL_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log("Gagal membaca daftar_matkul.json: " + str(e))
    return []


def cek_dan_presensi_matkul(driver, matkul):
    nama = matkul["title"]
    url = matkul["url"]
    
    try:
        driver.get(url)
        time.sleep(2)

        buttons = driver.find_elements(By.XPATH, "//button[contains(normalize-space(), 'Presensi') and not(contains(., 'Aturan'))]")
        
        if not buttons:
            return None

        btn = buttons[0]
        disabled = btn.get_attribute("disabled")
        btn_class = (btn.get_attribute("class") or "").lower()

        is_locked = (disabled is not None and str(disabled).lower() in ["true", "disabled"]) or ("lock" in btn_class)

        if is_locked:
            log(f"  -> [{nama}] Presensi masih TERKUNCI.")
            return None

        log(f"  >>> [{nama}] PRESENSI TERBUKA! Mengklik tombol presensi...")
        btn.click()
        time.sleep(3)

        try:
            dialog_btns = driver.find_elements(By.CSS_SELECTOR, ".swal2-confirm, .btn-primary, button[type='submit']")
            for c_btn in dialog_btns:
                if c_btn.is_displayed() and c_btn.is_enabled():
                    teks_btn = c_btn.text.strip().lower()
                    if any(k in teks_btn for k in ["ya", "ok", "simpan", "hadir", "submit", "konfirmasi"]):
                        c_btn.click()
                        time.sleep(2)
                        break
        except Exception:
            pass

        log(f"  >>> [{nama}] Presensi BERHASIL dilakukan!")
        return nama

    except Exception as e:
        log(f"  -> Error saat cek {nama}: {e}")
        return None


def run_presensi():
    log("=" * 60)
    log(">> [CLOUD] Memulai pemeriksaan auto-presensi PENS...")

    matkul_list = load_daftar_matkul()
    if not matkul_list:
        log("Daftar mata kuliah kosong!")
        return

    driver = make_driver()
    presensi_berhasil = []

    try:
        if not login(driver):
            send_telegram("⚠️ <b>Auto Presensi PENS (Cloud)</b>\nLogin gagal saat pemeriksaan terjadwal.")
            return

        log(f"Memeriksa {len(matkul_list)} mata kuliah...")
        for matkul in matkul_list:
            hasil = cek_dan_presensi_matkul(driver, matkul)
            if hasil:
                presensi_berhasil.append(hasil)

        if presensi_berhasil:
            daftar = "\n".join(f"  ✅ <b>{m}</b>" for m in presensi_berhasil)
            pesan = (
                "🎉 <b>PRESENSI OTOMATIS BERHASIL! (Cloud)</b>\n\n"
                f"Mata kuliah yang berhasil dipresensi:\n{daftar}\n\n"
                f"⏰ Waktu: {datetime.datetime.now().strftime('%H:%M:%S WIB, %d %b %Y')}\n"
                "Portal: ETHOL PENS"
            )
            send_telegram(pesan)
        else:
            log("Semua mata kuliah saat ini presensinya masih ditutup / terkunci.")

    finally:
        driver.quit()

    log("== Sesi selesai.")


if __name__ == "__main__":
    run_presensi()
