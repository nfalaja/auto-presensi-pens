# -*- coding: utf-8 -*-
"""
PENS Auto Presensi Cloud Server (Render.com Edition)
- Flask Web Server (Port listening agar Free Tier Render tetap Healthy & Active)
- 24/7 Real-Time Telegram Bot Listener
- Fast API Presensi Checker (Polling tiap 30-45 detik di jam kuliah)
"""

import os
import sys
import time
import json
import threading
import datetime
import requests
from flask import Flask, jsonify

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# -- Konfigurasi Lingkungan ---------------------------------------------------
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

# State & Cache
cached_cookies = {}
notified_sessions = set()
server_start_time = datetime.datetime.now()

app = Flask(__name__)


def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def get_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"mode": "auto"}


def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        log(f"Error save_settings: {e}")


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
        except Exception:
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


def send_mode_menu():
    current_mode = get_settings().get("mode", "auto").upper()
    text = (
        f"⚙️ <b>PENGATURAN MODE PRESENSI (CLOUD 24/7)</b>\n\n"
        f"Status saat ini: <b>{'🤖 OTOMATIS' if current_mode == 'AUTO' else '✋ MANUAL'}</b>\n\n"
        f"• <b>Otomatis</b>: Begitu dosen membuka presensi, sistem langsung absen sendiri tanpa menunggu.\n"
        f"• <b>Manual</b>: Saat presensi dibuka, bot akan mengirimkan konfirmasi dengan tombol 'Lakukan Presensi'.\n\n"
        f"Pilih mode yang kamu inginkan di bawah ini:"
    )
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "🤖 Mode Otomatis" + (" (Aktif)" if current_mode == "AUTO" else ""), "callback_data": "set_mode_auto"},
                {"text": "✋ Mode Manual" + (" (Aktif)" if current_mode == "MANUAL" else ""), "callback_data": "set_mode_manual"}
            ],
            [
                {"text": "🔄 Cek Status Server Cloud", "callback_data": "check_cloud"}
            ]
        ]
    }
    send_telegram(text, reply_markup=keyboard)


def make_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,900")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])

    # Linux Render / Docker environment
    chrome_bin = os.getenv("CHROME_BIN", "/usr/bin/google-chrome")
    if os.path.exists(chrome_bin):
        options.binary_location = chrome_bin

    try:
        service = Service(ChromeDriverManager().install())
    except Exception:
        service = Service()
        
    driver = webdriver.Chrome(service=service, options=options)
    driver.implicitly_wait(5)
    return driver


def get_fresh_session():
    global cached_cookies
    log("Memperbarui sesi login CAS PENS...")
    driver = make_driver()
    try:
        driver.get(LOGIN_URL)
        wait = WebDriverWait(driver, 20)

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
    log(f"Mengeksekusi presensi cloud untuk: {nama_matkul}...")
    driver = make_driver()
    try:
        driver.get(BASE_URL)
        for k, v in cached_cookies.items():
            driver.add_cookie({"name": k, "value": v, "domain": "ethol.pens.ac.id"})
        
        driver.get(url_matkul)
        time.sleep(3)

        buttons = driver.find_elements(By.XPATH, "//button[contains(normalize-space(), 'Presensi') and not(contains(., 'Aturan'))]")
        if not buttons:
            return False

        btn = buttons[0]
        disabled = btn.get_attribute("disabled")
        btn_class = (btn.get_attribute("class") or "").lower()

        if (disabled is not None and str(disabled).lower() in ["true", "disabled"]) or ("lock" in btn_class):
            log(f"Presensi {nama_matkul} masih terkunci.")
            return False

        btn.click()
        time.sleep(3)

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

        log(f"Presensi BERHASIL untuk: {nama_matkul}!")
        return True
    except Exception as e:
        log(f"Error eksekusi: {e}")
        return False
    finally:
        driver.quit()


def check_all_matkul_fast():
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
        kuliah_id = url.rstrip("/").split("/")[-1]

        api_url = f"{BASE_URL}/api/presensi/aktif-kuliah?kuliah={kuliah_id}&jenis_schema=4"
        try:
            r = s.get(api_url, timeout=5)
            if r.status_code in [401, 403]:
                get_fresh_session()
                return []
            
            data = r.json()
            if isinstance(data, list) and len(data) > 0:
                session_id = data[0].get("nomor", str(kuliah_id))
                opened_courses.append({
                    "id": kuliah_id,
                    "session_id": session_id,
                    "title": title,
                    "url": url,
                    "raw": data[0]
                })
        except Exception:
            pass

    return opened_courses


def monitor_loop():
    """Pemeriksaan real-time tiap 30-45 detik di jam 08:00 - 17:00 WIB"""
    log("Monitor presensi cloud aktif...")
    get_fresh_session()

    while True:
        try:
            # Waktu WIB (UTC+7)
            utc_now = datetime.datetime.utcnow()
            wib_now = utc_now + datetime.timedelta(hours=7)

            is_weekday = (wib_now.weekday() < 5) # Senin - Jumat
            is_kuliah_hours = (7 <= wib_now.hour <= 17)

            if is_weekday and is_kuliah_hours:
                opened = check_all_matkul_fast()
                mode = get_settings().get("mode", "auto").lower()

                for mk in opened:
                    unique_key = f"{mk['id']}_{mk['session_id']}"
                    if unique_key not in notified_sessions:
                        notified_sessions.add(unique_key)
                        nama = mk["title"]
                        url = mk["url"]

                        if mode == "auto":
                            log(f"[AUTO] Presensi terbuka di {nama}! Mengeksekusi...")
                            send_telegram(f"⚡ <b>Presensi Terbuka!</b>\nMatkul: <b>{nama}</b>\nSedang memproses presensi otomatis...")
                            sukses = eksekusi_presensi(url, nama)
                            if sukses:
                                send_telegram(
                                    f"🎉 <b>PRESENSI OTOMATIS BERHASIL! (Cloud)</b>\n\n"
                                    f"✅ Matkul: <b>{nama}</b>\n"
                                    f"⏰ Waktu: {wib_now.strftime('%H:%M:%S WIB, %d %b %Y')}\n"
                                    "Server: Render Cloud 24/7"
                                )
                            else:
                                send_telegram(f"⚠️ Gagal presensi otomatis untuk {nama}. Buka: {url}")
                        else:
                            # Mode Manual
                            log(f"[MANUAL] Presensi terbuka di {nama}! Mengirim konfirmasi ke Telegram.")
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

            time.sleep(30)
        except Exception as e:
            log(f"Error monitor_loop: {e}")
            time.sleep(10)


def telegram_listener_loop():
    """Listener 24/7 untuk perintah Telegram"""
    log("Telegram Bot listener aktif...")
    last_update_id = 0

    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
            params = {"offset": last_update_id + 1, "timeout": 20}
            resp = requests.get(url, params=params, timeout=25)

            if resp.status_code == 200:
                data = resp.json()
                for update in data.get("result", []):
                    last_update_id = update["update_id"]

                    # Message
                    if "message" in update and "text" in update["message"]:
                        text = update["message"]["text"].strip()
                        chat_id = str(update["message"]["chat"]["id"])

                        if chat_id == TELEGRAM_CHAT_ID:
                            if text in ["/mode", "/start", "/help", "mode", "menu"]:
                                send_mode_menu()
                            elif text in ["/status", "/cek", "status"]:
                                current_mode = get_settings().get("mode", "auto").upper()
                                utc_now = datetime.datetime.utcnow()
                                wib_now = utc_now + datetime.timedelta(hours=7)
                                send_telegram(
                                    f"📊 <b>STATUS CLOUD SERVER (RENDER 24/7)</b>\n\n"
                                    f"• Mode: <b>{'🤖 OTOMATIS' if current_mode == 'AUTO' else '✋ MANUAL'}</b>\n"
                                    f"• Status Server: <b>ONLINE 24/7 (Laptop mati tetap jalan!) 🟢</b>\n"
                                    f"• Waktu Server: <b>{wib_now.strftime('%H:%M:%S WIB')}</b>\n"
                                    f"• Monitoring: <b>Tiap 30 detik (Fast API)</b>\n"
                                    f"• Jam Presensi: <b>08:00 - 17:00 WIB (Senin-Jumat)</b>\n\n"
                                    f"Ketik /mode untuk mengubah mode."
                                )

                    # Callback Query
                    if "callback_query" in update:
                        cq = update["callback_query"]
                        cq_id = cq["id"]
                        cdata = cq["data"]
                        msg_id = cq["message"]["message_id"]

                        if cdata == "set_mode_auto":
                            settings = get_settings()
                            settings["mode"] = "auto"
                            save_settings(settings)
                            answer_callback_query(cq_id, "Mode diubah ke OTOMATIS ✅")
                            edit_message_text(
                                msg_id,
                                "🤖 <b>MODE OTOMATIS DIAKTIFKAN (CLOUD)</b>\n\n"
                                "Setiap kali dosen membuka presensi, server cloud akan <b>langsung presensi seketika</b> dan mengirim laporan ke kamu.\n\n"
                                "Ketik /mode jika ingin beralih ke Manual."
                            )

                        elif cdata == "set_mode_manual":
                            settings = get_settings()
                            settings["mode"] = "manual"
                            save_settings(settings)
                            answer_callback_query(cq_id, "Mode diubah ke MANUAL ✋")
                            edit_message_text(
                                msg_id,
                                "✋ <b>MODE MANUAL DIAKTIFKAN (CLOUD)</b>\n\n"
                                "Setiap kali ada presensi dibuka oleh dosen, bot akan <b>mengirim tombol konfirmasi</b>:\n"
                                "<i>'Terdapat presensi untuk matkul X, lakukan presensi?'</i>\n\n"
                                "Presensi baru akan dijalankan saat kamu menekan tombol 'Lakukan Presensi'.\n\n"
                                "Ketik /mode jika ingin beralih ke Otomatis."
                            )

                        elif cdata == "check_cloud":
                            answer_callback_query(cq_id, "Server Cloud Normal 🟢")
                            send_telegram("☁️ <b>Server Cloud Aktif Normal</b>\nSemua proses monitoring presensi berjalan aktif di Render.com.")

                        elif cdata.startswith("absen_"):
                            kid = cdata.split("_")[1]
                            answer_callback_query(cq_id, "Memproses presensi...")
                            with open(MATKUL_FILE, "r", encoding="utf-8") as f:
                                matkul_list = json.load(f)
                            target = next((m for m in matkul_list if kid in m["url"]), None)
                            if target:
                                edit_message_text(msg_id, f"⏳ Sedang melakukan presensi cloud untuk <b>{target['title']}</b>...")
                                sukses = eksekusi_presensi(target["url"], target["title"])
                                if sukses:
                                    edit_message_text(
                                        msg_id,
                                        f"🎉 <b>PRESENSI BERHASIL! (Cloud)</b>\n\n"
                                        f"✅ Matkul: <b>{target['title']}</b>\n"
                                        f"⏰ Waktu: {(datetime.datetime.utcnow() + datetime.timedelta(hours=7)).strftime('%H:%M:%S WIB')}"
                                    )
                                else:
                                    edit_message_text(msg_id, f"⚠️ Gagal presensi {target['title']}. Buka web: {target['url']}")

                        elif cdata.startswith("ignore_"):
                            answer_callback_query(cq_id, "Dilewati.")
                            edit_message_text(msg_id, "❌ Presensi untuk sesi ini dilewati.")

        except Exception as e:
            time.sleep(3)


# Endpoint Health Check untuk Render
@app.route("/")
def index():
    return jsonify({
        "status": "online",
        "service": "PENS Auto Presensi 24/7 Cloud Engine",
        "uptime_since": server_start_time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": get_settings().get("mode", "auto")
    })


# Start background workers saat server boot
t_mon = threading.Thread(target=monitor_loop, daemon=True)
t_mon.start()

t_bot = threading.Thread(target=telegram_listener_loop, daemon=True)
t_bot.start()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
