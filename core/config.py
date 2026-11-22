# -*- coding: utf-8 -*-
"""
Central Configuration Module
"""
import os
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Kredensial (Environment Variables didahulukan untuk Cloud, fallback ke lokal)
PENS_USERNAME    = os.getenv("PENS_USERNAME", "aghnapens1@gt.student.pens.ac.id")
PENS_PASSWORD    = os.getenv("PENS_PASSWORD", "ggPUnbbM8Uq493y")
PENS_NETID       = os.getenv("PENS_NETID", "aghnapens1@gt.student.pens.ac.id")

TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "9190737122:AAG9YkKMT0J6QTqKds2zFPbTqdNVt8b723M")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "1181181278")

BASE_URL         = "https://ethol.pens.ac.id"
LOGIN_URL        = f"{BASE_URL}/login"
MATKUL_LIST_URL  = f"{BASE_URL}/mahasiswa/matakuliah"

SETTINGS_FILE    = os.path.join(BASE_DIR, "settings.json")
MATKUL_FILE      = os.path.join(BASE_DIR, "daftar_matkul.json")
LOG_FILE         = os.path.join(BASE_DIR, "presensi.log")

# Lokasi Opera GX Windows
OPERA_GX_PATH    = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Opera GX\opera.exe")


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
        print(f"Error save_settings: {e}")


def load_matkul_list():
    if os.path.exists(MATKUL_FILE):
        try:
            with open(MATKUL_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []
