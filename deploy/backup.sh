#!/bin/bash
# 数据库备份脚本
# 用法: ./backup.sh [备份目录]
# 建议 crontab: 0 2 * * * /opt/attendance/deploy/backup.sh /opt/attendance/backups

set -e

DB_PATH="/opt/attendance/backend/data/attendance.db"
BACKUP_DIR="${1:-/opt/attendance/backups}"
DATE=$(date +%Y-%m-%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/attendance_backup_${DATE}.db"

mkdir -p "$BACKUP_DIR"

# SQLite 在线备份（不影响运行中的服务）
sqlite3 "$DB_PATH" ".backup '$BACKUP_FILE'"

# 压缩
gzip -f "$BACKUP_FILE"

# 保留最近 30 天的备份
find "$BACKUP_DIR" -name "attendance_backup_*.db.gz" -mtime +30 -delete

echo "备份完成: ${BACKUP_FILE}.gz"
