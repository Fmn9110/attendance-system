import requests, io
from openpyxl import Workbook

BASE = 'http://127.0.0.1:8000'
token = requests.post(f'{BASE}/api/classes/login', json={'class_id': 1, 'password': '123456'}).json()['data']['token']
h = {'Authorization': f'Bearer {token}'}

old = requests.get(f'{BASE}/api/classes/1/students', headers=h).json()['data']
print(f'旧名单: {len(old)}人')

wb = Workbook(); ws = wb.active
ws.append(['学号', '姓名'])
for i in range(1, 11):
    ws.append([f'2026{i:04d}', f'新学生{i}'])
buf = io.BytesIO(); wb.save(buf); buf.seek(0)
r = requests.post(f'{BASE}/api/classes/1/students/import/preview', headers=h,
                  files={'file': ('new.xlsx', buf.getvalue())}).json()
sp = r['data']['stored_path']
r2 = requests.post(f'{BASE}/api/classes/1/students/import/confirm', headers=h,
                   json={'stored_path': sp}).json()
d = r2['data']
print(f'新导入: {d["imported"]}人, 替换旧: {d["deactivated"]}人')

new = requests.get(f'{BASE}/api/classes/1/students', headers=h).json()['data']
print(f'新名单: {len(new)}人')

r3 = requests.get(f'{BASE}/api/attendance/1', headers=h).json()['data']
print(f'历史session1记录数: {len(r3["records"])} (历史数据保留)')
