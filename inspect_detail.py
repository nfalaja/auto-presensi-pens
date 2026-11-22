import sys, os, time
from presensi import make_driver, login

driver = make_driver()
if login(driver):
    driver.get('https://ethol.pens.ac.id/mahasiswa/matakuliah/221229')
    time.sleep(4)
    with open('matkul_detail.html', 'w', encoding='utf-8') as f:
        f.write(driver.page_source)
    print('Detail page saved.')
    
    buttons = driver.find_elements('xpath', '//button')
    print(f'Total buttons: {len(buttons)}')
    for i, b in enumerate(buttons):
        txt = b.text.strip()
        cls = b.get_attribute('class') or ''
        dis = b.get_attribute('disabled')
        print(f'Button [{i}] text="{txt}" disabled={dis} class="{cls}"')

driver.quit()
