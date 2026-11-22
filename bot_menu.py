# -*- coding: utf-8 -*-
"""
Bot Helper & Configuration Manager
"""
import os
import json
import requests
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
MATKUL_FILE = os.path.join(BASE_DIR, "daftar_matkul.json")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "9190737122:AAG9YkKMT0J6QTqKds2zFPbTqdNVt8b723M")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "1181181278")


def get_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # Default settings: mode auto
    default_settings = {"mode": "auto"}
    save_settings(default_settings)
    return default_settings


def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)


def send_telegram(text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.json()
    except Exception as e:
        print(f"Error send_telegram: {e}")
        return None


def send_mode_menu():
    current_mode = get_settings().get("mode", "auto").upper()
    text = (
        f"⚙️ <b>PENGATURAN MODE PRESENSI</b>\n\n"
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
                {"text": "🔄 Cek Semua Matkul Sekarang", "callback_data": "check_now"}
            ]
        ]
    }
    send_telegram(text, reply_markup=keyboard)


if __name__ == "__main__":
    send_mode_menu()
    print("Mode menu sent to Telegram!")
