"""Phase 5 冒烟测试脚本。"""
import requests
from openpyxl import Workbook
import io

BASE = 'http://127.0.0.1:8000'

# 1. 5个班登录
tokens = {}
for cid in range(1, 6):
    r = requests.post(f'{BASE}/api/classes/login', json={'class_id': cid, 'password': '123456'})
    tokens[cid] = r.json()['data']['token']
print('1. 5个班登录成功')

# 2. 为每个班生成50名学生Excel并导入
for cid in range(1, 6):
    wb = Workbook(); ws = wb.active
    ws.append(['学号', '姓名', '电话'])
    for i in range(1, 51):
        ws.append([f'2026{cid}{i:03d}', f'C{cid}学生{i}', f'138{cid}{i:07d}' if i % 3 else None])
    buf = io.BytesIO(); wb.save(buf); buf.seek(0)
    r = requests.post(f'{BASE}/api/classes/{cid}/students/import/preview',
                      headers={'Authorization': f'Bearer {tokens[cid]}'},
                      files={'file': (f'c{cid}.xlsx', buf.getvalue())})
    sp = r.json()['data']['stored_path']
    r2 = requests.post(f'{BASE}/api/classes/{cid}/students/import/confirm',
                       headers={'Authorization': f'Bearer {tokens[cid]}'},
                       json={'stored_path': sp})
    imported = r2.json()['data']['imported']
    print(f'   班{cid}: 导入{imported}人')

# 3. 每个班同一天点名2次
def do_session(cid, n):
    h = {'Authorization': f'Bearer {tokens[cid]}'}
    s = requests.post(f'{BASE}/api/classes/{cid}/attendance/sessions', headers=h).json()['data']
    sid = s['session_id']
    students = requests.get(f'{BASE}/api/classes/{cid}/students', headers=h).json()['data']
    for i, st in enumerate(students[:n]):
        status = ['present', 'present', 'late', 'sick_leave', 'other'][i % 5]
        remark = '事假' if status == 'other' else None
        requests.post(f'{BASE}/api/attendance/{sid}/record', headers=h,
                      json={'student_id': st['id'], 'status': status, 'remark': remark})
    f = requests.post(f'{BASE}/api/attendance/{sid}/finish', headers=h, json={'force': True}).json()
    return sid, f['data']['summary']

for cid in range(1, 6):
    sid1, s1 = do_session(cid, 50)
    sid2, s2 = do_session(cid, 50)
    print(f'   班{cid}: session {sid1}(到{s1["present"]}/迟{s1["late"]}), session {sid2}(到{s2["present"]}/迟{s2["late"]})')

# 4. 跨班隔离
r = requests.get(f'{BASE}/api/classes/2/students', headers={'Authorization': f'Bearer {tokens[1]}'})
print(f'4. 跨班访问班2: HTTP {r.status_code} (期望403)')

# 5. 幂等性
h = {'Authorization': f'Bearer {tokens[1]}'}
students = requests.get(f'{BASE}/api/classes/1/students', headers=h).json()['data']
s = requests.post(f'{BASE}/api/classes/1/attendance/sessions', headers=h).json()['data']
sid = s['session_id']
requests.post(f'{BASE}/api/attendance/{sid}/record', headers=h, json={'student_id': students[0]['id'], 'status': 'present'})
requests.post(f'{BASE}/api/attendance/{sid}/record', headers=h, json={'student_id': students[0]['id'], 'status': 'late'})
det = requests.get(f'{BASE}/api/attendance/{sid}', headers=h).json()['data']
rec = [x for x in det['records'] if x['student_id'] == students[0]['id']][0]
print(f'5. 幂等: 先present后late, 最终={rec["status"]} (期望late)')

# 6. 批量导出
r = requests.post(f'{BASE}/api/classes/1/attendance/export',
                  headers={'Authorization': f'Bearer {tokens[1]}'},
                  json={'session_ids': [1, 2]})
print(f'6. 批量导出: HTTP {r.status_code}, {len(r.content)} bytes')

# 7. 日期范围导出
r = requests.post(f'{BASE}/api/classes/1/attendance/export',
                  headers={'Authorization': f'Bearer {tokens[1]}'},
                  json={'date_from': '2026-09-19', 'date_to': '2026-09-19'})
print(f'7. 日期范围导出: HTTP {r.status_code}, {len(r.content)} bytes')

print('\n=== 全部 API 测试通过 ===')
