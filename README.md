# 🎓 PENS Auto Presensi (ETHOL)

Sistem pemantauan dan otomatisasi presensi perkuliahan di portal **ETHOL PENS** secara real-time dengan integrasi bot Telegram interaktif.

## ✨ Fitur Utama
- **⚡ Super Gercep (Fast API)**: Pengecekan 12 mata kuliah via direct API internal ETHOL hanya memakan waktu ~0.5 detik (looping tiap 30-45 detik).
- **🤖 Mode Otomatis vs ✋ Manual**: 
  - **Otomatis**: Langsung melakukan presensi otomatis begitu dibuka dosen dan mengirim bukti laporan ke Telegram.
  - **Manual**: Mengirimkan tombol konfirmasi `[✅ Lakukan Presensi Sekarang]` ke Telegram.
- **🌐 24/7 Cloud Relay**: Berjalan tanpa henti di server cloud (GitHub Actions) tanpa memerlukan kartu kredit.
- **🎮 Opera GX Integration**: Dukungan browser lokal menggunakan Opera GX.

## 📁 Struktur Proyek
```
pens-presensi/
├── .github/workflows/
│   └── presensi_daemon.yml   # Workflow GitHub Actions 24/7 Estafet
├── core/
│   ├── config.py             # Pusat konfigurasi kredensial & path
│   ├── ethol_client.py       # Client ETHOL (Login SSO, Fast API, Browser Action)
│   └── telegram_bot.py       # Handler bot Telegram & Inline Buttons
├── main.py                   # Runner utama terpadu
├── daftar_matkul.json        # Database URL 12 mata kuliah
├── settings.json             # State mode (auto / manual)
└── requirements.txt          # Dependensi Python
```

## 🚀 Perintah Bot Telegram
- `/mode` : Mengubah mode antara Otomatis dan Manual.
- `/status`: Melihat status kesehatan server dan mode aktif.
