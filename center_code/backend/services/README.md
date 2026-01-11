# 后端服务模块说明

## 概述

本模块将 `service_code` 中的所有功能整合到 `center_code/backend` 中，所有处理都在后端进行，包括：

- 视频上传任务执行
- 消息监听任务执行
- 消息回复任务执行

所有数据（设备ID、账号cookies等）都从数据库获取，不再依赖文件系统。

## 模块结构

- `config.py`: 服务配置（Chrome路径、headless模式等）
- `task_executor.py`: 任务执行器，包含所有任务的具体执行逻辑
- `task_processor.py`: 后台任务处理器，定期检查并执行待处理的任务

## 工作流程

1. **任务创建**: 通过API创建任务（视频上传、监听、回复等），任务状态为 `pending`
2. **任务处理**: 后台任务处理器定期检查 `pending` 状态的任务，并启动执行
3. **任务执行**: 任务执行器从数据库获取账号信息（包括cookies），执行相应操作
4. **状态更新**: 任务执行完成后，更新任务状态为 `completed` 或 `failed`

## 依赖关系

本模块依赖 `service_code` 中的以下模块：

- `uploader/douyin_uploader/main.py`: 视频上传器
- `listener/douyin_listener/main.py`: 消息监听器
- `utils/base_social_media.py`: 基础社交媒体工具
- `utils/log.py`: 日志工具

确保 `service_code` 目录在项目根目录下，且包含上述模块。

## 配置

通过环境变量配置：

- `LOCAL_CHROME_PATH`: Chrome浏览器路径（默认: `C:\Program Files\Google\Chrome\Application\chrome.exe`）
- `LOCAL_CHROME_HEADLESS`: 是否使用headless模式（默认: `False`）

## 注意事项

1. 所有cookies都存储在数据库中，不再使用文件系统
2. 任务执行是异步的，在后台线程中执行
3. 监听任务会保持浏览器打开，直到任务被停止
4. 确保数据库连接正常，所有账号信息都能从数据库获取

