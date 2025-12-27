# 迁移说明

## 概述

已将 `service_code` 中的所有功能迁移到 `center_code/backend` 中，现在系统只需要启动前后端即可运行，不再需要 `service_code` 目录。

## 迁移内容

### 1. 模块迁移
- ✅ `uploader/` - 视频上传模块
- ✅ `listener/` - 消息监听模块
- ✅ `utils/` - 工具模块（日志、反检测脚本等）

### 2. 配置文件
- ✅ `conf.py` - 统一配置文件（Chrome路径、headless模式等）
- ✅ `requirements.txt` - 合并了所有依赖

### 3. 服务模块
- ✅ `services/task_executor.py` - 任务执行器（已更新导入路径）
- ✅ `services/task_processor.py` - 后台任务处理器
- ✅ `services/config.py` - 服务配置（使用conf.py）

## 目录结构

```
center_code/backend/
├── uploader/              # 视频上传模块（从service_code迁移）
│   └── douyin_uploader/
├── listener/              # 消息监听模块（从service_code迁移）
│   └── douyin_listener/
├── utils/                  # 工具模块（从service_code迁移）
│   ├── base_social_media.py
│   ├── log.py
│   ├── files_times.py
│   ├── douyin_stealth.js
│   └── stealth.min.js
├── services/              # 后端服务模块
│   ├── task_executor.py   # 任务执行器
│   ├── task_processor.py  # 任务处理器
│   └── config.py          # 服务配置
├── conf.py                # 统一配置文件
├── logs/                  # 日志目录（自动创建）
└── requirements.txt        # 依赖列表（已合并）
```

## 导入路径更新

所有模块现在都从 `center_code/backend` 导入：

- `from conf import ...` - 从backend目录的conf.py导入
- `from utils.xxx import ...` - 从backend/utils导入
- `from uploader.douyin_uploader.main import ...` - 从backend/uploader导入
- `from listener.douyin_listener.main import ...` - 从backend/listener导入

## 配置说明

### 环境变量
- `LOCAL_CHROME_PATH`: Chrome浏览器路径（默认: `C:\Program Files\Google\Chrome\Application\chrome.exe`）
- `LOCAL_CHROME_HEADLESS`: 是否使用headless模式（默认: `False`）

### 配置文件
所有配置统一在 `conf.py` 中管理，支持环境变量覆盖。

## 使用说明

1. **安装依赖**
   ```bash
   cd center_code/backend
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **启动后端**
   ```bash
   python app.py
   ```

3. **启动前端**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## 注意事项

1. ✅ 所有cookies存储在数据库中，不再使用文件系统
2. ✅ 所有任务在后端自动处理，不需要单独的service_code服务
3. ✅ 日志文件保存在 `backend/logs/` 目录
4. ✅ 确保Chrome浏览器已安装且路径正确

## 不再需要的文件/目录

以下内容已不再需要，可以删除：
- `service_code/` 目录（所有功能已迁移）
- `service_code/client_main.py`（任务处理已整合到后端）
- `service_code/app.py`（功能已整合到后端）

现在系统只需要 `center_code` 目录即可完整运行！

