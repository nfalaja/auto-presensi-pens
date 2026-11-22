# -*- coding: utf-8 -*-
"""
Telegram Bot Handler
Mengelola komunikasi bot Telegram, command /mode & /status, serta Inline Keyboard.
"""

import json
import time
import requests
from core.config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, get_settings, save_settings


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
                {"text": "🔄 Cek Status Server", "callback_data": "check_status"}
            ]
        ]
    }
    send_telegram(text, reply_markup=keyboard)


def send_attendance_prompt(course_title, course_id):
    """Mengirim tombol konfirmasi presensi untuk mode manual"""
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Lakukan Presensi Sekarang", "callback_data": f"absen_{course_id}"},
                {"text": "❌ Lewati", "callback_data": f"ignore_{course_id}"}
            ]
        ]
    }
    text = (
        f"🔔 <b>PRESENSI TERBUKA!</b>\n\n"
        f"Mata Kuliah: <b>{course_title}</b>\n"
        f"Dosen telah membuka presensi!\n\n"
        f"Apakah kamu ingin melakukan presensi sekarang?"
    )
    return send_telegram(text, reply_markup=keyboard)
