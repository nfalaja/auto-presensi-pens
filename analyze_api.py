import re

with open('matkul_detail.html', encoding='utf-8') as f:
    html = f.read()

apis = re.findall(r'(/api/[^\s"\'<>]+)', html)
print('API endpoints in HTML:', set(apis))

# Cek tombol presensi dan atribut onclick / class / data
presensi_blocks = re.findall(r'.{0,100}Presensi.{0,100}', html)
for p in presensi_blocks[:10]:
    print('Snippet:', p.strip())
