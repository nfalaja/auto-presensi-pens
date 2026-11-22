# -*- coding: utf-8 -*-
"""
PENS Auto Presensi - Unified Main Runner (Local & Cloud)
"""

import sys
import time
import datetime
import threading
import argparse

from core.config import (
    get_settings, save_settings, load_matkul_list,
    TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, OPERA_GX_PATH
)
from core.ethol_client import EtholClient, log
from core.telegram_bot import (
    send_telegram, answer_callback_query, edit_message_text,
    send_mode_menu, send_attendance_prompt
)

ethol = EtholClient()
notified_sessions = set()


def is_active_hours():
    """Memeriksa apakah saat ini jam perkuliahan: Senin-Jumat, 07:45 - 17:15 WIB"""
    utc_now = datetime.datetime.utcnow()
    wib_now = utc_now + datetime.timedelta(hours=7)
    is_weekday = (wib_now.weekday() < 5)
    is_hours = (7 <= wib_now.hour <= 17)
    return is_weekday and is_hours, wib_now


def monitor_loop():
    """Background thread: memeriksa presensi secara berkala"""
    log("Monitor presensi dimulai...")
    ethol.refresh_session()

    while True:
        try:
            active, wib_now = is_active_hours()
            if active:
                opened_courses = ethol.check_active_attendance()
                mode = get_settings().get("mode", "auto").lower()

                for course in opened_courses:
                    key = f"{course['id']}_{course['session_id']}"
                    if key not in notified_sessions:
                        notified_sessions.add(key)
                        nama = course["title"]
                        url = course["url"]

                        if mode == "auto":
                            log(f"[AUTO] Presensi terbuka di {nama}! Mengeksekusi...")
                            send_telegram(f"⚡ <b>Presensi Terbuka!</b>\nMatkul: <b>{nama}</b>\nSedang memproses presensi otomatis...")
                            sukses = ethol.execute_attendance(url, nama)
                            if sukses:
                                send_telegram(
                                    f"🎉 <b>PRESENSI OTOMATIS BERHASIL!</b>\n\n"
                                    f"✅ Matkul: <b>{nama}</b>\n"
                                    f"⏰ Waktu: {wib_now.strftime('%H:%M:%S WIB, %d %b %Y')}\n"
                                    "Portal: ETHOL PENS"
                                )
                            else:
                                send_telegram(f"⚠️ Gagal presensi otomatis untuk <b>{nama}</b>. Buka web: {url}")
                        else:
                            # Mode Manual
                            log(f"[MANUAL] Presensi terbuka di {nama}! Mengirim konfirmasi Telegram.")
                            send_attendance_prompt(nama, course["id"])

            time.sleep(30)
        except Exception as e:
            log(f"Error monitor_loop: {e}")
            time.sleep(10)


def telegram_listener(duration_seconds=None):
    """Mendengarkan perintah dan tombol interaktif dari Telegram"""
    log("Telegram listener aktif...")
    start_time = time.time()
    last_update_id = 0

    while True:
        if duration_seconds and (time.time() - start_time) >= duration_seconds:
            log("Sesi listener selesai (mencapai batas durasi shift).")
            break

        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
            params = {"offset": last_update_id + 1, "timeout": 20}
            resp = requests_get(url, params)

            if resp and resp.status_code == 200:
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
                                _, wib_now = is_active_hours()
                                send_telegram(
                                    f"📊 <b>STATUS AUTO PRESENSI PENS</b>\n\n"
                                    f"• Mode: <b>{'🤖 OTOMATIS' if current_mode == 'AUTO' else '✋ MANUAL'}</b>\n"
                                    f"• Jam Server: <b>{wib_now.strftime('%H:%M:%S WIB')}</b>\n"
                                    f"• Fast API Polling: <b>Tiap 30-45 detik ⚡</b>\n"
                                    f"• Status Bot: <b>Online & Aktif 24/7 🟢</b>\n\n"
                                    f"Ketik /mode untuk mengubah mode."
                                )

                    # 2. Tombol Callback
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
                                "🤖 <b>MODE OTOMATIS DIAKTIFKAN</b>\n\n"
                                "Setiap kali dosen membuka presensi, sistem akan <b>langsung presensi seketika</b> dan mengabarimu.\n\n"
                                "Ketik /mode jika ingin beralih ke Manual."
                            )

                        elif cdata == "set_mode_manual":
                            settings = get_settings()
                            settings["mode"] = "manual"
                            save_settings(settings)
                            answer_callback_query(cq_id, "Mode diubah ke MANUAL ✋")
                            edit_message_text(
                                msg_id,
                                "✋ <b>MODE MANUAL DIAKTIFKAN</b>\n\n"
                                "Setiap kali ada presensi dibuka oleh dosen, bot akan <b>mengirim pesan konfirmasi</b>:\n"
                                "<i>'Terdapat presensi untuk matkul X, lakukan presensi?'</i>\n\n"
                                "Presensi baru akan dijalankan saat kamu menekan tombol 'Lakukan Presensi'.\n\n"
                                "Ketik /mode jika ingin beralih ke Otomatis."
                            )

                        elif cdata == "check_status":
                            answer_callback_query(cq_id, "Server normal 🟢")
                            send_telegram("🟢 <b>Server Berjalan Normal</b>\nSistem monitoring dan bot Telegram siap beroperasi.")

                        elif cdata.startswith("absen_"):
                            kid = cdata.split("_")[1]
                            answer_callback_query(cq_id, "Memproses...")
                            matkul_list = load_matkul_list()
                            target = next((m for m in matkul_list if kid in m["url"]), None)
                            if target:
                                edit_message_text(msg_id, f"⏳ Sedang melakukan presensi untuk <b>{target['title']}</b>...")
                                sukses = ethol.execute_attendance(target["url"], target["title"])
                                if sukses:
                                    edit_message_text(
                                        msg_id,
                                        f"🎉 <b>PRESENSI BERHASIL!</b>\n\n"
                                        f"✅ Matkul: <b>{target['title']}</b>\n"
                                        f"⏰ Waktu: {datetime.datetime.now().strftime('%H:%M:%S WIB')}"
                                    )
                                else:
                                    edit_message_text(msg_id, f"⚠️ Gagal presensi {target['title']}. Buka web: {target['url']}")

                        elif cdata.startswith("ignore_"):
                            answer_callback_query(cq_id, "Dilewati.")
                            edit_message_text(msg_id, "❌ Presensi untuk sesi ini dilewati.")

        except Exception as e:
            time.sleep(3)


def requests_get(url, params):
    import requests
    try:
        return requests.get(url, params=params, timeout=25)
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="PENS Auto Presensi Engine")
    parser.add_argument("--duration", type=int, default=None, help="Durasi berjalan dalam menit (opsional untuk Cloud)")
    args = parser.parse_args()

    log("Menjalankan PENS Auto Presensi System...")

    # Jalankan monitor thread
    t_mon = threading.Thread(target=monitor_loop, daemon=True)
    t_mon.start()

    # Jalankan Telegram listener di thread utama
    duration_sec = (args.duration * 60) if args.duration else None
    telegram_listener(duration_seconds=duration_sec)


if __name__ == "__main__":
    main()
