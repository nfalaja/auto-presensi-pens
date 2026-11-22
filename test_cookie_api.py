import time
import requests
from presensi import make_driver, login

driver = make_driver()
if login(driver):
    driver.get("https://ethol.pens.ac.id/mahasiswa/matakuliah/221229")
    time.sleep(2)
    
    cookies = driver.get_cookies()
    print("Cookies detail:")
    for c in cookies:
        print(c['name'], "=", c['value'][:20] + "...")

    # Coba requests.Session dengan cookies tersebut
    s = requests.Session()
    for c in cookies:
        s.cookies.set(c['name'], c['value'])
        
    res = s.get("https://ethol.pens.ac.id/api/presensi/aktif-kuliah?kuliah=221229&jenis_schema=4")
    print("Status code:", res.status_code)
    print("Response text:", res.text)

driver.quit()
