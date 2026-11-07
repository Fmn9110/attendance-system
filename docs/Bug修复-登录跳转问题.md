# Bug 修复记录：输入密码后跳转不到下一页

> 日期：2026-09-19
> 现象：在登录页输入密码 1234 后，页面直接回到首页，无法进入点名页。

---

## 一、问题现象

用户操作流程：
1. 打开 `http://0.0.0.0:8000/index.html`，看到 5 个班级卡片
2. 点击"计科2601班"，进入 `login.html?class_id=1`
3. 输入密码 `1234`，点击"登录"
4. **页面跳回首页**，没有进入点名页，也没有任何错误提示

用户感知："跳转不到下一页"。

---

## 二、根因分析

### 2.1 第一层原因：密码输错

系统初始化时创建的 5 个班级，**初始密码是 `123456`（6 位）**，不是 `1234`。

用 API 验证：

```
POST /api/classes/login  {"class_id":1, "password":"1234"}
→ HTTP 401  {"detail": "班级密码错误"}

POST /api/classes/login  {"class_id":1, "password":"123456"}
→ HTTP 200  {"code":0, "data": {"token":"..."}}
```

后端正确返回了 401 + "班级密码错误"。

### 2.2 第二层原因（真正的 Bug）：前端 401 处理逻辑错误

`frontend/js/api.js` 中的 `request()` 函数对所有 401 响应做了统一处理：

```js
// 修复前（有 bug）
if (resp.status === 401) {
  clearToken();
  location.href = '/index.html';   // ← 问题在这
  throw new Error(data.message || '未登录');
}
```

这段逻辑的意图是：当用户 Token 过期或未登录时，自动跳回首页重新登录。

**但问题在于**：登录接口本身也会返回 401（当密码错误时）。前端把"密码错误"和"Token 过期"混为一谈了：

| 场景 | 后端返回 | 前端行为（修复前） |
|---|---|---|
| Token 过期访问 /api/students | 401 | 跳回首页 ✅ 正确 |
| **登录时密码错误** | 401 | **跳回首页 ❌ 错误**（应停在登录页显示错误） |

结果：用户输错密码 → 后端返回 401 → 前端直接跳回首页 → 用户看不到"密码错误"提示，以为"跳转不到下一页"。

### 2.3 第三层原因：错误消息字段名不匹配

后端 `auth_service.py` 中登录失败用的是 FastAPI 的 `HTTPException(detail="班级密码错误")`，返回 JSON 格式为：

```json
{"detail": "班级密码错误"}
```

但前端 `api.js` 读取的是 `data.message`（统一响应信封格式），而 401 错误走的是 FastAPI 默认格式，字段名是 `detail`。即使不跳转，错误消息也会显示成"未登录"而不是"班级密码错误"。

---

## 三、修复内容

### 3.1 修改文件：`frontend/js/api.js`

```js
// 修复后
if (resp.status === 401) {
  // 登录页的 401 是密码错误，不跳转，让登录页自己显示错误
  const onLoginPage = location.pathname.endsWith('login.html');
  if (!onLoginPage) {
    clearToken();
    location.href = '/index.html';
  }
  throw new Error(data.message || data.detail || '未登录');
}
```

改动两点：
1. **在登录页时不跳转**：判断当前路径是否以 `login.html` 结尾，如果是则不执行 `location.href = '/index.html'`，让登录页的 `catch` 块自己显示错误提示。
2. **兼容 detail 字段**：错误消息优先读 `data.message`，其次读 `data.detail`。

### 3.2 修改文件：`frontend/login.html`

给 JS 引用加版本号防止浏览器缓存：

```html
<script src="/js/api.js?v=2"></script>
<script src="/js/storage.js?v=2"></script>
```

---

## 四、修复验证

| 测试场景 | 修复前 | 修复后 |
|---|---|---|
| 输入错误密码 1234 | 跳回首页，无提示 | 停在登录页，显示红色"班级密码错误" |
| 输入正确密码 123456 | 正常跳转 | 正常跳转到 attendance.html |
| Token 过期访问学生接口 | 跳回首页 | 跳回首页（行为不变） |

浏览器实测：
- 输入 `1234` → 页面停在登录页，红色提示"班级密码错误"
- 输入 `123456` → 成功进入点名页，学生列表正常显示

---

## 五、给用户的提示

**初始密码是 `123456`（6 位），不是 `1234`。**

如需修改密码，在服务器上执行：

```bash
cd backend
python -m scripts.set_password.py 计科2601班 你的新密码
```

---

## 六、同类问题预防

其他页面（attendance.html、history.html 等）也引用了 api.js，建议一并加版本号防缓存：

- `attendance.html`
- `history.html`
- `history_detail.html`
- `import.html`
- `export.html`
- `index.html`

如后续修改前端 JS，记得把版本号 `?v=2` 递增为 `?v=3`，避免用户浏览器缓存旧代码。
