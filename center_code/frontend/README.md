# 前端开发说明

## 启动开发服务器

```bash
npm install
npm run dev
```

## 配置后端API地址

前端默认连接到 `http://localhost:5000`（后端默认端口）。如果后端运行在其他端口，可以通过以下方式配置：

### 方式1：使用环境变量（推荐）

创建 `.env` 或 `.env.local` 文件：

```env
# 只配置端口号
VITE_BACKEND_PORT=5001

# 或配置完整URL
VITE_BACKEND_URL=http://localhost:5001
```

**Windows PowerShell:**
```powershell
$env:VITE_BACKEND_PORT="5001"
npm run dev
```

**Linux/Mac:**
```bash
export VITE_BACKEND_PORT=5001
npm run dev
```

### 方式2：直接修改 vite.config.js

如果不想使用环境变量，可以直接编辑 `vite.config.js` 中的 `backendUrl` 变量。

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

