#!/bin/bash

# Autovideo 项目快速部署脚本
# 适用于腾讯云轻量服务器 Ubuntu 20.04+

set -e  # 遇到错误立即退出

echo "=========================================="
echo "Autovideo 项目部署脚本"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否为 root 用户
if [ "$EUID" -eq 0 ]; then 
   echo -e "${RED}请不要使用 root 用户运行此脚本${NC}"
   echo "请使用普通用户运行，脚本会在需要时提示输入 sudo 密码"
   exit 1
fi

# 项目路径（Git 克隆会创建 AUTOVideo 目录）
PROJECT_DIR="/var/www/autovideo/AUTOVideo"
BACKEND_DIR="$PROJECT_DIR/center_code/backend"
FRONTEND_DIR="$PROJECT_DIR/center_code/frontend"

# 函数：打印信息
info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 函数：检查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        return 1
    fi
    return 0
}

# 步骤 1: 检查系统环境
info "检查系统环境..."

if ! check_command python3; then
    error "Python3 未安装，请先安装 Python 3.9+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
info "Python 版本: $(python3 --version)"

if ! check_command node; then
    warn "Node.js 未安装，将尝试安装..."
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt install -y nodejs
fi

if ! check_command mysql; then
    warn "MySQL 未安装，将尝试安装..."
    sudo apt install -y mysql-server
    sudo systemctl start mysql
    sudo systemctl enable mysql
fi

if ! check_command nginx; then
    warn "Nginx 未安装，将尝试安装..."
    sudo apt install -y nginx
    sudo systemctl start nginx
    sudo systemctl enable nginx
fi

if ! check_command ffmpeg; then
    warn "FFmpeg 未安装，将尝试安装..."
    sudo apt install -y ffmpeg
fi

info "系统环境检查完成"
echo ""

# 步骤 2: 检查项目目录
info "检查项目目录..."

if [ ! -d "$PROJECT_DIR" ]; then
    error "项目目录不存在: $PROJECT_DIR"
    error "请先将项目上传到服务器，或使用 Git 克隆项目"
    exit 1
fi

if [ ! -d "$BACKEND_DIR" ]; then
    error "后端目录不存在: $BACKEND_DIR"
    exit 1
fi

if [ ! -d "$FRONTEND_DIR" ]; then
    error "前端目录不存在: $FRONTEND_DIR"
    exit 1
fi

info "项目目录检查完成"
echo ""

# 步骤 3: 创建 Python 虚拟环境
info "配置 Python 虚拟环境..."

cd $BACKEND_DIR

if [ ! -d "venv" ]; then
    info "创建虚拟环境..."
    python3 -m venv venv
fi

info "激活虚拟环境并升级 pip..."
source venv/bin/activate
pip install --upgrade pip -q

info "安装 Python 依赖..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    error "requirements.txt 不存在"
    exit 1
fi

info "Python 环境配置完成"
echo ""

# 步骤 4: 配置环境变量
info "配置环境变量..."

if [ ! -f "$BACKEND_DIR/.env" ]; then
    warn ".env 文件不存在，创建示例文件..."
    
    # 生成 Secret Key
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    
    cat > $BACKEND_DIR/.env << EOF
# Flask 环境
FLASK_ENV=production
ENVIRONMENT=production

# 数据库配置（请修改为实际值）
DB_HOST=localhost
DB_PORT=3306
DB_NAME=autovideo
DB_USER=root
DB_PASSWORD=your_password_here

# Flask Secret Key
SECRET_KEY=$SECRET_KEY

# CORS 配置
CORS_ORIGINS=http://localhost,http://127.0.0.1

# AI 配置（请修改为实际值）
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# 百度 TTS 配置（请修改为实际值）
BAIDU_APP_ID=your_baidu_app_id
BAIDU_API_KEY=your_baidu_api_key
BAIDU_SECRET_KEY=your_baidu_secret_key

# FFmpeg 路径
FFMPEG_PATH=/usr/bin/ffmpeg

# 服务端口
PORT=8080
EOF
    
    warn "已创建 .env 文件，请编辑 $BACKEND_DIR/.env 并填入正确的配置"
    warn "特别是数据库密码和 API 密钥"
    read -p "按 Enter 继续（请确保已配置 .env 文件）..."
else
    info ".env 文件已存在"
fi

echo ""

# 步骤 5: 配置数据库
info "配置数据库..."

read -p "是否要初始化数据库？(y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    info "加载环境变量..."
    export $(cat $BACKEND_DIR/.env | grep -v '^#' | xargs)
    
    info "初始化数据库表..."
    python init_database.py || warn "数据库初始化可能失败，请检查配置"
    
    info "创建默认用户..."
    python init_user.py || warn "用户创建可能失败"
fi

echo ""

# 步骤 6: 构建前端
info "构建前端..."

cd $FRONTEND_DIR

if [ ! -d "node_modules" ]; then
    info "安装前端依赖..."
    npm install
fi

info "构建前端生产版本..."
npm run build

if [ ! -d "$BACKEND_DIR/static" ]; then
    error "前端构建失败，static 目录不存在"
    exit 1
fi

info "前端构建完成"
echo ""

# 步骤 7: 配置 systemd 服务
info "配置 systemd 服务..."

SERVICE_FILE="/etc/systemd/system/autovideo.service"
CURRENT_USER=$(whoami)

if [ ! -f "$SERVICE_FILE" ]; then
    info "创建 systemd 服务文件..."
    
    sudo tee $SERVICE_FILE > /dev/null << EOF
[Unit]
Description=Autovideo Flask Application
After=network.target mysql.service

[Service]
Type=simple
User=$CURRENT_USER
Group=$CURRENT_USER
WorkingDirectory=$BACKEND_DIR
Environment="PATH=$BACKEND_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=$BACKEND_DIR/.env
ExecStart=$BACKEND_DIR/venv/bin/python $BACKEND_DIR/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    info "重新加载 systemd..."
    sudo systemctl daemon-reload
    
    info "启动服务..."
    sudo systemctl start autovideo
    sudo systemctl enable autovideo
    
    info "等待服务启动..."
    sleep 3
    
    if sudo systemctl is-active --quiet autovideo; then
        info "服务启动成功"
    else
        error "服务启动失败，请检查日志: sudo journalctl -u autovideo -n 50"
    fi
else
    warn "systemd 服务文件已存在，跳过创建"
    info "重启服务..."
    sudo systemctl restart autovideo
fi

echo ""

# 步骤 8: 配置 Nginx
info "配置 Nginx..."

read -p "请输入域名（如果没有域名，直接按 Enter 使用 IP）: " DOMAIN

if [ -z "$DOMAIN" ]; then
    DOMAIN="_"
fi

NGINX_CONFIG="/etc/nginx/sites-available/autovideo"

if [ ! -f "$NGINX_CONFIG" ]; then
    info "创建 Nginx 配置文件..."
    
    sudo tee $NGINX_CONFIG > /dev/null << EOF
server {
    listen 80;
    server_name $DOMAIN;

    access_log /var/log/nginx/autovideo_access.log;
    error_log /var/log/nginx/autovideo_error.log;

    client_max_body_size 500M;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /static/ {
        alias $BACKEND_DIR/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /uploads/ {
        alias $PROJECT_DIR/center_code/uploads/;
        expires 7d;
        add_header Cache-Control "public";
    }
}
EOF
    
    info "启用 Nginx 配置..."
    sudo ln -sf $NGINX_CONFIG /etc/nginx/sites-enabled/autovideo
    
    # 删除默认配置（如果存在）
    sudo rm -f /etc/nginx/sites-enabled/default
    
    info "测试 Nginx 配置..."
    if sudo nginx -t; then
        info "重新加载 Nginx..."
        sudo systemctl reload nginx
    else
        error "Nginx 配置有误，请检查"
    fi
else
    warn "Nginx 配置文件已存在，跳过创建"
fi

echo ""

# 步骤 9: 配置防火墙
info "配置防火墙..."

if check_command ufw; then
    info "配置 UFW 防火墙..."
    sudo ufw allow 22/tcp
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    echo "y" | sudo ufw enable
    info "防火墙配置完成"
else
    warn "UFW 未安装，跳过防火墙配置"
fi

echo ""

# 步骤 10: 完成
info "=========================================="
info "部署完成！"
info "=========================================="
echo ""
info "服务状态:"
sudo systemctl status autovideo --no-pager -l
echo ""
info "访问地址:"
if [ "$DOMAIN" != "_" ]; then
    echo "  http://$DOMAIN"
else
    echo "  http://$(curl -s ifconfig.me)"
fi
echo ""
info "常用命令:"
echo "  查看服务状态: sudo systemctl status autovideo"
echo "  查看服务日志: sudo journalctl -u autovideo -f"
echo "  重启服务: sudo systemctl restart autovideo"
echo "  查看 Nginx 日志: sudo tail -f /var/log/nginx/autovideo_error.log"
echo ""
warn "重要提示:"
echo "  1. 请确保已正确配置 .env 文件中的数据库密码和 API 密钥"
echo "  2. 如果使用域名，请在域名服务商处配置 A 记录"
echo "  3. 建议配置 SSL 证书（使用 Let's Encrypt）"
echo "  4. 定期备份数据库和重要文件"
echo ""
info "详细文档请查看: DEPLOYMENT_GUIDE.md"
echo ""

