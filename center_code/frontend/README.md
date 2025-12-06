# 前端开发说明

## 启动开发服务器

```bash
npm install
npm run dev
```

## 配置后端API地址

### 方式1：修改 vite.config.js（推荐）

编辑 `vite.config.js`，修改代理配置中的 `target`：

```javascript
proxy: {
  '/api': {
    target: 'http://localhost:5001',  // 修改为你的后端实际端口
    ...
  }
}
```

### 方式2：使用环境变量

创建 `.env.development` 文件（已创建示例）：

```env
VITE_API_BASE_URL=http://localhost:5001/api
```

然后修改 `vite.config.js`：

```javascript
proxy: {
  '/api': {
    target: process.env.VITE_API_BASE_URL?.replace('/api', '') || 'http://localhost:5001',
    ...
  }
}
```

## 常见问题

### 1. 404错误 - Cannot GET /api/xxx

**原因**：后端未运行或端口不匹配

**解决**：
- 确认后端已启动
- 检查后端运行端口
- 更新 `vite.config.js` 中的 `target` 为正确的后端地址

### 2. 端口被占用

如果3000端口被占用，Vite会自动使用下一个可用端口（如3001），这是正常的。

### 3. CORS错误

确保后端已配置CORS，并且 `vite.config.js` 中的代理配置正确。

