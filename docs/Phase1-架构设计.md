# Phase 1：项目架构设计

> 线上班级点名管理系统 — 架构设计文档
> 版本：v1.0 ｜ 日期：2026-09-19

---

## 一、技术栈总览

| 层 | 技术选型 | 说明 |
|---|---|---|
| 前端 | 原生 HTML5 + CSS3 + Vanilla JS (ES6+) | 不使用 React/Vue，移动端优先 |
| 后端 | Python 3.10+ / FastAPI | REST API，自动 OpenAPI 文档 |
| ORM | SQLAlchemy 2.0 | 同时支持 SQLite / MySQL / PostgreSQL |
| 数据库 | SQLite（默认） | 通过连接串可切换 MySQL/PostgreSQL |
| Excel | openpyxl（.xlsx）+ xlrd（.xls 兼容） | 导入导出均使用 |
| 密码哈希 | passlib[bcrypt] | 不可逆哈希，禁止明文 |
| 会话 | Bearer Token（itsdangerous 签名） | 无状态，适合手机浏览器 |
| 部署 | Nginx + Uvicorn + Systemd | Ubuntu 22.04 |

---

## 二、项目目录结构

```
attendance-system/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI 入口，挂载路由、静态文件、异常处理
│   │   ├── config.py               # 配置（DB URL、上传目录、密钥、会话时长）
│   │   ├── database/
│   │   │   ├── __init__.py
│   │   │   ├── session.py          # Engine / SessionLocal / get_db 依赖
│   │   │   └── base.py             # Declarative Base
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── class_.py           # Class
│   │   │   ├── student.py          # Student
│   │   │   ├── session.py          # AttendanceSession
│   │   │   └── record.py           # AttendanceRecord
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── common.py           # 统一响应信封
│   │   │   ├── class_schema.py
│   │   │   ├── student_schema.py
│   │   │   └── attendance_schema.py
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── classes.py         # 班级列表 + 登录
│   │   │   ├── students.py         # 学生列表 + Excel 导入预览/确认
│   │   │   ├── attendance.py       # 点名 Session 与记录
│   │   │   ├── history.py         # 历史记录查询
│   │   │   └── export.py           # 单次/批量 Excel 导出
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py      # 登录、Token 签发/校验、依赖注入
│   │   │   ├── excel_service.py     # Excel 解析、校验、导出生成
│   │   │   ├── attendance_service.py# Session 生命周期、记录幂等写入
│   │   │   └── export_naming.py     # 中文文件名自动生成
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── security.py         # bcrypt 哈希
│   │       └── timeutil.py         # 耗时格式化、文件名日期
│   ├── data/                       # SQLite 数据库文件（gitignore）
│   │   └── attendance.db
│   ├── uploads/                    # 临时上传的 Excel（导入后可清理）
│   ├── scripts/
│   │   ├── init_db.py              # 建表 + 创建默认 5 个班级 + 设置密码
│   │   └── set_password.py         # 单独重置某班密码
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── index.html                  # 首页：5 个班级选择
│   ├── login.html                  # 班级密码登录
│   ├── attendance.html             # 核心点名页（单页完成全部操作）
│   ├── import.html                 # Excel 花名册上传与预览
│   ├── history.html                # 历史记录列表
│   ├── history_detail.html         # 单次点名详情
│   ├── export.html                 # 批量导出选择
│   ├── css/
│   │   ├── base.css                # 重置变量、通用样式
│   │   └── pages/                  # 各页面样式
│   └── js/
│       ├── api.js                  # fetch 封装、Token、统一错误
│       ├── storage.js              # localStorage 离线暂存与恢复
│       └── pages/                  # 各页面逻辑
├── deploy/
│   ├── attendance.service          # systemd 单元
│   ├── nginx.conf                  # Nginx 站点配置
│   └── backup.sh                   # SQLite 备份脚本
├── docs/
│   ├── Phase1-架构设计.md
│   ├── Phase2-后端开发.md
│   ├── Phase3-前端开发.md
│   ├── Phase4-移动端UI优化.md
│   ├── Phase5-测试报告.md
│   └── Phase6-部署文档.md
└── README.md
```

---

## 三、数据库 ER 设计

### 3.1 实体关系

```
classes 1 ──── n students
classes 1 ──── n attendance_sessions
attendance_sessions 1 ──── n attendance_records
students 1 ──── n attendance_records
```

- 一个班级有多份学生名单（重新上传时**软替换**：旧学生标记为已替换，不物理删除，保证历史记录仍可关联到 student_id）。
- 一次 Session 属于一个班级，包含多条 Record。
- 一个 (session_id, student_id) 唯一，保证一人一次一条最终记录。

### 3.2 表结构

#### classes（班级表）

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | INTEGER | PK, AUTOINCREMENT | |
| class_name | VARCHAR(64) | NOT NULL, UNIQUE | 如"计科2601班" |
| password_hash | VARCHAR(255) | NOT NULL | bcrypt 哈希 |
| created_at | DATETIME | NOT NULL | |

#### students（学生表）

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | INTEGER | PK | |
| class_id | INTEGER | FK → classes.id, NOT NULL | |
| student_number | VARCHAR(32) | NOT NULL | 学号，文本存储防科学计数 |
| name | VARCHAR(64) | NOT NULL | |
| phone | VARCHAR(32) | NULL | 可选 |
| is_active | BOOLEAN | NOT NULL DEFAULT 1 | 重新上传后旧名单置 0，保留历史 |
| created_at | DATETIME | | |
| updated_at | DATETIME | | |

唯一约束：`(class_id, student_number)` WHERE is_active=1（应用层保证）。

#### attendance_sessions（点名场次表）

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | INTEGER | PK | |
| class_id | INTEGER | FK, NOT NULL | |
| started_at | DATETIME | NULL | 第一次设置状态时写入 |
| finished_at | DATETIME | NULL | 点击结束时写入 |
| status | VARCHAR(16) | NOT NULL DEFAULT 'active' | active / finished |
| created_at | DATETIME | NOT NULL | |

#### attendance_records（点名记录表）

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | INTEGER | PK | |
| session_id | INTEGER | FK, NOT NULL | |
| student_id | INTEGER | FK, NOT NULL | |
| status | VARCHAR(16) | NOT NULL DEFAULT 'pending' | pending/present/late/sick_leave/other |
| remark | VARCHAR(255) | NULL | "其他"时的说明 |
| created_at | DATETIME | | |
| updated_at | DATETIME | | |

唯一约束：`UNIQUE(session_id, student_id)` —— UPSERT 实现幂等。

### 3.3 状态枚举

```
pending    未点名
present    已到
late       迟到
sick_leave 病假
other      其他
```

---

## 四、API 接口设计

统一响应信封：

```json
{ "code": 0, "message": "ok", "data": { ... } }
```

错误时 `code != 0`，HTTP 状态码保持语义化（401/403/404/422/500）。

所有 `/api/classes/{class_id}/*` 与 `/api/attendance/*`（除登录外）均需在 `Authorization: Bearer <token>` 中携带班级 Token，后端校验 Token 中的 class_id 与路径 class_id 一致，实现数据隔离。

### 4.1 班级

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /api/classes | 班级列表（不含密码哈希） |
| POST | /api/classes/login | body: {class_id, password} → {token, class} |

### 4.2 学生

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /api/classes/{class_id}/students | 当前激活学生列表 |
| POST | /api/classes/{class_id}/students/import/preview | 上传 Excel → 返回校验结果（错误行、预览行），不落库 |
| POST | /api/classes/{class_id}/students/import/confirm | 确认导入：旧学生 is_active=0，新学生入库 |

### 4.3 点名

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /api/classes/{class_id}/attendance/active | 获取当前未完成 session（无则 404） |
| POST | /api/classes/{class_id}/attendance/sessions | 创建新 session（开始时间留空，等第一条记录） |
| POST | /api/attendance/{session_id}/record | UPSERT 单条记录；若 session.started_at 为空则自动写入当前时间（幂等） |
| POST | /api/attendance/{session_id}/finish | body: {force: bool} → 写入 finished_at，置 status=finished |
| GET | /api/attendance/{session_id} | 单场详情（学生 + 状态 + 备注） |

### 4.4 历史

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /api/classes/{class_id}/attendance/sessions?date_from=&date_to=&page=&size= | 倒序分页 |
| GET | /api/attendance/{session_id}/summary | 汇总计数 |

### 4.5 导出

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /api/attendance/{session_id}/export | 单场导出 xlsx |
| POST | /api/classes/{class_id}/attendance/export | body: {session_ids: []} 或 {date_from, date_to} → 批量导出 xlsx |

导出响应为 `application/vnd.openxmlformats...`，`Content-Disposition` 携带中文文件名（RFC 5987 编码）。

---

## 五、页面结构设计

| 页面 | 路由 | 核心内容 |
|---|---|---|
| 首页 | /index.html | 5 个大卡片，点击进入登录 |
| 登录 | /login.html?class_id= | 密码输入框 + 登录按钮 |
| 点名页 | /attendance.html?class_id= | 顶部固定状态栏 + 学生卡片流 + 搜索筛选 + 结束按钮 |
| 导入 | /import.html?class_id= | 文件选择 + 预览 + 确认导入 |
| 历史 | /history.html?class_id= | 时间倒序列表 |
| 历史详情 | /history_detail.html?session_id= | 单场完整学生名单 |
| 批量导出 | /export.html?class_id= | 日期范围 / 多选场次 → 导出 |

**硬约束**：核心点名流程无 Modal。"其他"备注在学生卡片行内展开。

---

## 六、手机端 UI 设计方案

- **断点**：基准 375px；`@media (min-width: 768px)` 双列卡片；桌面最大宽度 960px 居中。
- **字体**：基础 16px，学生姓名 18px，学号 14px 等宽。
- **按钮**：最小高度 44px，点击区域 ≥ 48×48dp，圆角 10px。
- **配色**：
  - 已到 `#2e7d32`（绿）
  - 迟到 `#ef6c00`（橙）
  - 病假 `#1565c0`（蓝）
  - 其他 `#6a1b9a`（紫）
  - 未点名 `#9e9e9e`（浅灰）
- **状态选中**：背景色填充 + 白字 + 轻微阴影，未选中为浅灰底深字。
- **顶部固定栏**：班级名、日期、开始/当前时间、已处理 x/y、各状态计数。底部固定"结束本次点名"大按钮。
- **离线指示**：顶部出现红色横条"网络异常，数据暂存本地"，恢复后自动消失。
- **无横向滚动**：`box-sizing: border-box`，卡片 `padding: 12px`，学号用 `tabular-nums`。

---

## 七、Excel 数据结构

### 7.1 导入格式（.xlsx）

首行表头（顺序不限，按列名识别）：

| 学号* | 姓名* | 电话 |
|---|---|---|
| 20260001 | 张三 | 13800138000 |

校验规则：
- 缺"学号"或"姓名"列 → 整表拒绝。
- 学号/姓名为空 → 该行标错，不进入预览。
- 学号重复 → 标错。
- 全空行忽略。
- 电话列可缺省。

### 7.2 单场导出

列：序号 / 学号 / 姓名 / 电话 / 到课状态 / 备注 / 点名开始时间 / 点名结束时间 / 点名日期。

### 7.3 批量导出（多 Sheet）

- **Sheet1 点名明细**：序号、点名日期、开始时间、结束时间、班级、学号、姓名、电话、到课状态、备注。
- **Sheet2 点名汇总**：点名日期、开始时间、结束时间、耗时、总人数、已到、迟到、病假、其他、未点名。
- **Sheet3 学生统计（增强）**：学号、姓名、总次数、已到、迟到、病假、其他。

Excel 样式：首行加粗、冻结首行、自动列宽、学号/电话列设为文本格式（防科学计数法）、状态单元格按文字着色。

### 7.4 文件命名

- 单场：`{班级名}M月D日H点MM分点名情况.xlsx`
- 单日批量：`{班级名}M月D日的到课情况.xlsx`
- 多日批量：`{班级名}M月D日到M月D日的到课情况.xlsx`

---

## 八、点名 Session 生命周期

```
[进入点名页]
   │
   ├─ 后端存在 active session？
   │     ├─ 是 → 恢复该 session，加载已记录的状态
   │     └─ 否 → 前端可点"开始本次点名"创建 session（started_at 仍为 NULL）
   │
[班长点击某学生状态按钮]
   │
   ├─ POST /record（幂等：UPSERT on (session_id, student_id)）
   │     ├─ 若 session.started_at IS NULL → 自动写入 NOW()
   │     └─ 返回最新记录
   │
   ├─ 前端乐观更新 UI + localStorage 暂存
   │     └─ 网络失败 → 标红"未同步"，后台队列重试
   │
[点击"结束本次点名"]
   │
   ├─ 若存在 pending 学生 → 顶部横幅提示"还有 N 人未完成"，给出【继续点名】/【仍然结束】
   │
   └─ POST /finish → finished_at=NOW(), status=finished
         │
         └─ 页面原地展开完成卡片：统计 + [查看本次] [导出] [开始下一次] [返回历史]
```

**同一天多次点名**：每次创建新 session，旧 session 不被修改，`started_at` 天然按时间排序区分。

**刷新恢复**：前端打开点名页时先查 active session，有则恢复；同时 localStorage 缓存未同步操作作为兜底。

---

## 九、安全设计要点

1. 密码 bcrypt 哈希，永不返回前端。
2. Token 为 itsdangerous URLSafeTimedSerializer 签名，payload 仅含 `class_id`，有效期 7 天。
3. 所有 ORM 查询均以 class_id 为过滤条件；依赖 `require_class(token, path_class_id)` 校验一致性。
4. 上传限制：`.xlsx/.xls` 扩展名 + MIME 嗅探 + 大小 ≤ 5MB + openpyxl 加载时校验。
5. 备注/姓名等用户输入在导出 Excel 时按文本写入，不执行公式（openpyxl 默认不解析）。
6. 生产环境 `debug=False`，不暴露 `.db` 文件，Nginx 禁止访问 `data/`、`uploads/`。

---

## 十、Phase 1 交付清单

- [x] 项目目录结构已创建
- [x] 数据库 ER 设计
- [x] API 接口设计
- [x] 页面结构设计
- [x] 移动端 UI 方案
- [x] Excel 结构
- [x] Session 生命周期
- [ ] Phase 2 待开发后端
