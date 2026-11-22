import sys, os, time
from presensi import make_driver, login, MATKUL_LIST_URL

driver = make_driver()
if login(driver):
    driver.get(MATKUL_LIST_URL)
    time.sleep(3)
    buttons = driver.find_elements("xpath", "//button[contains(., 'Akses Kuliah')]")
    print(f"Found buttons: {len(buttons)}")
    if buttons:
        btn = buttons[0]
        card = btn.find_element("xpath", "./ancestor::div[contains(@class, 'rounded-xl')]")
        print("Card title text:", card.text.split("\n")[0])
        print("Clicking button...")
        btn.click()
        time.sleep(4)
        print("New URL after click:", driver.current_url)
        driver.save_screenshot("debug_matkul_detail.png")
driver.quit()
