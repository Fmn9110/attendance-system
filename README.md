# 线上班级点名管理系统

手机端优先的班级点名系统：班级密码登录 → 上传 Excel 花名册 → 单页直接点名 → 自动保存时间 → 历史查询 → Excel 导出。

## 技术栈

- 前端：原生 HTML + CSS + JavaScript
- 后端：Python FastAPI
- 数据库：SQLite（可切换 MySQL/PostgreSQL）
- 部署：Nginx + Uvicorn + Systemd（Ubuntu 22.04）

---

## 一、Windows 本地运行

```powershell
# 1. 进入 backend 目录
cd backend

# 2. 创建虚拟环境（首次）
python -m venv .venv
.venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 初始化数据库（创建 5 个班，初始密码 123456）
python -m scripts.init_db

# 5. 启动后端（同时托管前端静态文件）
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 6. 浏览器访问
#    http://127.0.0.1:8000
```

## 二、macOS / Linux 本地运行

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m scripts.init_db
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 三、Python 版本要求

- Python 3.10+（开发环境使用 3.14）
- 需要安装 `sqlite3` 系统库（Ubuntu: `apt install sqlite3`）

## 四、配置

复制 `backend/.env.example` 为 `backend/.env` 并修改：

```ini
DATABASE_URL=sqlite:///./data/attendance.db
SECRET_KEY=请改为随机长字符串
SESSION_EXPIRE_DAYS=7
MAX_UPLOAD_MB=5
```

切换到 MySQL/PostgreSQL 时修改 `DATABASE_URL` 即可，例如：

```
DATABASE_URL=mysql+pymysql://user:pass@localhost/attendance?charset=utf8mb4
DATABASE_URL=postgresql+psycopg2://user:pass@localhost/attendance
```

## 五、设置班级密码

```bash
cd backend
python -m scripts.set_password.py 计科2601班 your_new_password
```

## 六、Excel 花名册格式

首行表头，列名按名称识别（顺序不限）：

| 学号* | 姓名* | 电话 |
|---|---|---|
| 20260001 | 张三 | 13800138000 |
| 20260002 | 李四 | |

- `*` 为必填列
- 电话列可省略
- 支持 .xlsx（优先）和 .xls
- 学号/姓名为空、学号重复的行会被标记错误
- 空白行自动忽略

## 七、Ubuntu 22.04 部署

```bash
# 1. 安装依赖
sudo apt update
sudo apt install -y python3 python3-pip python3-venv sqlite3 nginx

# 2. 上传项目到 /opt/attendance
sudo mkdir -p /opt/attendance
sudo chown -R $USER:$USER /opt/attendance
# 将项目文件上传到 /opt/attendance

# 3. 创建虚拟环境并安装依赖
cd /opt/attendance/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 4. 初始化
python -m scripts.init_db
python -m scripts.set_password.py 计科2601班 your_password

# 5. 配置 systemd
sudo cp /opt/attendance/deploy/attendance.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now attendance

# 6. 配置 Nginx
sudo cp /opt/attendance/deploy/nginx.conf /etc/nginx/sites-available/attendance
sudo ln -s /etc/nginx/sites-available/attendance /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx

# 7. 开放防火墙
sudo ufw allow 80
sudo ufw allow 443
```

## 八、HTTPS 配置（推荐）

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

certbot 会自动修改 Nginx 配置并申请续期。

## 九、数据库备份

```bash
# 手动备份
chmod +x /opt/attendance/deploy/backup.sh
/opt/attendance/deploy/backup.sh /opt/attendance/backups

# 每天凌晨 2 点自动备份（crontab -e）
0 2 * * * /opt/attendance/deploy/backup.sh /opt/attendance/backups
```

恢复备份：

```bash
gunzip -k attendance_backup_2026-09-19.db.gz
sudo systemctl stop attendance
cp attendance_backup_2026-09-19.db /opt/attendance/backend/data/attendance.db
sudo systemctl start attendance
```

## 十、常用命令

```bash
# 查看服务状态
sudo systemctl status attendance

# 查看日志
journalctl -u attendance -f

# 重启服务
sudo systemctl restart attendance
```

## 十一、目录结构

```
attendance-system/
├── backend/          # FastAPI 后端
│   ├── app/          # 应用代码
│   ├── data/         # SQLite 数据库
│   ├── uploads/      # 临时上传
│   ├── scripts/      # 初始化/改密/测试脚本
│   └── requirements.txt
├── frontend/         # 静态 HTML/CSS/JS
├── deploy/           # systemd / nginx / backup
├── docs/             # 各 Phase 开发文档
└── README.md
```
