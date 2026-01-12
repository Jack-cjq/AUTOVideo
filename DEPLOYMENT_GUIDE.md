# 腾讯云轻量服务器部署指南

本文档详细说明如何将 Autovideo 项目部署到腾讯云轻量服务器上。

## 目录

1. [服务器环境准备](#1-服务器环境准备)
2. [项目上传](#2-项目上传)
3. [环境配置](#3-环境配置)
4. [数据库配置](#4-数据库配置)
5. [前端构建](#5-前端构建)
6. [服务配置](#6-服务配置)
7. [Nginx 反向代理](#7-nginx-反向代理)
8. [防火墙配置](#8-防火墙配置)
9. [域名和 SSL 配置（可选）](#9-域名和-ssl-配置可选)
10. [常见问题排查](#10-常见问题排查)

---

## 1. 服务器环境准备

### 1.1 系统要求

- **操作系统**: Ubuntu 20.04 LTS 或更高版本（推荐）
- **内存**: 至少 2GB RAM
- **磁盘**: 至少 20GB 可用空间
- **网络**: 公网 IP 地址

### 1.2 安装基础软件

```bash
# 更新系统包
sudo apt update && sudo apt upgrade -y

# 安装基础工具
sudo apt install -y git curl wget vim build-essential
```

### 1.3 安装 Python 3.9+

```bash
# 检查 Python 版本（Ubuntu 20.04+ 通常已预装 Python 3.8+）
python3 --version

# 如果没有或版本过低，安装 Python 3.9
sudo apt install -y python3.9 python3.9-venv python3-pip

# 创建软链接（如果需要）
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.9 1
```

### 1.4 安装 Node.js 和 npm

```bash
# 使用 NodeSource 安装 Node.js 18 LTS
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# 验证安装
node --version  # 应该显示 v18.x.x
npm --version
```

### 1.5 安装 MySQL

```bash
# 安装 MySQL Server
sudo apt install -y mysql-server

# 启动 MySQL 服务
sudo systemctl start mysql
sudo systemctl enable mysql

# 运行安全配置脚本
sudo mysql_secure_installation

# 登录 MySQL 创建数据库
sudo mysql -u root -p
```

在 MySQL 中执行：

```sql
-- 创建数据库
CREATE DATABASE autovideo CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 创建用户（可选，也可以直接使用 root）
CREATE USER 'autovideo'@'localhost' IDENTIFIED BY 'your_strong_password';
GRANT ALL PRIVILEGES ON autovideo.* TO 'autovideo'@'localhost';
FLUSH PRIVILEGES;

-- 退出
EXIT;
```

### 1.6 安装 FFmpeg（视频处理需要）

```bash
# 安装 FFmpeg
sudo apt install -y ffmpeg

# 验证安装
ffmpeg -version
```

### 1.7 安装 Nginx

```bash
# 安装 Nginx
sudo apt install -y nginx

# 启动并设置开机自启
sudo systemctl start nginx
sudo systemctl enable nginx

# 验证安装
sudo systemctl status nginx
```

### 1.8 安装 Playwright 浏览器依赖（如果需要）

```bash
# 安装 Playwright 系统依赖
sudo apt install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2
```

---

## 2. 项目上传

### 2.1 方法一：使用 Git（推荐）

如果项目在 Git 仓库中：

```bash
# 创建项目目录
sudo mkdir -p /var/www/autovideo
sudo chown $USER:$USER /var/www/autovideo
cd /var/www/autovideo

# 克隆项目（替换为你的仓库地址）
git clone <your-repository-url> .

# 或者如果项目在本地，先推送到远程仓库
```

### 2.2 方法二：使用 SCP 上传

在本地电脑上执行：

```bash
# Windows PowerShell
scp -r D:\Autovideo root@your_server_ip:/var/www/autovideo

# Linux/Mac
scp -r /path/to/Autovideo root@your_server_ip:/var/www/autovideo
```

### 2.3 方法三：使用 FTP/SFTP 工具

使用 FileZilla、WinSCP 等工具上传项目文件。

### 2.4 设置项目权限

```bash
cd /var/www/autovideo
sudo chown -R $USER:$USER .
chmod -R 755 .
```

---

## 3. 环境配置

### 3.1 创建 Python 虚拟环境

```bash
cd /var/www/autovideo/center_code/backend

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 升级 pip
pip install --upgrade pip
```

### 3.2 安装 Python 依赖

```bash
# 确保虚拟环境已激活
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器（如果需要）
playwright install chromium
playwright install-deps chromium
```

### 3.3 配置环境变量

创建环境变量配置文件：

```bash
cd /var/www/autovideo/center_code/backend
vim .env
```

添加以下内容（根据实际情况修改）：

```bash
# Flask 环境
FLASK_ENV=production
ENVIRONMENT=production

# 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_NAME=autovideo
DB_USER=autovideo
DB_PASSWORD=your_strong_password

# Flask Secret Key（生成方式：python -c "import secrets; print(secrets.token_hex(32))"）
SECRET_KEY=your_generated_secret_key_here

# CORS 配置（生产环境使用你的域名）
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# AI 配置（DeepSeek）
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# 百度 TTS 配置
BAIDU_APP_ID=your_baidu_app_id
BAIDU_API_KEY=your_baidu_api_key
BAIDU_SECRET_KEY=your_baidu_secret_key

# FFmpeg 路径（如果不在系统 PATH 中）
FFMPEG_PATH=/usr/bin/ffmpeg

# 服务端口
PORT=8080
```

### 3.4 创建启动脚本

```bash
cd /var/www/autovideo/center_code/backend
vim start_production.sh
```

添加以下内容：

```bash
#!/bin/bash

# 激活虚拟环境
cd /var/www/autovideo/center_code/backend
source venv/bin/activate

# 加载环境变量
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# 启动应用
python app.py
```

设置执行权限：

```bash
chmod +x start_production.sh
```

---

## 4. 数据库配置

### 4.1 初始化数据库

```bash
cd /var/www/autovideo/center_code/backend
source venv/bin/activate

# 加载环境变量
export $(cat .env | grep -v '^#' | xargs)

# 初始化数据库表
python init_database.py

# 创建默认用户
python init_user.py
```

### 4.2 验证数据库连接

```bash
python test_db.py
```

---

## 5. 前端构建

### 5.1 安装前端依赖

```bash
cd /var/www/autovideo/center_code/frontend

# 安装依赖
npm install
```

### 5.2 配置生产环境 API 地址

如果需要修改生产环境的 API 地址，可以：

1. 修改 `vite.config.js` 中的代理配置
2. 或者在构建时设置环境变量

### 5.3 构建前端

```bash
# 确保在 frontend 目录
cd /var/www/autovideo/center_code/frontend

# 构建生产版本（会自动输出到 backend/static 目录）
npm run build
```

构建完成后，前端文件会在 `center_code/backend/static` 目录中。

---

## 6. 服务配置

### 6.1 使用 systemd 管理服务（推荐）

创建 systemd 服务文件：

```bash
sudo vim /etc/systemd/system/autovideo.service
```

添加以下内容：

```ini
[Unit]
Description=Autovideo Flask Application
After=network.target mysql.service

[Service]
Type=simple
User=your_username
Group=your_username
WorkingDirectory=/var/www/autovideo/center_code/backend
Environment="PATH=/var/www/autovideo/center_code/backend/venv/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=/var/www/autovideo/center_code/backend/.env
ExecStart=/var/www/autovideo/center_code/backend/venv/bin/python /var/www/autovideo/center_code/backend/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**注意**: 将 `your_username` 替换为你的实际用户名。

启动服务：

```bash
# 重新加载 systemd
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start autovideo

# 设置开机自启
sudo systemctl enable autovideo

# 查看服务状态
sudo systemctl status autovideo

# 查看日志
sudo journalctl -u autovideo -f
```

### 6.2 使用 Supervisor（备选方案）

如果不想使用 systemd，可以使用 Supervisor：

```bash
# 安装 Supervisor
sudo apt install -y supervisor

# 创建配置文件
sudo vim /etc/supervisor/conf.d/autovideo.conf
```

添加以下内容：

```ini
[program:autovideo]
command=/var/www/autovideo/center_code/backend/venv/bin/python /var/www/autovideo/center_code/backend/app.py
directory=/var/www/autovideo/center_code/backend
user=your_username
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/www/autovideo/logs/app.log
environment=FLASK_ENV="production",ENVIRONMENT="production"
```

启动 Supervisor：

```bash
# 重新加载配置
sudo supervisorctl reread
sudo supervisorctl update

# 启动服务
sudo supervisorctl start autovideo

# 查看状态
sudo supervisorctl status autovideo
```

---

## 7. Nginx 反向代理

### 7.1 配置 Nginx

创建 Nginx 配置文件：

```bash
sudo vim /etc/nginx/sites-available/autovideo
```

添加以下内容（根据实际情况修改域名和端口）：

```nginx
server {
    listen 80;
    server_name your_domain.com www.your_domain.com;  # 替换为你的域名，如果没有域名则使用服务器 IP

    # 日志
    access_log /var/log/nginx/autovideo_access.log;
    error_log /var/log/nginx/autovideo_error.log;

    # 客户端最大上传文件大小（根据需求调整）
    client_max_body_size 500M;

    # 代理到 Flask 应用
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 支持（如果需要）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # 静态文件直接由 Nginx 提供（可选，提高性能）
    location /static/ {
        alias /var/www/autovideo/center_code/backend/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # 上传文件访问
    location /uploads/ {
        alias /var/www/autovideo/center_code/uploads/;
        expires 7d;
        add_header Cache-Control "public";
    }
}
```

### 7.2 启用配置

```bash
# 创建软链接
sudo ln -s /etc/nginx/sites-available/autovideo /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重新加载 Nginx
sudo systemctl reload nginx
```

---

## 8. 防火墙配置

### 8.1 配置 UFW 防火墙

```bash
# 允许 SSH（重要！）
sudo ufw allow 22/tcp

# 允许 HTTP
sudo ufw allow 80/tcp

# 允许 HTTPS（如果使用 SSL）
sudo ufw allow 443/tcp

# 启用防火墙
sudo ufw enable

# 查看状态
sudo ufw status
```

### 8.2 腾讯云安全组配置

在腾讯云控制台配置安全组规则：

1. 登录腾讯云控制台
2. 进入「轻量应用服务器」→「防火墙」
3. 添加规则：
   - **HTTP**: 端口 80，协议 TCP，来源 0.0.0.0/0
   - **HTTPS**: 端口 443，协议 TCP，来源 0.0.0.0/0
   - **SSH**: 端口 22，协议 TCP，来源 0.0.0.0/0（建议限制为你的 IP）

---

## 9. 域名和 SSL 配置（可选）

### 9.1 配置域名解析

在域名服务商处添加 A 记录，将域名指向服务器 IP。

### 9.2 使用 Let's Encrypt 免费 SSL 证书

```bash
# 安装 Certbot
sudo apt install -y certbot python3-certbot-nginx

# 获取证书（自动配置 Nginx）
sudo certbot --nginx -d your_domain.com -d www.your_domain.com

# 测试自动续期
sudo certbot renew --dry-run
```

证书会自动续期，Nginx 配置也会自动更新为 HTTPS。

### 9.3 更新 Flask 配置

如果使用 HTTPS，需要更新 Flask 配置：

在 `.env` 文件中确保：

```bash
FLASK_ENV=production
ENVIRONMENT=production
```

Flask 会自动启用 `SESSION_COOKIE_SECURE`。

---

## 10. 常见问题排查

### 10.1 服务无法启动

```bash
# 查看服务状态
sudo systemctl status autovideo

# 查看详细日志
sudo journalctl -u autovideo -n 100

# 检查端口是否被占用
sudo netstat -tlnp | grep 8080
```

### 10.2 数据库连接失败

```bash
# 测试数据库连接
mysql -u autovideo -p -h localhost autovideo

# 检查 MySQL 服务状态
sudo systemctl status mysql

# 查看 MySQL 日志
sudo tail -f /var/log/mysql/error.log
```

### 10.3 前端页面无法访问

```bash
# 检查 Nginx 状态
sudo systemctl status nginx

# 查看 Nginx 错误日志
sudo tail -f /var/log/nginx/autovideo_error.log

# 检查前端文件是否存在
ls -la /var/www/autovideo/center_code/backend/static/
```

### 10.4 文件上传失败

```bash
# 检查上传目录权限
ls -la /var/www/autovideo/center_code/uploads/

# 确保目录可写
sudo chmod -R 755 /var/www/autovideo/center_code/uploads/
sudo chown -R your_username:your_username /var/www/autovideo/center_code/uploads/

# 检查 Nginx client_max_body_size 配置
```

### 10.5 Playwright 相关问题

```bash
# 重新安装 Playwright 浏览器
cd /var/www/autovideo/center_code/backend
source venv/bin/activate
playwright install chromium
playwright install-deps chromium
```

### 10.6 查看实时日志

```bash
# Flask 应用日志（如果使用 systemd）
sudo journalctl -u autovideo -f

# Nginx 访问日志
sudo tail -f /var/log/nginx/autovideo_access.log

# Nginx 错误日志
sudo tail -f /var/log/nginx/autovideo_error.log
```

---

## 11. 部署检查清单

部署完成后，请检查以下项目：

- [ ] Python 虚拟环境已创建并激活
- [ ] 所有 Python 依赖已安装
- [ ] 数据库已创建并初始化
- [ ] 环境变量文件 `.env` 已配置
- [ ] 前端已构建（`backend/static` 目录有文件）
- [ ] systemd 服务已启动并设置为开机自启
- [ ] Nginx 配置已启用并重新加载
- [ ] 防火墙规则已配置
- [ ] 可以通过域名或 IP 访问网站
- [ ] 数据库连接正常
- [ ] 文件上传功能正常
- [ ] 日志文件正常生成

---

## 12. 更新部署

当需要更新代码时：

```bash
# 1. 进入项目目录
cd /var/www/autovideo

# 2. 拉取最新代码（如果使用 Git）
git pull

# 3. 更新 Python 依赖（如果有新依赖）
cd center_code/backend
source venv/bin/activate
pip install -r requirements.txt

# 4. 重新构建前端（如果有前端更新）
cd ../frontend
npm install
npm run build

# 5. 重启服务
sudo systemctl restart autovideo

# 6. 检查服务状态
sudo systemctl status autovideo
```

---

## 13. 备份建议

### 13.1 数据库备份

```bash
# 创建备份脚本
vim /var/www/autovideo/backup_db.sh
```

添加内容：

```bash
#!/bin/bash
BACKUP_DIR="/var/www/autovideo/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# 备份数据库
mysqldump -u autovideo -p'your_password' autovideo > $BACKUP_DIR/db_$DATE.sql

# 删除 7 天前的备份
find $BACKUP_DIR -name "db_*.sql" -mtime +7 -delete
```

设置定时任务：

```bash
# 编辑 crontab
crontab -e

# 添加每天凌晨 2 点备份
0 2 * * * /var/www/autovideo/backup_db.sh
```

### 13.2 文件备份

```bash
# 备份上传的文件
tar -czf /var/www/autovideo/backups/uploads_$(date +%Y%m%d).tar.gz /var/www/autovideo/center_code/uploads/
```

---

## 14. 性能优化建议

1. **启用 Nginx 缓存**: 对静态文件启用缓存
2. **使用 Gunicorn**: 生产环境建议使用 Gunicorn + Nginx，而不是 Flask 开发服务器
3. **数据库优化**: 根据数据量添加适当的索引
4. **CDN 加速**: 如果有条件，使用 CDN 加速静态资源
5. **监控和日志**: 配置日志轮转，避免日志文件过大

---

## 15. 使用 Gunicorn（生产环境推荐）

### 15.1 安装 Gunicorn

```bash
cd /var/www/autovideo/center_code/backend
source venv/bin/activate
pip install gunicorn
```

### 15.2 创建 Gunicorn 配置文件

```bash
vim gunicorn_config.py
```

添加内容：

```python
bind = "127.0.0.1:8080"
workers = 4
worker_class = "sync"
worker_connections = 1000
timeout = 60
keepalive = 5
max_requests = 1000
max_requests_jitter = 50
preload_app = True
```

### 15.3 更新 systemd 服务

修改 `/etc/systemd/system/autovideo.service`：

```ini
[Unit]
Description=Autovideo Flask Application
After=network.target mysql.service

[Service]
Type=simple
User=your_username
Group=your_username
WorkingDirectory=/var/www/autovideo/center_code/backend
Environment="PATH=/var/www/autovideo/center_code/backend/venv/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=/var/www/autovideo/center_code/backend/.env
ExecStart=/var/www/autovideo/center_code/backend/venv/bin/gunicorn -c gunicorn_config.py app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

重启服务：

```bash
sudo systemctl daemon-reload
sudo systemctl restart autovideo
```

---

## 总结

完成以上步骤后，你的 Autovideo 项目应该已经成功部署到腾讯云轻量服务器上。如果遇到问题，请参考「常见问题排查」部分，或查看相关日志文件。

**重要提示**:
- 生产环境务必使用强密码
- 定期更新系统和依赖包
- 定期备份数据库和重要文件
- 监控服务器资源使用情况
- 配置日志轮转避免磁盘空间不足

祝部署顺利！🎉

