# -*- coding: utf-8 -*-
"""
PENS Auto Presensi - ethol.pens.ac.id
Otomatis login, cek semua 12 matkul, dan lakukan presensi jika tombol terbuka.
Kirim notifikasi ke Telegram jika berhasil.
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

# -- Konfigurasi ---------------------------------------------------------------
USERNAME         = "aghnapens1@gt.student.pens.ac.id"
PASSWORD         = "ggPUnbbM8Uq493y"
NETID            = "aghnapens1@gt.student.pens.ac.id"
BASE_URL         = "https://ethol.pens.ac.id"
LOGIN_URL        = BASE_URL + "/login"
MATKUL_LIST_URL  = BASE_URL + "/mahasiswa/matakuliah"
TELEGRAM_TOKEN   = "9190737122:AAG9YkKMT0J6QTqKds2zFPbTqdNVt8b723M"
TELEGRAM_CHAT_ID = "1181181278"

BASE_DIR         = os.path.dirname(os.path.abspath(__file__))
LOG_FILE         = os.path.join(BASE_DIR, "presensi.log")
MATKUL_FILE      = os.path.join(BASE_DIR, "daftar_matkul.json")
STATE_FILE       = os.path.join(BASE_DIR, "presensi_state.json")
OPERA_GX_PATH    = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Opera GX\opera.exe")
# ------------------------------------------------------------------------------


def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = "[{}] {}".format(ts, msg)
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def send_telegram(msg):
    for attempt in range(3):
        try:
            url = "https://api.telegram.org/bot{}/sendMessage".format(TELEGRAM_TOKEN)
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
            log("[TELEGRAM attempt {}/3] {}".format(attempt + 1, str(e)))
            time.sleep(5)
    log("[TELEGRAM] Gagal kirim setelah 3 percobaan.")


def make_driver():
    options = Options()
    if os.path.exists(OPERA_GX_PATH):
        options.binary_location = OPERA_GX_PATH
        log(f"Menggunakan browser: Opera GX ({OPERA_GX_PATH})")
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,900")
    options.add_argument("--log-level=3")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])

    try:
        service = Service(ChromeDriverManager(driver_version="155.0.8059.85").install())
    except Exception:
        service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.implicitly_wait(5)
    return driver


def login(driver):
    log("Membuka halaman login: " + LOGIN_URL)
    driver.get(LOGIN_URL)
    wait = WebDriverWait(driver, 20)

    try:
        # Step 1: Tombol Masuk/Login di landing page
        try:
            masuk_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(
                (By.XPATH, '//a[contains(text(),"Masuk") or contains(text(),"Login")]'
                           '| //button[contains(text(),"Masuk") or contains(text(),"Login")]')
            ))
            log("Klik tombol 'Masuk/Login' di landing page...")
            masuk_btn.click()
            time.sleep(2)
        except Exception:
            pass

        # Step 2: Pilih metode login "Dosen / Staff / Mahasiswa" (SSO PENS)
        try:
            sso_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(
                (By.XPATH, '//*[contains(text(),"Dosen / Staff / Mahasiswa") or contains(text(),"SSO PENS")]'
                           '/ancestor-or-self::a | //*[contains(text(),"Dosen / Staff / Mahasiswa")]'
                           '/ancestor-or-self::button')
            ))
            log("Klik opsi 'Dosen / Staff / Mahasiswa (SSO PENS)'...")
            sso_btn.click()
            time.sleep(3)
        except Exception as e:
            log("Tidak ada modal pilih login, lanjut cari form... (" + str(e) + ")")

        # Step 3: Isi form SSO CAS PENS
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

        # Tunggu redirect ke portal mahasiswa
        WebDriverWait(driver, 30).until(EC.url_contains("/mahasiswa"))
        log("Login berhasil OK")
        return True

    except TimeoutException:
        log("Login GAGAL - timeout. URL saat ini: " + driver.current_url)
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

        # Cari tombol Presensi (bukan "Aturan Presensi")
        buttons = driver.find_elements(By.XPATH, "//button[contains(normalize-space(), 'Presensi') and not(contains(., 'Aturan'))]")
        
        if not buttons:
            log("  -> [{}] Tombol presensi tidak ditemukan.".format(nama))
            return None

        btn = buttons[0]
        disabled = btn.get_attribute("disabled")
        btn_class = (btn.get_attribute("class") or "").lower()

        # Tombol terkunci biasanya memiliki class 'lock' atau attribute disabled='true'
        is_locked = (disabled is not None and str(disabled).lower() in ["true", "disabled"]) or ("lock" in btn_class)

        if is_locked:
            log("  -> [{}] Presensi masih TERKUNCI.".format(nama))
            return None

        # JIKA TERBUKA / UNLOCKED:
        log("  >>> [{}] PRESENSI TERBUKA! Mengklik tombol presensi...".format(nama))
        btn.click()
        time.sleep(3)

        # Konfirmasi dialog jika muncul
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

        # Screenshot bukti presensi berhasil
        proof_path = os.path.join(BASE_DIR, "bukti_presensi_{}.png".format(int(time.time())))
        driver.save_screenshot(proof_path)
        log("  >>> [{}] Presensi BERHASIL dilakukan! Bukti: {}".format(nama, proof_path))
        return nama

    except TimeoutException:
        log("  -> Timeout saat mengakses {}: {}".format(nama, url))
        return None
    except Exception as e:
        log("  -> Error saat cek {}: {}".format(nama, str(e)))
        return None


def run_presensi():
    log("=" * 60)
    log(">> Memulai pemeriksaan auto-presensi PENS...")

    matkul_list = load_daftar_matkul()
    if not matkul_list:
        log("Daftar mata kuliah kosong! Periksa file daftar_matkul.json.")
        return

    driver = make_driver()
    presensi_berhasil = []

    try:
        if not login(driver):
            send_telegram("⚠️ <b>Auto Presensi PENS</b>\nLogin gagal saat pemeriksaan terjadwal.")
            return

        log("Memeriksa {} mata kuliah...".format(len(matkul_list)))
        for matkul in matkul_list:
            hasil = cek_dan_presensi_matkul(driver, matkul)
            if hasil:
                presensi_berhasil.append(hasil)

        if presensi_berhasil:
            daftar = "\n".join("  ✅ <b>{}</b>".format(m) for m in presensi_berhasil)
            pesan = (
                "🎉 <b>PRESENSI OTOMATIS BERHASIL!</b>\n\n"
                "Mata kuliah yang berhasil dipresensi:\n{}\n\n"
                "⏰ Waktu: {}\n"
                "Portal: ETHOL PENS"
            ).format(daftar, datetime.datetime.now().strftime("%H:%M:%S WIB, %d %b %Y"))
            send_telegram(pesan)
        else:
            log("Semua mata kuliah saat ini presensinya masih ditutup / terkunci.")

    finally:
        driver.quit()

    log("== Sesi pemeriksaan selesai.")


if __name__ == "__main__":
    run_presensi()
