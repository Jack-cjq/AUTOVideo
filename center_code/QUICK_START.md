# 快速启动指南

## 问题排查：前端404错误

如果遇到 `GET http://localhost:3001/api/auth/check 404 (Not Found)` 错误，请按以下步骤排查：

### 1. 确认后端是否运行

**检查后端端口：**
```powershell
# Windows PowerShell
netstat -ano | findstr "LISTENING" | findstr ":5000 :5001 :8080"
```

**启动后端：**
```bash
cd center_code/backend
python app.py
```

后端启动后会显示：
```
✓ 数据库连接成功
✓ 数据库表初始化成功
正在启动服务器...
访问地址: http://localhost:5000  (或自动切换的其他端口)
```

**注意后端实际运行的端口！**

### 2. 更新前端代理配置

编辑 `center_code/frontend/vite.config.js`，修改 `target` 为后端实际运行的端口：

```javascript
proxy: {
  '/api': {
    target: 'http://localhost:5001',  // 修改为后端实际端口
    changeOrigin: true,
    secure: false
  }
}
```

### 3. 重启前端开发服务器

修改配置后，**必须重启前端开发服务器**：

```bash
# 停止当前服务器（Ctrl+C）
# 然后重新启动
cd center_code/frontend
npm run dev
```

### 4. 验证连接

打开浏览器控制台，检查：
- 网络请求是否发送到正确的后端地址
- 是否有CORS错误
- 后端是否返回正确的响应

## 常见端口配置

- **前端开发服务器**: 3000（如果被占用会自动切换到3001）
- **后端服务器**: 5000（如果被占用会自动切换到5001-5009）

## 快速测试

1. **测试后端API**：
   ```bash
   curl http://localhost:5001/api/health
   ```
   应该返回：`{"status":"healthy","database":"mysql",...}`

2. **测试前端代理**：
   在浏览器访问：`http://localhost:3001/api/health`
   应该返回相同的JSON响应

## 如果仍然无法连接

1. 检查防火墙设置
2. 确认后端CORS配置正确
3. 查看浏览器控制台的完整错误信息
4. 查看后端控制台的请求日志

