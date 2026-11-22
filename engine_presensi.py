# -*- coding: utf-8 -*-
"""
PENS Auto Presensi Engine v2 (Gercep + Interactive Telegram Bot)
- Mendukung Mode Otomatis & Manual
- Fast API Polling tiap 30-60 detik (Real-time detection)
- Inline button konfirmasi presensi via Telegram
"""

import time
import datetime
import requests
import os
import sys
import json
import threading

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# -- Konfigurasi ---------------------------------------------------------------
USERNAME         = os.getenv("PENS_USERNAME", "aghnapens1@gt.student.pens.ac.id")
PASSWORD         = os.getenv("PENS_PASSWORD", "ggPUnbbM8Uq493y")
NETID            = os.getenv("PENS_NETID", "aghnapens1@gt.student.pens.ac.id")
BASE_URL         = "https://ethol.pens.ac.id"
LOGIN_URL        = BASE_URL + "/login"
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "9190737122:AAG9YkKMT0J6QTqKds2zFPbTqdNVt8b723M")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "1181181278")

BASE_DIR         = os.path.dirname(os.path.abspath(__file__))
MATKUL_FILE      = os.path.join(BASE_DIR, "daftar_matkul.json")
SETTINGS_FILE    = os.path.join(BASE_DIR, "settings.json")
LOG_FILE         = os.path.join(BASE_DIR, "presensi.log")

BRAVE_PATH       = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
# ------------------------------------------------------------------------------

# Global session cache
cached_cookies = {}
notified_sessions = set()  # Hindari spam notifikasi berulang untuk sesi yang sama


def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def get_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    settings = {"mode": "auto"}
    save_settings(settings)
    return settings


def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        log(f"Error saving settings: {e}")


def send_telegram(text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    for _ in range(3):
        try:
            r = requests.post(url, json=payload, timeout=15)
            return r.json()
        except Exception as e:
            time.sleep(2)
    return None


def answer_callback_query(callback_query_id, text=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery"
    try:
        requests.post(url, json={"callback_query_id": callback_query_id, "text": text}, timeout=10)
    except Exception:
        pass


def edit_message_text(message_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception:
        pass


def make_driver():
    options = Options()
    if os.path.exists(BRAVE_PATH):
        options.binary_location = BRAVE_PATH
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,900")
    options.add_argument("--log-level=3")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])

    try:
        service = Service(ChromeDriverManager(driver_version="157.0.8103.50").install())
    except Exception:
        service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.implicitly_wait(5)
    return driver


def get_fresh_session():
    """Melakukan login dan mengembalikan cookies aktif"""
    global cached_cookies
    log("Memperbarui sesi login CAS PENS...")
    driver = make_driver()
    try:
        driver.get(LOGIN_URL)
        wait = WebDriverWait(driver, 20)

        # 1. Klik tombol login
        try:
            masuk_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(
                (By.XPATH, '//a[contains(text(),"Masuk") or contains(text(),"Login")]'
                           '| //button[contains(text(),"Masuk") or contains(text(),"Login")]')
            ))
            masuk_btn.click()
            time.sleep(2)
        except Exception:
            pass

        # 2. Opsi SSO
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
        log("Login CAS berhasil!")

        cookies = driver.get_cookies()
        cached_cookies = {c['name']: c['value'] for c in cookies}
        return cached_cookies
    except Exception as e:
        log(f"Login gagal: {e}")
        return None
    finally:
        driver.quit()


def eksekusi_presensi(url_matkul, nama_matkul):
    """Membuka halaman matkul via browser dan mengklik tombol presensi"""
    log(f"Mengeksekusi presensi untuk: {nama_matkul} ({url_matkul})...")
    driver = make_driver()
    try:
        # Inject cookies jika ada
        driver.get(BASE_URL)
        for k, v in cached_cookies.items():
            driver.add_cookie({"name": k, "value": v, "domain": "ethol.pens.ac.id"})
        
        driver.get(url_matkul)
        time.sleep(3)

        # Cari tombol presensi
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

        log("Mengklik tombol presensi...")
        btn.click()
        time.sleep(3)

        # Konfirmasi dialog jika ada
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


def check_all_matkul_fast():
    """Pemeriksaan cepat 12 matkul via API dalam 1-2 detik"""
    global cached_cookies
    if not cached_cookies or 'token' not in cached_cookies:
        if not get_fresh_session():
            return []

    try:
        with open(MATKUL_FILE, "r", encoding="utf-8") as f:
            matkul_list = json.load(f)
    except Exception:
        return []

    s = requests.Session()
    for k, v in cached_cookies.items():
        s.cookies.set(k, v)

    opened_courses = []

    for item in matkul_list:
        url = item["url"]
        title = item["title"]
        # Ambil ID kuliah dari URL
        kuliah_id = url.rstrip("/").split("/")[-1]

        api_url = f"{BASE_URL}/api/presensi/aktif-kuliah?kuliah={kuliah_id}&jenis_schema=4"
        try:
            r = s.get(api_url, timeout=5)
            if r.status_code == 401 or r.status_code == 403:
                # Token kadaluarsa, refresh session
                log("Token expired, refreshing session...")
                get_fresh_session()
                return []
            
            data = r.json()
            # Jika ada presensi aktif, data berupa list yang tidak kosong
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


def monitor_loop():
    """Loop background yang mengecek presensi tiap 30-45 detik di jam kuliah"""
    log("Monitor presensi background dimulai...")
    
    # Inisialisasi sesi pertama
    get_fresh_session()

    while True:
        try:
            now = datetime.datetime.now()
            # Cek jam perkuliahan: 07:45 sampai 17:30
            is_kuliah_hours = (7 <= now.hour <= 17)
            
            if is_kuliah_hours:
                opened = check_all_matkul_fast()
                mode = get_settings().get("mode", "auto").lower()

                for mk in opened:
                    unique_key = f"{mk['id']}_{mk['session_id']}"
                    
                    if unique_key not in notified_sessions:
                        notified_sessions.add(unique_key)
                        nama = mk['title']
                        url = mk['url']
                        
                        if mode == "auto":
                            log(f"Presensi terbuka di {nama}! Mode OTOMATIS: langsung dieksekusi.")
                            send_telegram(f"⚡ <b>Presensi Terbuka!</b>\nMatkul: <b>{nama}</b>\nSedang melakukan presensi otomatis...")
                            sukses = eksekusi_presensi(url, nama)
                            if sukses:
                                send_telegram(
                                    f"🎉 <b>PRESENSI OTOMATIS BERHASIL!</b>\n\n"
                                    f"✅ Matkul: <b>{nama}</b>\n"
                                    f"⏰ Waktu: {datetime.datetime.now().strftime('%H:%M:%S WIB, %d %b %Y')}\n"
                                    f"Portal: ETHOL PENS"
                                )
                            else:
                                send_telegram(f"⚠️ Gagal melakukan presensi otomatis untuk <b>{nama}</b>. Silakan cek manual: {url}")
                        else:
                            # MODE MANUAL
                            log(f"Presensi terbuka di {nama}! Mode MANUAL: mengirim konfirmasi ke Telegram.")
                            keyboard = {
                                "inline_keyboard": [
                                    [
                                        {"text": "✅ Lakukan Presensi Sekarang", "callback_data": f"absen_{mk['id']}"},
                                        {"text": "❌ Lewati", "callback_data": f"ignore_{mk['id']}"}
                                    ]
                                ]
                            }
                            send_telegram(
                                f"🔔 <b>PRESENSI TERBUKA!</b>\n\n"
                                f"Mata Kuliah: <b>{nama}</b>\n"
                                f"Dosen telah membuka presensi!\n\n"
                                f"Apakah kamu ingin melakukan presensi sekarang?",
                                reply_markup=keyboard
                            )

            # Polling tiap 30 detik agar super GERCEP
            time.sleep(30)
        except Exception as e:
            log(f"Error di monitor_loop: {e}")
            time.sleep(10)


def handle_telegram_updates():
    """Mendengarkan tombol klik dan perintah dari Telegram"""
    last_update_id = 0
    log("Telegram listener dimulai...")

    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
            params = {"offset": last_update_id + 1, "timeout": 20}
            resp = requests.get(url, params=params, timeout=25)
            
            if resp.status_code == 200:
                data = resp.json()
                for update in data.get("result", []):
                    last_update_id = update["update_id"]
                    
                    # 1. Handle Pesan Teks (/mode, /start, /status)
                    if "message" in update and "text" in update["message"]:
                        text = update["message"]["text"].strip()
                        chat_id = str(update["message"]["chat"]["id"])
                        
                        if chat_id == TELEGRAM_CHAT_ID:
                            if text in ["/mode", "/start", "/help", "menu", "mode"]:
                                from bot_menu import send_mode_menu
                                send_mode_menu()
                            elif text in ["/status", "/cek", "status"]:
                                current_mode = get_settings().get("mode", "auto").upper()
                                send_telegram(
                                    f"📊 <b>STATUS AUTO PRESENSI PENS</b>\n\n"
                                    f"• Mode: <b>{'🤖 OTOMATIS' if current_mode == 'AUTO' else '✋ MANUAL'}</b>\n"
                                    f"• Kecepatan cek: <b>Tiap 30 detik (Gercep API)</b>\n"
                                    f"• Jam operasional: <b>08:00 - 17:00 WIB</b>\n"
                                    f"• Portal: <b>ETHOL PENS (12 Mata Kuliah)</b>\n\n"
                                    f"Ketik /mode untuk mengubah mode."
                                )

                    # 2. Handle Tombol Inline Callback
                    if "callback_query" in update:
                        cq = update["callback_query"]
                        cq_id = cq["id"]
                        data_str = cq["data"]
                        msg_id = cq["message"]["message_id"]

                        # Ganti Mode ke Auto
                        if data_str == "set_mode_auto":
                            settings = get_settings()
                            settings["mode"] = "auto"
                            save_settings(settings)
                            answer_callback_query(cq_id, "Mode diubah ke OTOMATIS ✅")
                            edit_message_text(
                                msg_id,
                                "🤖 <b>MODE OTOMATIS DIAKTIFKAN</b>\n\n"
                                "Setiap kali dosen membuka presensi, sistem akan <b>langsung melakukan presensi otomatis</b> dan memberi kabar setelah selesai.\n\n"
                                "Ketik /mode kapan saja jika ingin mengubah ke Manual."
                            )

                        # Ganti Mode ke Manual
                        elif data_str == "set_mode_manual":
                            settings = get_settings()
                            settings["mode"] = "manual"
                            save_settings(settings)
                            answer_callback_query(cq_id, "Mode diubah ke MANUAL ✋")
                            edit_message_text(
                                msg_id,
                                "✋ <b>MODE MANUAL DIAKTIFKAN</b>\n\n"
                                "Setiap kali ada presensi dibuka oleh dosen, bot akan <b>mengirim tombol konfirmasi</b>:\n"
                                "<i>'Terdapat presensi untuk matkul X, lakukan presensi?'</i>\n\n"
                                "Presensi baru akan dijalankan saat kamu menekan tombol 'Lakukan Presensi'.\n\n"
                                "Ketik /mode kapan saja jika ingin mengubah ke Otomatis."
                            )

                        # Cek status sekarang
                        elif data_str == "check_now":
                            answer_callback_query(cq_id, "Sedang memeriksa seluruh matkul...")
                            opened = check_all_matkul_fast()
                            if opened:
                                daftar = "\n".join(f"• <b>{m['title']}</b>" for m in opened)
                                send_telegram(f"🔔 <b>Presensi Terbuka Ditemukan:</b>\n{daftar}")
                            else:
                                send_telegram("ℹ️ Semua mata kuliah saat ini masih belum membuka presensi.")

                        # Konfirmasi Absen Manual
                        elif data_str.startswith("absen_"):
                            kuliah_id = data_str.split("_")[1]
                            answer_callback_query(cq_id, "Memproses presensi...")
                            
                            # Cari nama matkul
                            with open(MATKUL_FILE, "r", encoding="utf-8") as f:
                                matkul_list = json.load(f)
                            target = next((m for m in matkul_list if kuliah_id in m["url"]), None)
                            
                            if target:
                                edit_message_text(msg_id, f"⏳ Sedang melakukan presensi untuk <b>{target['title']}</b>...")
                                sukses = eksekusi_presensi(target["url"], target["title"])
                                if sukses:
                                    edit_message_text(
                                        msg_id,
                                        f"🎉 <b>PRESENSI BERHASIL!</b>\n\n"
                                        f"✅ Matkul: <b>{target['title']}</b>\n"
                                        f"⏰ Waktu: {datetime.datetime.now().strftime('%H:%M:%S WIB')}"
                                    )
                                else:
                                    edit_message_text(
                                        msg_id,
                                        f"⚠️ Gagal melakukan presensi untuk <b>{target['title']}</b>.\n"
                                        f"Silakan coba presensi manual di browser: {target['url']}"
                                    )

                        # Lewati Absen Manual
                        elif data_str.startswith("ignore_"):
                            answer_callback_query(cq_id, "Presensi dilewati.")
                            edit_message_text(msg_id, "❌ Presensi untuk sesi ini dilewati.")

        except Exception as e:
            time.sleep(3)


if __name__ == "__main__":
    log("Menjalankan PENS Auto Presensi Engine v2...")
    
    # Jalankan monitor di thread terpisah
    t_monitor = threading.Thread(target=monitor_loop, daemon=True)
    t_monitor.start()

    # Jalankan Telegram listener di thread utama
    handle_telegram_updates()
