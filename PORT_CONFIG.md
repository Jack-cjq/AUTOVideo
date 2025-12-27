# 端口配置说明

## 默认端口配置

系统已统一更新端口配置，避免与常见服务冲突：

### 后端服务器（Center Code）
- **默认端口**: `8080`
- **备用端口**: `8081-8089`（如果8080被占用，自动尝试）
- **配置文件**: `center_code/backend/app.py`
- **环境变量**: `PORT=8080`

### 前端开发服务器（Frontend）
- **默认端口**: `3001`
- **代理目标**: `http://localhost:8080`（后端地址）
- **配置文件**: `center_code/frontend/vite.config.js`
- **环境变量**: `VITE_BACKEND_PORT=8080` 或 `VITE_BACKEND_URL=http://localhost:8080`

### Service_Code 服务器
- **默认端口**: `8081`
- **配置文件**: `service_code/app.py`
- **环境变量**: `PORT=8081`

### Service_Code 客户端
- **检测端口**: `8080, 8081, 8082`（自动检测中心服务器）
- **默认连接**: `http://127.0.0.1:8080`
- **配置文件**: `service_code/client_main.py`
- **环境变量**: `CENTER_BASE_URL=http://127.0.0.1:8080`

## 启动方式

### 后端服务器
```bash
cd center_code/backend
python app.py
# 或指定端口
python app.py 8080
# 或使用环境变量
$env:PORT=8080  # Windows PowerShell
export PORT=8080  # Linux/Mac
python app.py
```

### 前端开发服务器
```bash
cd center_code/frontend
npm run dev
# 访问地址: http://localhost:3001
```

### Service_Code 服务器
```bash
cd service_code
python app.py
# 或指定端口
$env:PORT=8081  # Windows PowerShell
export PORT=8081  # Linux/Mac
python app.py
```

### Service_Code 客户端
```bash
cd service_code
python client_main.py
# 或指定中心服务器地址
$env:CENTER_BASE_URL="http://127.0.0.1:8080"  # Windows PowerShell
export CENTER_BASE_URL="http://127.0.0.1:8080"  # Linux/Mac
python client_main.py
```

## 端口冲突处理

### 后端服务器
如果默认端口8080被占用，会自动尝试8081-8089端口。

### 前端开发服务器
如果默认端口3001被占用，Vite会自动尝试下一个可用端口（3002, 3003...）。

### 手动指定端口
所有服务都支持通过环境变量或命令行参数指定端口。

## 注意事项

1. **防火墙**: 确保相关端口未被防火墙阻止
2. **CORS配置**: 后端已配置允许前端端口（3001, 3002, 5173）
3. **代理配置**: 前端代理会自动转发到后端8080端口
4. **Service_Code连接**: 确保Service_Code客户端能访问后端8080端口

## 端口映射总结

| 服务 | 默认端口 | 备用端口 | 说明 |
|------|---------|---------|------|
| 后端服务器 | 8080 | 8081-8089 | Center Code 后端 |
| 前端开发服务器 | 3001 | 3002+ | Vite 开发服务器 |
| Service_Code 服务器 | 8081 | - | Service Code 后端 |
| Service_Code 客户端 | - | - | 连接后端8080端口 |

