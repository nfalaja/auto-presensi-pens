import sys, os, time
from selenium import webdriver
from selenium.webdriver.common.by import By
from presensi import make_driver, login, MATKUL_LIST_URL

driver = make_driver()
if login(driver):
    driver.get(MATKUL_LIST_URL)
    time.sleep(4)
    with open("matkul_page.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    print("Page HTML saved.")

    # Find cards or links
    elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Akses Kuliah')]")
    print(f"Total elements with 'Akses Kuliah': {len(elements)}")
    for i, el in enumerate(elements):
        p = el.find_element(By.XPATH, "..")
        print(f"[{i}] tag={el.tag_name}, class={el.get_attribute('class')}, parent_tag={p.tag_name}, parent_class={p.get_attribute('class')}")
        # check if clicking opens new url
    
    # Check all links on page
    links = driver.find_elements(By.TAG_NAME, "a")
    print(f"Total <a> tags: {len(links)}")
    for l in links:
        href = l.get_attribute("href") or ""
        txt = l.text.strip()
        if href or txt:
            print(f"  <a> text='{txt}' href='{href}'")

driver.quit()
