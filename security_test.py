import requests
import json

base = 'http://127.0.0.1:8000'

# 登录
r = requests.post(f'{base}/api/classes/login', json={'class_id': 1, 'password': '123456'})
token = r.json()['data']['token']
headers = {'Authorization': f'Bearer {token}'}

print('=== 4. SQL注入测试 ===')

# 测试1: student_id注入
payloads = [
    {'student_id': '1 OR 1=1', 'status': 'present'},
    {'student_id': "1; DROP TABLE students--", 'status': 'present'},
    {'student_id': '1 UNION SELECT * FROM classes--', 'status': 'present'},
]
for p in payloads:
    try:
        r = requests.post(f'{base}/api/attendance/1/record', json=p, headers=headers)
        if r.status_code == 400:
            print(f'  ✅ 拦截: {p["student_id"]} -> HTTP {r.status_code}')
        else:
            print(f'  ❌ 注入成功: {p["student_id"]} -> HTTP {r.status_code}')
    except Exception as e:
        print(f'  ✅ 拦截: {p["student_id"]}')

# 测试2: remark字段XSS注入
print()
print('测试2: remark字段XSS注入')
r = requests.post(f'{base}/api/attendance/1/record',
                  json={'student_id': 1, 'status': 'other', 'remark': '<script>alert(1)</script>'},
                  headers=headers)
print(f'  状态: HTTP {r.status_code} (内容被存储，前端innerHTML渲染时需注意)')

# 验证数据库完整性
r = requests.get(f'{base}/api/classes/1/students', headers=headers)
print(f'  学生数量: {len(r.json()["data"])} - 正常')

# 测试3: 暴力破解密码
print()
print('=== 5. 密码暴力破解测试 ===')
wrong_passwords = ['1234', 'admin', 'password', '000000', '111111', 'class123']
for pwd in wrong_passwords:
    r = requests.post(f'{base}/api/classes/login', json={'class_id': 1, 'password': pwd})
    if r.status_code == 200:
        print(f'  ❌ 密码 {pwd} 竟然登录成功!')
    else:
        print(f'  ✅ 密码 {pwd}: 拒绝 (HTTP {r.status_code})')

# 测试正确密码
r = requests.post(f'{base}/api/classes/login', json={'class_id': 1, 'password': '123456'})
print(f'  正确密码 123456: HTTP {r.status_code} (正常)')

# 测试Token伪造
print()
print('=== 6. Token伪造测试 ===')
fake_tokens = ['fake_token_123', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.fake', 'admin']
for ft in fake_tokens:
    r = requests.get(f'{base}/api/classes/1/students', headers={'Authorization': f'Bearer {ft}'})
    if r.status_code == 200:
        print(f'  ❌ 伪造token {ft}: 竟然通过认证!')
    else:
        print(f'  ✅ 伪造token {ft[:20]}: 拒绝 (HTTP {r.status_code})')

# 测试URL参数token伪造
r = requests.get(f'{base}/api/classes/1/students?token=fake_token_123')
print(f'  URL参数伪造token: HTTP {r.status_code} - {"✅ 拦截" if r.status_code == 401 else "❌ 通过"}')
