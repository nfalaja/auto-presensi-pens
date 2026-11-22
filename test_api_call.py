import time
import json
import requests
from presensi import make_driver, login

driver = make_driver()
if login(driver):
    driver.get("https://ethol.pens.ac.id/mahasiswa/matakuliah/221229")
    time.sleep(2)
    
    # Ambil cookies dan local storage / token
    cookies = driver.get_cookies()
    session_cookies = {c['name']: c['value'] for c in cookies}
    print("Cookies count:", len(cookies))
    
    # Ambil token dari localStorage jika ada
    token = driver.execute_script("return localStorage.getItem('token') || localStorage.getItem('jwt') || localStorage.getItem('auth');")
    print("Token from localStorage:", token)
    
    # Coba fetch API aktif-kuliah via javascript di halaman yang sama
    api_res = driver.execute_script("""
        return fetch('/api/presensi/aktif-kuliah?kuliah=221229&jenis_schema=4')
            .then(res => res.json())
            .then(data => JSON.stringify(data))
            .catch(err => err.toString());
    """)
    print("API aktif-kuliah response:", api_res)

driver.quit()
