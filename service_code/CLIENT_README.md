# 客户端通信模块使用说明

## 概述

当 `social-auto-upload` 部署在用户电脑上时，由于用户电脑可能在NAT后面或没有公网IP，中心服务器无法直接访问。因此，我们采用**任务队列模式**，让客户端主动从中心服务器拉取任务。

## 架构说明

### 通信模式

```
┌─────────────────┐
│  中心服务器      │  (center/app.py)
│  (Center)       │  提供API，存储任务到数据库
└────────┬────────┘
         │
         │ HTTP (客户端主动连接)
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼───┐
│客户端1│ │客户端2│  (social-auto-upload/client)
│(用户PC)│ │(用户PC)│  定期拉取任务并执行
└───────┘ └──────┘
```

### 工作流程

1. **设备注册**：客户端启动时，自动注册设备到中心服务器
2. **心跳机制**：客户端每30秒发送一次心跳，保持在线状态
3. **任务轮询**：客户端每10秒轮询一次待处理任务
4. **任务执行**：获取到任务后，执行相应操作（上传视频/发送消息）
5. **结果上报**：执行完成后，上报结果到中心服务器

## 使用方法

### 1. 配置中心服务器地址

设置环境变量 `CENTER_BASE_URL`：

```bash
# Windows PowerShell
$env:CENTER_BASE_URL="http://your-server.com:8080"

# Linux/Mac
export CENTER_BASE_URL="http://your-server.com:8080"
```

或者在代码中直接修改 `client_main.py`：

```python
CENTER_BASE_URL = os.getenv('CENTER_BASE_URL', 'http://your-server.com:8080')
```

### 2. 启动客户端

运行客户端主程序：

```bash
cd social-auto-upload
python client_main.py
```

### 3. 设备管理

- 设备ID会自动生成并保存到 `.device_id` 文件
- 设备名称默认为主机名，可通过环境变量 `DEVICE_NAME` 设置
- 设备首次启动时会自动注册到中心服务器

## API说明

### 客户端功能

客户端模块 (`client/center_client.py`) 提供以下功能：

- `register_device()`: 注册设备
- `send_heartbeat()`: 发送心跳
- `get_pending_tasks()`: 获取待处理的视频任务
- `get_pending_chat_tasks()`: 获取待处理的对话任务
- `update_task_status()`: 更新任务状态
- `get_account_info()`: 获取账号信息（包括cookies）
- `update_account_cookies()`: 更新账号cookies

### 任务处理

任务处理器 (`client/task_handler.py`) 自动处理：

- **视频上传任务**：下载视频文件，使用账号cookies上传到抖音
- **对话任务**：使用账号cookies发送消息

## 任务创建

在中心服务器上创建任务时，需要指定 `device_id`（设备的字符串ID，不是数据库ID）。

### 通过API创建任务

```python
# 创建视频上传任务
POST /api/video/upload
{
    "account_id": 1,
    "device_id": "device_abc123",  # 设备的字符串ID
    "video_url": "http://example.com/video.mp4",
    "video_title": "测试视频",
    "video_tags": "标签1,标签2",
    "publish_date": "2024-01-01T10:00:00"
}

# 创建对话任务
POST /api/chat/send
{
    "account_id": 1,
    "device_id": "device_abc123",  # 设备的字符串ID
    "target_user": "用户名",
    "message": "消息内容"
}
```

## 注意事项

1. **网络连接**：客户端需要能够访问中心服务器的HTTP API
2. **防火墙**：确保客户端可以访问中心服务器的端口（默认8080）
3. **设备ID**：每个客户端有唯一的设备ID，保存在 `.device_id` 文件中
4. **任务分配**：任务通过 `device_id` 分配给特定设备
5. **并发处理**：客户端会顺序处理任务，避免并发冲突

## 故障排查

### 客户端无法连接中心服务器

1. 检查 `CENTER_BASE_URL` 环境变量是否正确
2. 检查网络连接，确保可以访问中心服务器
3. 检查中心服务器是否正常运行

### 设备注册失败

1. 检查中心服务器API是否正常
2. 检查设备ID是否冲突（删除 `.device_id` 文件重新生成）

### 任务无法执行

1. 检查账号是否有有效的cookies
2. 检查任务参数是否正确
3. 查看日志文件了解详细错误信息

## 与旧版本的兼容性

- 旧的直接HTTP调用方式仍然保留（`app.py` 中的 `/api/upload/video` 等接口）
- 新的任务队列模式是可选功能，可以同时使用
- 如果客户端未运行，中心服务器仍可以通过HTTP直接调用（如果网络可达）

