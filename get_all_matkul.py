import sys, os, time, json
from presensi import make_driver, login, MATKUL_LIST_URL

driver = make_driver()
if login(driver):
    driver.get(MATKUL_LIST_URL)
    time.sleep(3)
    
    # Let's get all 12 cards and their matkul IDs by clicking or checking
    cards_data = []
    
    # We can execute JS to get all 12 button clicks or click them sequentially
    num_cards = len(driver.find_elements("xpath", "//button[contains(., 'Akses Kuliah')]"))
    print(f"Total matkul cards found: {num_cards}")
    
    for i in range(num_cards):
        # Refresh to matkul list if needed
        if driver.current_url != MATKUL_LIST_URL:
            driver.get(MATKUL_LIST_URL)
            time.sleep(2)
            
        buttons = driver.find_elements("xpath", "//button[contains(., 'Akses Kuliah')]")
        if i >= len(buttons):
            break
        btn = buttons[i]
        card = btn.find_element("xpath", "./ancestor::div[contains(@class, 'rounded-xl')]")
        card_text = card.text.split("\n")[0].strip()
        
        btn.click()
        time.sleep(2)
        
        detail_url = driver.current_url
        print(f"[{i+1}/{num_cards}] {card_text} -> {detail_url}")
        cards_data.append({"title": card_text, "url": detail_url})
        
    with open("daftar_matkul.json", "w", encoding="utf-8") as f:
        json.dump(cards_data, f, indent=2)
    print("Daftar matkul saved to daftar_matkul.json")

driver.quit()
