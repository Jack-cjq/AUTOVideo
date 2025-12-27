# 抖音中心管理平台

前后端分离版本，使用 Vue 3 + Element Plus 前端，Flask + MySQL 后端。

## 项目结构

```
center_code/
├── frontend/          # Vue 3 + Element Plus 前端
│   ├── src/
│   │   ├── api/       # API 服务层
│   │   ├── components/ # Vue 组件
│   │   ├── stores/    # Pinia 状态管理
│   │   ├── views/     # 页面视图
│   │   └── router/    # 路由配置
│   └── package.json
├── backend/           # Flask 后端（模块化设计）
│   ├── app.py         # 主应用文件
│   ├── config.py      # 数据库配置（MySQL）
│   ├── db.py          # 数据库连接管理
│   ├── models.py      # 数据模型定义
│   ├── utils.py       # 工具函数
│   ├── blueprints/    # API 模块（按功能分块）
│   │   ├── __init__.py
│   │   ├── auth.py    # 认证模块
│   │   ├── devices.py # 设备管理
│   │   ├── accounts.py # 账号管理
│   │   ├── video.py    # 视频上传
│   │   ├── chat.py    # 对话功能
│   │   ├── listen.py  # 监听功能
│   │   ├── social.py  # 社交平台
│   │   ├── messages.py # 消息管理
│   │   ├── stats.py   # 统计
│   │   └── login.py   # 登录相关
│   └── requirements.txt
└── README.md
```

## 环境要求

- Python 3.8+
- Node.js 16+
- MySQL 8+（默认使用 MySQL）

## 安装步骤

### 1. 数据库设置（MySQL）

#### 1.1 创建数据库
```bash
mysql -u root -p
CREATE DATABASE autovideo CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EXIT;
```

#### 1.2 配置数据库连接

有三种方式配置数据库连接：

**方式1：设置环境变量（推荐）**

Windows PowerShell:
```powershell
$env:DB_HOST="localhost"
$env:DB_PORT="3306"
$env:DB_NAME="autovideo"
$env:DB_USER="root"
$env:DB_PASSWORD="your_password"
$env:SECRET_KEY="your-secret-key"
```

Windows CMD:
```cmd
set DB_HOST=localhost
set DB_PORT=3306
set DB_NAME=autovideo
set DB_USER=root
set DB_PASSWORD=your_password
set SECRET_KEY=your-secret-key
```

Linux/Mac:
```bash
export DB_HOST=localhost
export DB_PORT=3306
export DB_NAME=autovideo
export DB_USER=root
export DB_PASSWORD=your_password
export SECRET_KEY=your-secret-key
```

**方式2：直接修改配置文件**

编辑 `center_code/backend/config.py`，修改 `MYSQL_CONFIG` 字典：
```python
MYSQL_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'database': 'autovideo',
    'user': 'root',
    'password': 'your_password',  # 修改这里
    'charset': 'utf8mb4'
}
```

**方式3：使用 .env 文件（需要安装 python-dotenv）**

复制 `backend/.env.example` 为 `backend/.env`，然后修改配置。

### 2. 后端设置

```bash
cd center_code/backend

# 安装依赖
pip install -r requirements.txt

# 运行后端（确保已配置数据库连接）
python app.py
```

**注意**：如果遇到数据库连接错误，请检查：
- MySQL 服务是否运行
- 数据库是否已创建
- 用户名和密码是否正确
- 数据库用户是否有足够权限

### 3. 前端设置

```bash
cd center_code/frontend

# 安装依赖
npm install

# 开发模式运行
npm run dev

# 构建生产版本
npm run build
```

## 环境变量配置

### 后端环境变量

在 `backend/config.py` 中配置，或使用环境变量：

- `DB_HOST`: 数据库主机地址（默认 `localhost`）
- `DB_PORT`: 数据库端口（默认 `3306`）
- `DB_NAME`: 数据库名称（默认 `autovideo`）
- `DB_USER`: 数据库用户名（默认 `root`）
- `DB_PASSWORD`: 数据库密码
- `SECRET_KEY`: Flask 会话密钥

### 前端环境变量

在 `frontend/.env.development` 和 `frontend/.env.production` 中配置：

- `VITE_API_BASE_URL`: API 基础地址（开发环境默认 `http://localhost:8080/api`）

## 后端模块化设计

后端采用模块化设计，使用 Flask Blueprint 将 API 按功能分块管理：

### 模块说明

1. **auth.py** - 认证模块
   - `/api/auth/login` - 用户登录
   - `/api/auth/logout` - 用户登出
   - `/api/auth/check` - 检查登录状态

2. **devices.py** - 设备管理模块
   - `/api/devices/register` - 设备注册
   - `/api/devices` - 获取设备列表
   - `/api/devices/<id>` - 获取设备详情
   - `/api/devices/<id>/heartbeat` - 设备心跳

3. **accounts.py** - 账号管理模块
   - `/api/accounts` - 创建/获取账号列表
   - `/api/accounts/<id>` - 获取/删除账号
   - `/api/accounts/<id>/status` - 更新账号状态
   - `/api/accounts/<id>/cookies` - 获取/更新 Cookies

4. **video.py** - 视频上传模块
   - `/api/video/upload` - 创建视频任务
   - `/api/video/tasks` - 获取任务列表
   - `/api/video/tasks/<id>` - 任务详情/删除
   - `/api/video/callback` - 任务回调
   - `/api/video/download/<filename>` - 下载视频文件

5. **chat.py** - 对话功能模块
   - `/api/chat/send` - 发送消息
   - `/api/chat/tasks` - 获取对话任务
   - `/api/chat/tasks/<id>` - 任务详情
   - `/api/chat/callback` - 对话回调

6. **listen.py** - 监听功能模块
   - `/api/listen/tasks` - 获取监听任务
   - `/api/listen/tasks/<id>` - 任务详情/删除
   - `/api/listen/callback` - 监听回调

7. **social.py** - 社交平台模块
   - `/api/social/upload` - 社交平台上传
   - `/api/social/listen/start` - 开始监听
   - `/api/social/listen/stop` - 停止监听
   - `/api/social/listen/messages` - 获取消息
   - `/api/social/chat/reply` - 回复消息

8. **messages.py** - 消息管理模块
   - `/api/messages` - 获取/创建消息
   - `/api/messages/<id>` - 删除消息
   - `/api/messages/clear` - 清空消息

9. **stats.py** - 统计模块
   - `/api/stats` - 获取统计信息

10. **login.py** - 登录相关模块
    - `/api/login/start` - 开始登录
    - `/api/login/qrcode` - 获取二维码

## 数据库迁移

### 从 SQLite 迁移到 MySQL

1. 导出 SQLite 数据（如果需要）
2. 创建 MySQL 数据库
3. 运行新的后端应用，会自动创建表结构
4. 如果需要迁移数据，可以使用数据迁移脚本

## 开发说明

### 前端开发

前端使用 Vite 作为构建工具，支持热重载。

```bash
cd frontend
npm run dev  # 开发服务器运行在 http://localhost:3001
```

### 后端开发

后端使用 Flask，支持调试模式。

```bash
cd backend
python app.py  # 默认运行在 http://localhost:8080
```

### API 调用示例

前端通过 `src/api/index.js` 统一管理 API 调用，使用 axios 发送请求。

## 注意事项

1. 确保数据库已创建并配置正确
2. 首次运行会自动创建数据库表
3. 生产环境请修改 `SECRET_KEY`
4. 前端构建后，静态文件会输出到 `backend/static` 目录
5. 后端需要配置 CORS 以支持前端跨域请求（已配置）

## 故障排查

### 数据库连接失败

- 检查数据库服务是否运行
- 检查数据库配置是否正确
- 检查数据库用户权限

### 前端无法连接后端

- 检查后端服务是否运行
- 检查 `VITE_API_BASE_URL` 配置
- 检查 CORS 配置

### 表结构创建失败

- 检查数据库用户是否有创建表的权限
- 检查数据库是否已存在同名表

