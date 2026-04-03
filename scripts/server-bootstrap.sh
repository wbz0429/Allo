#!/bin/bash
# Allo 服务器环境自动化部署脚本
# 用法：sudo bash scripts/server-bootstrap.sh

set -e

echo "=========================================="
echo "Allo 服务器环境初始化脚本"
echo "=========================================="

# 检查是否为 root
if [ "$EUID" -ne 0 ]; then 
    echo "错误：请使用 root 或 sudo 运行此脚本"
    exit 1
fi

# 检查操作系统
if [ ! -f /etc/os-release ]; then
    echo "错误：无法检测操作系统版本"
    exit 1
fi

source /etc/os-release
if [[ "$ID" != "ubuntu" ]]; then
    echo "警告：此脚本仅在 Ubuntu 上测试过，当前系统：$ID"
    read -p "是否继续？(y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "检测到系统：$PRETTY_NAME"
echo ""

# ==========================================
# 第一步：更新系统
# ==========================================
echo "[1/10] 更新系统软件包..."
apt update
apt upgrade -y

# ==========================================
# 第二步：安装基础工具
# ==========================================
echo "[2/10] 安装基础工具..."
apt install -y curl wget git vim build-essential software-properties-common

# ==========================================
# 第三步：安装 PostgreSQL 16
# ==========================================
echo "[3/10] 安装 PostgreSQL 16..."
if ! command -v psql &> /dev/null; then
    apt install -y postgresql-16 postgresql-contrib-16
    systemctl enable postgresql
    systemctl start postgresql
    echo "PostgreSQL 安装完成"
else
    echo "PostgreSQL 已安装，跳过"
fi

# ==========================================
# 第四步：安装 Redis
# ==========================================
echo "[4/10] 安装 Redis..."
if ! command -v redis-cli &> /dev/null; then
    apt install -y redis-server
    systemctl enable redis-server
    systemctl start redis-server
    echo "Redis 安装完成"
else
    echo "Redis 已安装，跳过"
fi

# ==========================================
# 第五步：安装 nginx
# ==========================================
echo "[5/10] 安装 nginx..."
if ! command -v nginx &> /dev/null; then
    apt install -y nginx
    systemctl enable nginx
    systemctl start nginx
    echo "nginx 安装完成"
else
    echo "nginx 已安装，跳过"
fi

# ==========================================
# 第六步：安装 Python 3.12
# ==========================================
echo "[6/10] 安装 Python 3.12..."
if ! command -v python3.12 &> /dev/null; then
    # Ubuntu 24.04 自带 3.12，22.04 需要 PPA
    if [[ "$VERSION_ID" == "22.04" ]]; then
        add-apt-repository -y ppa:deadsnakes/ppa
        apt update
    fi
    apt install -y python3.12 python3.12-venv python3.12-dev
    echo "Python 3.12 安装完成"
else
    echo "Python 3.12 已安装，跳过"
fi

# ==========================================
# 第七步：安装 uv
# ==========================================
echo "[7/10] 安装 uv..."
if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo "uv 安装完成"
else
    echo "uv 已安装，跳过"
fi

# ==========================================
# 第八步：安装 Node.js 22
# ==========================================
echo "[8/10] 安装 Node.js 22..."
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
    apt install -y nodejs
    echo "Node.js 安装完成"
else
    NODE_VERSION=$(node -v)
    echo "Node.js 已安装：$NODE_VERSION"
fi

# 安装 pnpm
if ! command -v pnpm &> /dev/null; then
    npm install -g pnpm
    echo "pnpm 安装完成"
else
    echo "pnpm 已安装，跳过"
fi

# ==========================================
# 第九步：安装 Docker
# ==========================================
echo "[9/10] 安装 Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    echo "Docker 安装完成"
else
    echo "Docker 已安装，跳过"
fi

# ==========================================
# 第十步：创建应用用户和目录
# ==========================================
echo "[10/10] 创建应用用户和目录..."

# 创建 allo 用户
if ! id -u allo &> /dev/null; then
    useradd -r -m -s /bin/bash allo
    echo "用户 allo 创建完成"
else
    echo "用户 allo 已存在，跳过"
fi

# 创建目录
mkdir -p /srv/allo
mkdir -p /var/lib/allo/users
mkdir -p /var/log/allo
mkdir -p /backups
mkdir -p /etc/allo

# 设置权限
chown -R allo:allo /srv/allo
chown -R allo:allo /var/lib/allo
chown -R allo:allo /var/log/allo
chown -R allo:allo /backups
chown -R allo:allo /etc/allo

echo "目录创建完成"

# ==========================================
# 完成
# ==========================================
echo ""
echo "=========================================="
echo "环境初始化完成！"
echo "=========================================="
echo ""
echo "已安装的软件："
echo "  - PostgreSQL: $(psql --version | head -n1)"
echo "  - Redis: $(redis-server --version)"
echo "  - nginx: $(nginx -v 2>&1)"
echo "  - Python: $(python3.12 --version)"
echo "  - Node.js: $(node -v)"
echo "  - pnpm: $(pnpm -v)"
echo "  - Docker: $(docker --version)"
echo ""
echo "已创建的目录："
echo "  - /srv/allo          (应用代码)"
echo "  - /var/lib/allo      (用户数据)"
echo "  - /var/log/allo      (日志)"
echo "  - /backups           (备份)"
echo "  - /etc/allo          (配置)"
echo ""
echo "下一步："
echo "  1. 配置 PostgreSQL 数据库（参考《服务器环境准备指南.md》第三步）"
echo "  2. 配置 Redis 密码（参考第四步）"
echo "  3. 部署应用代码到 /srv/allo"
echo "  4. 配置环境变量 /etc/allo/allo.env"
echo "  5. 运行数据库迁移"
echo "  6. 安装 systemd 服务"
echo ""
