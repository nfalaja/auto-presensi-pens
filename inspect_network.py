import time
import json
from presensi import make_driver, login

driver = make_driver()
if login(driver):
    # Enable network performance logging if possible or inspect scripts
    driver.get("https://ethol.pens.ac.id/mahasiswa/matakuliah/221229")
    time.sleep(3)
    
    # Ambil semua network requests melalui window.performance
    logs = driver.execute_script("""
        var entries = window.performance.getEntriesByType("resource");
        var urls = [];
        for (var i = 0; i < entries.length; i++) {
            urls.push(entries[i].name);
        }
        return urls;
    """)
    
    print(f"Total network resources: {len(logs)}")
    api_urls = [u for u in logs if "api" in u or "json" in u or "presensi" in u or "kuliah" in u]
    for u in api_urls:
        print("API URL:", u)

driver.quit()
