import requests
import json

base = 'http://127.0.0.1:8000'

# 登录班级1拿token
r = requests.post(f'{base}/api/classes/login', json={'class_id': 1, 'password': '123456'})
token1 = r.json()['data']['token']
headers1 = {'Authorization': f'Bearer {token1}'}

# 登录班级2拿token
r2 = requests.post(f'{base}/api/classes/login', json={'class_id': 2, 'password': '123456'})
token2 = r2.json()['data']['token']
headers2 = {'Authorization': f'Bearer {token2}'}

print('=' * 60)
print('1. 删除接口安全测试')
print('=' * 60)

# 1.1 未认证删除
print('\n1.1 未认证删除:')
r = requests.delete(f'{base}/api/attendance/1', json={'password': '123456'})
print(f'  无token删除: HTTP {r.status_code} - {"✅ 拦截" if r.status_code == 401 else "❌ 漏洞"}')

# 1.2 班级1token删除班级2的场次
print('\n1.2 越权删除（班级1token删班级2场次）:')
# 先获取班级2的场次列表
r = requests.get(f'{base}/api/classes/2/attendance/sessions', headers=headers2)
sessions2 = r.json()['data']
if sessions2:
    sid2 = sessions2[0]['session_id']
    r = requests.delete(f'{base}/api/attendance/{sid2}', headers=headers1, json={'password': '123456'})
    print(f'  删除班级2场次{sid2}: HTTP {r.status_code} - {"✅ 拦截(403)" if r.status_code == 403 else "❌ 漏洞"}')
else:
    print('  班级2无场次，跳过')

# 1.3 密码错误
print('\n1.3 密码错误删除:')
# 先创建一个测试场次
r = requests.post(f'{base}/api/classes/1/attendance/sessions', headers=headers1, json={})
test_sid = r.json()['data']['session_id']
r = requests.delete(f'{base}/api/attendance/{test_sid}', headers=headers1, json={'password': 'wrong'})
print(f'  错误密码删除: HTTP {r.status_code} - {"✅ 拦截" if r.status_code == 401 else "❌ 漏洞"}')

# 1.4 正确密码删除
print('\n1.4 正确密码删除:')
r = requests.delete(f'{base}/api/attendance/{test_sid}', headers=headers1, json={'password': '123456'})
print(f'  正确密码删除: HTTP {r.status_code} - {"✅ 成功" if r.status_code == 200 else "❌ 失败"}')

# 1.5 不带密码
print('\n1.5 不带密码删除:')
r = requests.post(f'{base}/api/classes/1/attendance/sessions', headers=headers1, json={})
test_sid2 = r.json()['data']['session_id']
r = requests.delete(f'{base}/api/attendance/{test_sid2}', headers=headers1, json={})
print(f'  无密码删除: HTTP {r.status_code} - {"✅ 拦截" if r.status_code == 400 else "❌ 漏洞"}')

# 清理
requests.delete(f'{base}/api/attendance/{test_sid2}', headers=headers1, json={'password': '123456'})

print('\n' + '=' * 60)
print('2. 修改密码接口安全测试')
print('=' * 60)

# 2.1 原始密码错误
print('\n2.1 原始密码错误:')
r = requests.post(f'{base}/api/classes/change-password', json={
    'class_id': 1, 'old_password': 'wrong', 'new_password': '123456'
})
print(f'  错误原密码: HTTP {r.status_code} - {"✅ 拦截" if r.status_code == 401 else "❌ 漏洞"}')

# 2.2 新密码太短
print('\n2.2 新密码太短:')
r = requests.post(f'{base}/api/classes/change-password', json={
    'class_id': 1, 'old_password': '123456', 'new_password': '123'
})
print(f'  3位新密码: HTTP {r.status_code} - {"✅ 拦截" if r.status_code == 400 else "❌ 漏洞"}')

# 2.3 修改不存在的班级
print('\n2.3 修改不存在的班级:')
r = requests.post(f'{base}/api/classes/change-password', json={
    'class_id': 999, 'old_password': '123456', 'new_password': '123456'
})
print(f'  不存在班级: HTTP {r.status_code} - {"✅ 拦截" if r.status_code == 404 else "⚠️ " + str(r.status_code)}')

print('\n' + '=' * 60)
print('3. 回归测试（之前修复的漏洞）')
print('=' * 60)

# 3.1 未认证访问
print('\n3.1 未认证访问敏感接口:')
endpoints = [
    '/api/classes/1/students',
    '/api/classes/1/attendance/active',
    '/api/attendance/1',
]
for ep in endpoints:
    r = requests.get(f'{base}{ep}')
    print(f'  {ep}: HTTP {r.status_code} - {"✅" if r.status_code == 401 else "❌"}')

# 3.2 横向越权
print('\n3.2 横向越权:')
r = requests.get(f'{base}/api/classes/2/students', headers=headers1)
print(f'  班级1访问班级2学生: HTTP {r.status_code} - {"✅" if r.status_code == 403 else "❌"}')

# 3.3 路径遍历
print('\n3.3 路径遍历:')
r = requests.post(f'{base}/api/classes/1/students/import/confirm',
    headers=headers1,
    json={'stored_path': '../../../etc/passwd'})
print(f'  路径遍历: HTTP {r.status_code} - {"✅" if r.status_code == 400 else "❌"}')

# 3.4 Token伪造
print('\n3.4 Token伪造:')
r = requests.get(f'{base}/api/classes/1/students', headers={'Authorization': 'Bearer fake'})
print(f'  假token: HTTP {r.status_code} - {"✅" if r.status_code == 401 else "❌"}')

print('\n' + '=' * 60)
print('安全测试完成')
print('=' * 60)
