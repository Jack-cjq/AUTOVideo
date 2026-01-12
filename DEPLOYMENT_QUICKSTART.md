# 快速部署指南

本文档提供最快速的部署步骤，详细说明请查看 `DEPLOYMENT_GUIDE.md`。

## 前置条件

- 腾讯云轻量服务器（Ubuntu 20.04+）
- 已通过 SSH 连接到服务器
- 项目文件已上传到服务器（或使用 Git 克隆）

## 方法一：使用自动部署脚本（推荐）

### 1. 上传项目到服务器

```bash
# 在服务器上创建目录
sudo mkdir -p /var/www/autovideo
sudo chown $USER:$USER /var/www/autovideo

# 使用 Git 克隆（推荐）
cd /var/www/autovideo
git clone https://github.com/Jack-cjq/AUTOVideo.git 

# 或使用 SCP 上传（在本地电脑执行）
# scp -r D:\Autovideo root@your_server_ip:/var/www/autovideo
```

### 2. 运行部署脚本

```bash
cd /var/www/autovideo/AUTOVideo
chmod +x deploy.sh
./deploy.sh
```

脚本会自动完成：
- ✅ 检查并安装必要的软件（Python、Node.js、MySQL、Nginx 等）
- ✅ 创建 Python 虚拟环境并安装依赖
- ✅ 创建环境变量配置文件
- ✅ 初始化数据库
- ✅ 构建前端
- ✅ 配置 systemd 服务
- ✅ 配置 Nginx 反向代理
- ✅ 配置防火墙

### 3. 配置环境变量

脚本会创建 `.env` 文件，请编辑并填入正确的配置：

```bash
vim /var/www/autovideo/AUTOVideo/center_code/backend/.env
```

**必须修改的配置**：
- `DB_PASSWORD`: 数据库密码
- `DEEPSEEK_API_KEY`: DeepSeek API 密钥（如果有）
- `BAIDU_APP_ID`, `BAIDU_API_KEY`, `BAIDU_SECRET_KEY`: 百度 TTS 配置（如果有）

### 4. 初始化数据库

如果脚本运行时跳过了数据库初始化，可以手动执行：

```bash
cd /var/www/autovideo/AUTOVideo/center_code/backend
source venv/bin/activate
export $(cat .env | grep -v '^#' | xargs)
python init_database.py
python init_user.py
```

### 5. 访问网站

部署完成后，通过以下地址访问：

- 如果配置了域名: `http://your_domain.com`
- 如果使用 IP: `http://your_server_ip`

---

## 方法二：手动部署

如果自动脚本遇到问题，可以按照以下步骤手动部署：

### 1. 安装基础软件

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.9 python3.9-venv python3-pip nodejs npm mysql-server nginx ffmpeg git
```

### 2. 配置 MySQL

```bash
sudo mysql_secure_installation
sudo mysql -u root -p
```

在 MySQL 中执行：

```sql
CREATE DATABASE autovideo CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EXIT;
```

### 3. 配置 Python 环境

```bash
cd /var/www/autovideo/AUTOVideo/center_code/backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
# 复制并编辑 .env 文件
cp .env.example .env  # 如果没有示例文件，手动创建
vim .env
```

### 5. 初始化数据库

```bash
export $(cat .env | grep -v '^#' | xargs)
python init_database.py
python init_user.py
```

### 6. 构建前端

```bash
cd /var/www/autovideo/AUTOVideo/center_code/frontend
npm install
npm run build
```

### 7. 配置 systemd 服务

```bash
sudo vim /etc/systemd/system/autovideo.service
```

参考 `DEPLOYMENT_GUIDE.md` 中的配置内容。

```bash
sudo systemctl daemon-reload
sudo systemctl start autovideo
sudo systemctl enable autovideo
```

### 8. 配置 Nginx

```bash
sudo vim /etc/nginx/sites-available/autovideo
```

参考 `DEPLOYMENT_GUIDE.md` 中的配置内容。

```bash
sudo ln -s /etc/nginx/sites-available/autovideo /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 验证部署

### 检查服务状态

```bash
# 检查 Flask 应用
sudo systemctl status autovideo

# 检查 Nginx
sudo systemctl status nginx

# 检查 MySQL
sudo systemctl status mysql
```

### 查看日志

```bash
# Flask 应用日志
sudo journalctl -u autovideo -f

# Nginx 错误日志
sudo tail -f /var/log/nginx/autovideo_error.log

# Nginx 访问日志
sudo tail -f /var/log/nginx/autovideo_access.log
```

### 测试访问

```bash
# 测试本地访问
curl http://localhost:8080/api/health

# 测试通过 Nginx 访问
curl http://localhost/api/health
```

---

## 常见问题

### 1. 服务无法启动

```bash
# 查看详细错误
sudo journalctl -u autovideo -n 50

# 检查端口是否被占用
sudo netstat -tlnp | grep 8080
```

### 2. 数据库连接失败

```bash
# 测试数据库连接
mysql -u root -p -h localhost autovideo

# 检查 .env 文件中的数据库配置
cat /var/www/autovideo/AUTOVideo/center_code/backend/.env | grep DB_
```

### 3. 前端页面空白

```bash
# 检查前端文件是否构建成功
ls -la /var/www/autovideo/AUTOVideo/center_code/backend/static/

# 重新构建前端
cd /var/www/autovideo/AUTOVideo/center_code/frontend
npm run build
```

### 4. 文件上传失败

```bash
# 检查上传目录权限
ls -la /var/www/autovideo/AUTOVideo/center_code/uploads/

# 修复权限
sudo chmod -R 755 /var/www/autovideo/AUTOVideo/center_code/uploads/
sudo chown -R $USER:$USER /var/www/autovideo/AUTOVideo/center_code/uploads/
```

---

## 下一步

1. **配置 SSL 证书**（使用 Let's Encrypt）
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d your_domain.com
   ```

2. **配置备份**（参考 `DEPLOYMENT_GUIDE.md` 第 13 节）

3. **性能优化**（参考 `DEPLOYMENT_GUIDE.md` 第 14-15 节）

4. **监控和日志**（配置日志轮转）

---

## 获取帮助

- 详细部署文档: `DEPLOYMENT_GUIDE.md`
- 项目 README: `README.md`
- 端口配置说明: `PORT_CONFIG.md`

如果遇到问题，请查看日志文件或参考详细部署指南。

