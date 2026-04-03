#!/bin/bash
# Allo 数据备份脚本
# 用法：sudo -u allo /usr/local/bin/allo-backup
# Cron: 0 2 * * * /usr/local/bin/allo-backup >> /var/log/allo/backup.log 2>&1

set -e

# ==========================================
# 配置
# ==========================================
BACKUP_ROOT="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${BACKUP_ROOT}/${TIMESTAMP}"
RETENTION_DAYS=30

# 数据库配置（从环境变量读取）
source /etc/allo/allo.env
DB_HOST="127.0.0.1"
DB_NAME="allo"
DB_USER="allo"
DB_PASSWORD="${POSTGRES_PASSWORD}"

# Redis 配置
REDIS_PASSWORD="${REDIS_PASSWORD}"
REDIS_DUMP="/var/lib/redis/dump.rdb"

# 用户数据目录
USER_DATA_DIR="/var/lib/allo/users"

# ==========================================
# 日志函数
# ==========================================
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" >&2
}

# ==========================================
# 创建备份目录
# ==========================================
log "开始备份到 ${BACKUP_DIR}"
mkdir -p "${BACKUP_DIR}"

# ==========================================
# 备份 PostgreSQL
# ==========================================
log "备份 PostgreSQL 数据库..."
export PGPASSWORD="${DB_PASSWORD}"
if pg_dump -h "${DB_HOST}" -U "${DB_USER}" -d "${DB_NAME}" | gzip > "${BACKUP_DIR}/allo.sql.gz"; then
    log "PostgreSQL 备份成功: $(du -h ${BACKUP_DIR}/allo.sql.gz | cut -f1)"
else
    error "PostgreSQL 备份失败"
    exit 1
fi
unset PGPASSWORD

# ==========================================
# 备份 Redis
# ==========================================
log "备份 Redis 数据..."
if redis-cli -a "${REDIS_PASSWORD}" BGSAVE > /dev/null 2>&1; then
    # 等待 BGSAVE 完成
    sleep 5
    
    # 检查 BGSAVE 是否成功
    LAST_SAVE=$(redis-cli -a "${REDIS_PASSWORD}" LASTSAVE 2>/dev/null)
    if [ -n "${LAST_SAVE}" ]; then
        if [ -f "${REDIS_DUMP}" ]; then
            cp "${REDIS_DUMP}" "${BACKUP_DIR}/redis.rdb"
            log "Redis 备份成功: $(du -h ${BACKUP_DIR}/redis.rdb | cut -f1)"
        else
            error "Redis dump 文件不存在: ${REDIS_DUMP}"
        fi
    else
        error "Redis BGSAVE 失败"
    fi
else
    error "Redis 备份命令执行失败"
fi

# ==========================================
# 备份用户数据文件
# ==========================================
log "备份用户数据文件..."
if [ -d "${USER_DATA_DIR}" ]; then
    if tar czf "${BACKUP_DIR}/user-data.tar.gz" -C "$(dirname ${USER_DATA_DIR})" "$(basename ${USER_DATA_DIR})"; then
        log "用户数据备份成功: $(du -h ${BACKUP_DIR}/user-data.tar.gz | cut -f1)"
    else
        error "用户数据备份失败"
    fi
else
    log "用户数据目录不存在，跳过: ${USER_DATA_DIR}"
fi

# ==========================================
# 备份配置文件
# ==========================================
log "备份配置文件..."
mkdir -p "${BACKUP_DIR}/config"

# 备份环境变量（敏感信息，需加密或限制权限）
if [ -f "/etc/allo/allo.env" ]; then
    cp /etc/allo/allo.env "${BACKUP_DIR}/config/allo.env"
    chmod 600 "${BACKUP_DIR}/config/allo.env"
fi

# 备份应用配置
if [ -f "/srv/allo/config.yaml" ]; then
    cp /srv/allo/config.yaml "${BACKUP_DIR}/config/config.yaml"
fi

# 备份 nginx 配置
if [ -f "/etc/nginx/sites-available/allo" ]; then
    cp /etc/nginx/sites-available/allo "${BACKUP_DIR}/config/nginx-allo.conf"
fi

log "配置文件备份完成"

# ==========================================
# 生成备份清单
# ==========================================
log "生成备份清单..."
cat > "${BACKUP_DIR}/manifest.txt" <<EOF
Allo 备份清单
===========================================
备份时间: ${TIMESTAMP}
备份目录: ${BACKUP_DIR}

文件列表:
$(ls -lh ${BACKUP_DIR})

总大小: $(du -sh ${BACKUP_DIR} | cut -f1)
===========================================
EOF

# ==========================================
# 清理旧备份
# ==========================================
log "清理 ${RETENTION_DAYS} 天前的旧备份..."
find "${BACKUP_ROOT}" -maxdepth 1 -type d -name "20*" -mtime +${RETENTION_DAYS} -exec rm -rf {} \;

# ==========================================
# 完成
# ==========================================
log "备份完成！"
log "备份位置: ${BACKUP_DIR}"
log "总大小: $(du -sh ${BACKUP_DIR} | cut -f1)"
log "当前备份数量: $(find ${BACKUP_ROOT} -maxdepth 1 -type d -name '20*' | wc -l)"

exit 0
