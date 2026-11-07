# Phase 6：Ubuntu 22.04 部署文档汇总

> 日期：2026-09-19

## 一、已完成内容

- `deploy/attendance.service`：Systemd 单元（开机自启、崩溃重启、日志 journal）
- `deploy/nginx.conf`：Nginx 反向代理（静态文件、API 代理、gzip、安全头、HTTPS 示例）
- `deploy/backup.sh`：SQLite 在线备份（保留 30 天、自动压缩）
- `README.md`：完整部署文档（Windows/Linux 本地运行、Ubuntu 部署、HTTPS、备份恢复）

## 二、部署架构

```
手机浏览器
   ↓ HTTP/HTTPS
Nginx (80/443)
   ↓ proxy_pass
Uvicorn (127.0.0.1:8000, 2 workers)
   ↓
FastAPI
   ↓
SQLite (/opt/attendance/backend/data/attendance.db)
```

## 三、部署步骤（摘要）

```bash
# 服务器上
sudo apt install -y python3 python3-venv sqlite3 nginx
cd /opt/attendance/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m scripts.init_db
python -m scripts.set_password.py 计科2601班 <your_password>

sudo cp deploy/attendance.service /etc/systemd/system/
sudo systemctl enable --now attendance

sudo cp deploy/nginx.conf /etc/nginx/sites-available/attendance
sudo ln -s /etc/nginx/sites-available/attendance /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl restart nginx
```

## 四、安全要点

- 密码 bcrypt 哈希存储
- Token 签名 7 天过期
- Nginx 禁止访问 backend/uploads/data 目录
- 上传文件大小限制 5MB
- 文件类型校验（.xlsx/.xls）
- 生产环境 `debug=false`

## 五、最终验收

对照需求文档第三十五节验收清单，全部 40 项均已在 Phase 5 测试通过。
