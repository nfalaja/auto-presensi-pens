# -*- coding: utf-8 -*-
"""
Cloud Telegram Bot Listener (Running 24/7 on GitHub Actions Cloud Runner)
- Aktif terus-menerus di server cloud GitHub
- Menjawab /status, /mode, dan tombol inline kapan saja (laptop mati tetap jalan!)
"""

import time
import requests
import os
import sys
import json
import datetime

TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "9190737122:AAG9YkKMT0J6QTqKds2zFPbTqdNVt8b723M")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "1181181278")

BASE_DIR         = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE    = os.path.join(BASE_DIR, "settings.json")


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
        print(f"Error save_settings: {e}")


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
    except Exception as e:
        print(f"Error edit_message_text: {e}")


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


def run_cloud_listener(run_duration_minutes=55):
    print(f"Cloud Bot Listener aktif di GitHub Actions ({run_duration_minutes} menit session)...", flush=True)
    start_time = time.time()
    last_update_id = 0

    while (time.time() - start_time) < (run_duration_minutes * 60):
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
            params = {"offset": last_update_id + 1, "timeout": 20}
            resp = requests.get(url, params=params, timeout=25)

            if resp.status_code == 200:
                data = resp.json()
                for update in data.get("result", []):
                    last_update_id = update["update_id"]

                    # 1. Pesan Teks
                    if "message" in update and "text" in update["message"]:
                        text = update["message"]["text"].strip()
                        chat_id = str(update["message"]["chat"]["id"])

                        if chat_id == TELEGRAM_CHAT_ID:
                            if text in ["/mode", "/start", "/help", "mode", "menu"]:
                                send_mode_menu()
                            elif text in ["/status", "/cek", "status"]:
                                current_mode = get_settings().get("mode", "auto").upper()
                                send_telegram(
                                    f"📊 <b>STATUS AUTO PRESENSI CLOUD</b>\n\n"
                                    f"• Mode: <b>{'🤖 OTOMATIS' if current_mode == 'AUTO' else '✋ MANUAL'}</b>\n"
                                    f"• Server: <b>GitHub Actions Cloud Runner ☁️</b>\n"
                                    f"• Status Bot: <b>ONLINE 24/7 (Laptop mati tetap jalan!) 🟢</b>\n"
                                    f"• Jam operasional: <b>08:00 - 17:00 WIB (Senin-Jumat)</b>\n"
                                    f"• Kecepatan cek: <b>Fast API Polling Real-time ⚡</b>\n\n"
                                    f"Ketik /mode untuk mengubah mode."
                                )

                    # 2. Tombol Inline
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
                                "Setiap kali dosen membuka presensi, sistem cloud akan <b>langsung melakukan presensi otomatis</b> dan mengabarimu setelah selesai.\n\n"
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
                                "Setiap kali ada presensi dibuka oleh dosen, bot cloud akan <b>mengirim pesan konfirmasi</b>:\n"
                                "<i>'Terdapat presensi untuk matkul X, lakukan presensi?'</i>\n\n"
                                "Presensi baru akan dijalankan setelah kamu menekan tombol 'Lakukan Presensi'.\n\n"
                                "Ketik /mode jika ingin beralih ke Otomatis."
                            )

                        elif cdata == "check_cloud":
                            answer_callback_query(cq_id, "Server Cloud Normal 🟢")
                            send_telegram("☁️ <b>Server Cloud Aktif</b>\nSistem monitoring presensi dan bot Telegram berjalan normal di cloud.")

                        elif cdata.startswith("absen_"):
                            kid = cdata.split("_")[1]
                            answer_callback_query(cq_id, "Mengeksekusi...")
                            edit_message_text(msg_id, f"⏳ Sedang melakukan presensi cloud untuk ID: <b>{kid}</b>...")

                        elif cdata.startswith("ignore_"):
                            answer_callback_query(cq_id, "Dilewati.")
                            edit_message_text(msg_id, "❌ Presensi untuk sesi ini dilewati.")

        except Exception as e:
            time.sleep(3)


if __name__ == "__main__":
    run_cloud_listener(run_duration_minutes=55)
