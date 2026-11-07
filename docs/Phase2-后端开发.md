# Phase 2：后端开发汇总

> 日期：2026-09-19

## 一、已完成内容

- FastAPI 项目骨架（配置、数据库会话、异常处理、CORS）
- SQLAlchemy 2.0 数据模型：Class / Student / AttendanceSession / AttendanceRecord
- 统一 JSON 响应信封 `{code, message, data}`
- 班级列表 + 密码登录（bcrypt 哈希，itsdangerous 签名 Token，7 天有效期）
- 学生列表查询、Excel 预览、确认导入（旧名单软删除 is_active=0）
- 点名 Session：创建 / 获取当前活跃 / UPSERT 记录（幂等，第一条自动写 started_at）
- 结束 Session：未强制时返回 1001 提示还有 N 人未完成
- 历史记录列表（按时间倒序）+ 单场详情
- 单场 Excel 导出、批量 Excel 导出（Sheet1 明细 / Sheet2 汇总 / Sheet3 学生统计）
- 中文文件名自动生成（RFC 5987 编码）
- 权限隔离：`require_class` + `require_matching_class` 双校验
- 初始化脚本 `init_db.py`（建表 + 默认 5 班，初始密码 123456）
- 改密脚本 `set_password.py`

## 二、新增/修改文件

```
backend/
├── requirements.txt
├── .env.example
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── main.py
│   ├── database/{__init__,base,session}.py
│   ├── models/{__init__,class_,student,session,record}.py
│   ├── schemas/{__init__,common,class_schema,student_schema,attendance_schema}.py
│   ├── routers/{__init__,classes,students,attendance,history,export}.py
│   ├── services/{__init__,auth_service,excel_service,attendance_service,export_naming}.py
│   └── utils/{__init__,security,timeutil}.py
└── scripts/{__init__,init_db,set_password}.py
```

## 三、本地运行方式

```bash
cd backend
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m scripts.init_db          # 建表 + 创建 5 个班
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
# 浏览器访问 http://127.0.0.1:8000  (前端 Phase 3 后由静态文件挂载)
# API 文档：http://127.0.0.1:8000/docs
```

## 四、已验证的测试项

| 接口 | 结果 |
|---|---|
| GET /api/classes | 返回 5 个班 |
| POST /api/classes/login | 返回 token |
| POST /api/classes/{id}/attendance/sessions | 创建 session，started_at 为空 |
| POST /api/attendance/{id}/record | 第一条自动写 started_at，幂等 UPSERT |
| POST /api/attendance/{id}/finish | 写入 finished_at，状态 finished |
| GET /api/attendance/{id} | 返回学生列表 + 状态 + 备注 + 汇总 |
| GET /api/attendance/{id}/export | 生成单场 xlsx（5.4KB） |
| POST /api/classes/{id}/attendance/export | 生成批量 xlsx（7.1KB，3 Sheet） |

## 五、下一阶段（Phase 3）需要做什么

- 首页 index.html：5 个班级卡片
- 登录页 login.html：密码输入
- 核心点名页 attendance.html：学生卡片流、状态按钮、其他行内展开、顶部进度条、搜索筛选
- 导入页 import.html：文件上传 + 预览 + 确认
- 历史页 history.html + history_detail.html
- 导出页 export.html：日期范围 / 多选场次
- 公共 api.js / storage.js（离线暂存、Token 管理）
- 移动端优先 CSS
