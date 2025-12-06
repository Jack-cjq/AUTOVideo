# 视频矩阵管理平台 - 项目说明文档

## 一、项目概述

本项目是一个视频矩阵管理平台，用于管理多个社交媒体账号的视频发布、消息监听、对话回复等功能。系统采用前后端分离架构，前端使用 Vue 3 + Element Plus，后端使用 Flask + MySQL。

## 二、技术栈

### 后端技术栈
- **框架**: Flask (Python Web 框架)
- **数据库**: MySQL
- **ORM**: SQLAlchemy
- **认证**: Session-based 认证
- **CORS**: flask-cors (跨域支持)

### 前端技术栈
- **框架**: Vue 3 (Composition API)
- **UI 组件库**: Element Plus
- **状态管理**: Pinia
- **路由**: Vue Router
- **构建工具**: Vite
- **HTTP 客户端**: Axios

## 三、项目结构

```
center_code/
├── backend/                 # 后端代码
│   ├── app.py              # Flask 应用主文件
│   ├── config.py           # 配置文件
│   ├── db.py               # 数据库连接管理
│   ├── models.py           # 数据模型定义
│   ├── utils.py            # 工具函数
│   ├── init_database.py    # 数据库初始化脚本
│   ├── init_user.py        # 默认用户创建脚本
│   ├── test_db.py          # 数据库测试脚本
│   ├── requirements.txt     # Python 依赖
│   └── blueprints/         # API 路由模块
│       ├── auth.py         # 认证相关 API
│       ├── devices.py      # 设备管理 API
│       ├── accounts.py     # 账号管理 API
│       ├── video.py        # 视频任务 API
│       ├── chat.py         # 对话任务 API
│       ├── listen.py       # 监听任务 API
│       ├── social.py       # 社交功能 API
│       ├── messages.py     # 消息管理 API
│       ├── stats.py        # 统计信息 API
│       ├── login.py        # 登录流程 API
│       ├── publish_plans.py # 发布计划 API
│       ├── merchants.py    # 商家管理 API
│       ├── video_library.py # 视频库 API
│       ├── data_center.py  # 数据中心 API
│       └── video_editor.py  # AI视频剪辑 API
│
├── frontend/               # 前端代码
│   ├── src/
│   │   ├── main.js        # 应用入口
│   │   ├── App.vue        # 根组件
│   │   ├── api/           # API 调用封装
│   │   │   ├── index.js   # API 主文件
│   │   │   ├── publishPlans.js
│   │   │   ├── merchants.js
│   │   │   ├── videoLibrary.js
│   │   │   ├── dataCenter.js
│   │   │   └── videoEditor.js
│   │   ├── components/    # 组件
│   │   │   ├── layout/    # 布局组件
│   │   │   │   ├── TopNavbar.vue
│   │   │   │   └── SideNavbar.vue
│   │   │   ├── LoginDialog.vue
│   │   │   ├── AccountModal.vue
│   │   │   ├── DeviceModal.vue
│   │   │   ├── VideoModal.vue
│   │   │   └── MessageModal.vue
│   │   ├── layouts/       # 布局
│   │   │   └── MainLayout.vue
│   │   ├── views/         # 页面视图
│   │   │   ├── Dashboard.vue
│   │   │   ├── Publish.vue
│   │   │   ├── PublishPlan.vue
│   │   │   ├── Accounts.vue
│   │   │   ├── DataCenter.vue
│   │   │   ├── Merchants.vue
│   │   │   ├── VideoLibrary.vue
│   │   │   └── VideoEditor.vue
│   │   ├── router/        # 路由配置
│   │   │   └── index.js
│   │   └── stores/        # 状态管理
│   │       ├── auth.js
│   │       └── stats.js
│   ├── vite.config.js     # Vite 配置
│   └── package.json       # 前端依赖
│
└── uploads/               # 上传文件目录
```

## 四、后端框架结构

### 4.1 核心文件说明

#### `backend/app.py`
- **功能**: Flask 应用主文件
- **职责**:
  - 初始化 Flask 应用
  - 配置 CORS 和 Session
  - 注册所有 Blueprint 路由
  - 提供静态文件服务（前端构建产物）
  - 自动端口检测和重试（5000-5009）

#### `backend/config.py`
- **功能**: 数据库配置
- **职责**:
  - 从环境变量读取数据库配置
  - 支持 MySQL 数据库连接
  - 提供数据库连接字符串

#### `backend/db.py`
- **功能**: 数据库连接管理
- **职责**:
  - 创建 SQLAlchemy Engine
  - 提供数据库会话管理（get_db）
  - 管理数据库连接池

#### `backend/models.py`
- **功能**: 数据模型定义
- **职责**:
  - 定义所有数据库表的 ORM 模型
  - 包含以下模型：
    - `User`: 用户表
    - `Device`: 设备表
    - `Account`: 账号表
    - `VideoTask`: 视频任务表
    - `ChatTask`: 对话任务表
    - `ListenTask`: 监听任务表
    - `Message`: 消息表
    - `PublishPlan`: 发布计划表
    - `PlanVideo`: 计划视频表
    - `Merchant`: 商家表
    - `VideoLibrary`: 视频库表
    - `AccountStats`: 账号统计表

#### `backend/utils.py`
- **功能**: 工具函数
- **职责**:
  - `response_success()`: 成功响应格式化
  - `response_error()`: 错误响应格式化
  - `login_required`: 登录验证装饰器

#### `backend/init_database.py`
- **功能**: 数据库初始化脚本
- **职责**:
  - 自动创建数据库（如果不存在）
  - 创建所有数据表
  - 创建默认用户

#### `backend/init_user.py`
- **功能**: 默认用户创建脚本
- **职责**:
  - 创建默认管理员账号（hbut/dydy?123）
  - 如果用户已存在则跳过

### 4.2 Blueprint 模块说明

#### `blueprints/auth.py` - 认证模块
- **功能**: 用户登录、登出、登录状态检查
- **接口**:
  - `POST /api/auth/login` - 用户登录 ✅
  - `POST /api/auth/logout` - 用户登出 ✅
  - `GET /api/auth/check` - 检查登录状态 ✅

#### `blueprints/devices.py` - 设备管理模块
- **功能**: 设备注册、查询、心跳
- **接口**:
  - `POST /api/devices/register` - 设备注册 ✅
  - `GET /api/devices` - 获取设备列表 ✅
  - `GET /api/devices/{device_id}` - 获取设备详情 ✅
  - `POST /api/devices/{device_id}/heartbeat` - 设备心跳 ✅

#### `blueprints/accounts.py` - 账号管理模块
- **功能**: 账号创建、查询、更新、删除、Cookies 管理
- **接口**:
  - `POST /api/accounts` - 创建账号 ✅
  - `GET /api/accounts` - 获取账号列表 ✅
  - `GET /api/accounts/{account_id}` - 获取账号详情 ✅
  - `PUT /api/accounts/{account_id}/status` - 更新账号状态 ✅
  - `DELETE /api/accounts/{account_id}` - 删除账号 ✅
  - `GET /api/accounts/{account_id}/cookies` - 获取 Cookies ✅
  - `PUT /api/accounts/{account_id}/cookies` - 更新 Cookies ✅
  - `GET /api/accounts/{account_id}/cookies/file` - 获取 Cookies 文件 ✅

#### `blueprints/video.py` - 视频任务模块
- **功能**: 视频上传任务创建、查询、删除、回调
- **接口**:
  - `POST /api/video/upload` - 创建视频上传任务 ✅
  - `GET /api/video/tasks` - 获取视频任务列表 ✅
  - `GET /api/video/tasks/{task_id}` - 获取任务详情 ✅
  - `DELETE /api/video/tasks/{task_id}` - 删除任务 ✅
  - `POST /api/video/callback` - 视频上传回调 ✅
  - `GET /api/video/download/{filename}` - 下载视频文件 ✅

#### `blueprints/chat.py` - 对话任务模块
- **功能**: 对话发送任务创建、查询、回调
- **接口**:
  - `POST /api/chat/send` - 创建对话发送任务 ✅
  - `GET /api/chat/tasks` - 获取对话任务列表 ✅
  - `GET /api/chat/tasks/{task_id}` - 获取任务详情 ✅
  - `POST /api/chat/callback` - 对话任务回调 ✅

#### `blueprints/listen.py` - 监听任务模块
- **功能**: 消息监听任务查询、删除、回调
- **接口**:
  - `GET /api/listen/tasks` - 获取监听任务列表 ✅
  - `GET /api/listen/tasks/{task_id}` - 获取任务详情 ✅
  - `DELETE /api/listen/tasks/{task_id}` - 删除任务 ✅
  - `POST /api/listen/callback` - 监听任务回调 ✅

#### `blueprints/social.py` - 社交功能模块
- **功能**: 视频上传、消息监听、消息回复
- **接口**:
  - `POST /api/social/upload` - 上传视频 ✅
  - `POST /api/social/listen/start` - 启动消息监听 ✅
  - `POST /api/social/listen/stop` - 停止消息监听 ✅
  - `GET /api/social/listen/messages` - 获取监听到的消息 ✅
  - `POST /api/social/chat/reply` - 回复消息 ✅

#### `blueprints/messages.py` - 消息管理模块
- **功能**: 消息查询、创建、删除、清空
- **接口**:
  - `GET /api/messages` - 获取消息列表 ✅
  - `POST /api/messages` - 创建消息 ✅
  - `DELETE /api/messages/{message_id}` - 删除消息 ✅
  - `POST /api/messages/clear` - 清空消息 ✅

#### `blueprints/stats.py` - 统计信息模块
- **功能**: 系统统计信息
- **接口**:
  - `GET /api/stats` - 获取统计信息 ✅

#### `blueprints/login.py` - 登录流程模块
- **功能**: 账号登录流程管理
- **接口**:
  - `POST /api/login/start` - 启动登录流程 ✅
  - `GET /api/login/qrcode` - 获取登录二维码 ⚠️ (占位接口)

#### `blueprints/publish_plans.py` - 发布计划模块
- **功能**: 发布计划管理、视频添加
- **接口**:
  - `GET /api/publish-plans` - 获取发布计划列表 ✅
  - `POST /api/publish-plans` - 创建发布计划 ✅
  - `GET /api/publish-plans/{plan_id}` - 获取计划详情 ✅
  - `PUT /api/publish-plans/{plan_id}` - 更新发布计划 ✅
  - `DELETE /api/publish-plans/{plan_id}` - 删除发布计划 ✅
  - `POST /api/publish-plans/{plan_id}/videos` - 向计划添加视频 ✅
  - `POST /api/publish-plans/{plan_id}/save-info` - 保存发布信息 ⚠️ (占位接口)
  - `POST /api/publish-plans/{plan_id}/distribute` - 分发发布计划 ⚠️ (占位接口)
  - `POST /api/publish-plans/{plan_id}/claim` - 领取计划视频 ⚠️ (占位接口)

#### `blueprints/merchants.py` - 商家管理模块
- **功能**: 商家信息管理
- **接口**:
  - `GET /api/merchants` - 获取商家列表 ✅
  - `POST /api/merchants` - 创建商家 ✅
  - `GET /api/merchants/{merchant_id}` - 获取商家详情 ✅
  - `PUT /api/merchants/{merchant_id}` - 更新商家信息 ✅
  - `DELETE /api/merchants/{merchant_id}` - 删除商家 ✅

#### `blueprints/video_library.py` - 视频库模块
- **功能**: 云视频库管理
- **接口**:
  - `GET /api/video-library` - 获取视频列表 ✅
  - `POST /api/video-library` - 上传视频 ✅
  - `GET /api/video-library/{video_id}` - 获取视频详情 ✅
  - `PUT /api/video-library/{video_id}` - 更新视频信息 ✅
  - `DELETE /api/video-library/{video_id}` - 删除视频 ✅

#### `blueprints/data_center.py` - 数据中心模块
- **功能**: 数据统计和分析
- **接口**:
  - `GET /api/data-center/video-stats` - 获取视频数据统计 ✅
  - `GET /api/data-center/account-stats` - 获取账号统计数据 ✅
  - `POST /api/data-center/account-stats` - 创建账号统计数据 ⚠️ (占位接口)

#### `blueprints/video_editor.py` - AI视频剪辑模块
- **功能**: AI视频剪辑项目管理、视频上传、剪辑任务管理、AI功能
- **接口**: 所有接口均为占位接口 ⚠️
  - `GET /api/video-editor/projects` - 获取项目列表 ⚠️
  - `GET /api/video-editor/projects/{id}` - 获取项目详情 ⚠️
  - `POST /api/video-editor/projects` - 创建项目 ⚠️
  - `PUT /api/video-editor/projects/{id}` - 更新项目 ⚠️
  - `DELETE /api/video-editor/projects/{id}` - 删除项目 ⚠️
  - `POST /api/video-editor/upload` - 上传视频 ⚠️
  - `POST /api/video-editor/projects/{id}/start-edit` - 开始剪辑 ⚠️
  - `POST /api/video-editor/projects/{id}/export` - 导出视频 ⚠️
  - `GET /api/video-editor/tasks/{id}` - 获取任务状态 ⚠️
  - `POST /api/video-editor/tasks/{id}/cancel` - 取消任务 ⚠️
  - `DELETE /api/video-editor/projects/{id}/videos/{video_id}` - 删除项目视频 ⚠️
  - `POST /api/video-editor/ai/cut` - AI智能裁剪 ⚠️
  - `POST /api/video-editor/ai/subtitle` - AI生成字幕 ⚠️
  - `POST /api/video-editor/ai/filter` - AI滤镜美化 ⚠️
  - `POST /api/video-editor/ai/music` - AI配乐推荐 ⚠️

## 五、前端框架结构

### 5.1 核心文件说明

#### `frontend/src/main.js`
- **功能**: 应用入口文件
- **职责**:
  - 初始化 Vue 应用
  - 注册 Pinia 状态管理
  - 注册 Vue Router
  - 注册 Element Plus 组件库
  - 注册 Element Plus 图标

#### `frontend/src/App.vue`
- **功能**: 根组件
- **职责**:
  - 应用初始化
  - 登录状态检查
  - 路由视图渲染

#### `frontend/src/router/index.js`
- **功能**: 路由配置
- **职责**:
  - 定义所有路由
  - 路由守卫（登录验证）
  - 路由懒加载

#### `frontend/vite.config.js`
- **功能**: Vite 构建配置
- **职责**:
  - 配置开发服务器
  - 配置 API 代理
  - 配置构建输出目录

### 5.2 API 调用封装

#### `frontend/src/api/index.js`
- **功能**: API 调用主文件
- **职责**:
  - 创建 Axios 实例
  - 配置请求/响应拦截器
  - 统一错误处理
  - 定义所有 API 方法

#### `frontend/src/api/publishPlans.js`
- **功能**: 发布计划 API 封装

#### `frontend/src/api/merchants.js`
- **功能**: 商家管理 API 封装

#### `frontend/src/api/videoLibrary.js`
- **功能**: 视频库 API 封装

#### `frontend/src/api/dataCenter.js`
- **功能**: 数据中心 API 封装

#### `frontend/src/api/videoEditor.js`
- **功能**: AI视频剪辑 API 封装

### 5.3 状态管理

#### `frontend/src/stores/auth.js`
- **功能**: 认证状态管理
- **状态**:
  - `isLoggedIn`: 是否已登录
  - `username`: 用户名
  - `showLoginDialog`: 是否显示登录对话框
- **方法**:
  - `checkLogin()`: 检查登录状态
  - `login()`: 用户登录
  - `logout()`: 用户登出

#### `frontend/src/stores/stats.js`
- **功能**: 统计信息状态管理

### 5.4 组件说明

#### 布局组件
- **`components/layout/TopNavbar.vue`**: 顶部导航栏
- **`components/layout/SideNavbar.vue`**: 侧边导航栏
- **`layouts/MainLayout.vue`**: 主布局容器

#### 功能组件
- **`components/LoginDialog.vue`**: 登录对话框
- **`components/AccountModal.vue`**: 账号管理弹窗
- **`components/DeviceModal.vue`**: 设备管理弹窗
- **`components/VideoModal.vue`**: 视频管理弹窗
- **`components/MessageModal.vue`**: 消息管理弹窗

### 5.5 页面视图

- **`views/Dashboard.vue`**: 首页仪表盘
- **`views/Publish.vue`**: 立即发布页面
- **`views/PublishPlan.vue`**: 发布计划页面
- **`views/Accounts.vue`**: 授权管理页面
- **`views/DataCenter.vue`**: 数据中心页面
- **`views/Merchants.vue`**: 商家管理页面
- **`views/VideoLibrary.vue`**: 云视频库页面
- **`views/VideoEditor.vue`**: AI视频剪辑页面

## 六、已实现的接口列表

### 6.1 认证相关 (3个)
- ✅ `POST /api/auth/login` - 用户登录
- ✅ `POST /api/auth/logout` - 用户登出
- ✅ `GET /api/auth/check` - 检查登录状态

### 6.2 设备管理 (4个)
- ✅ `POST /api/devices/register` - 设备注册
- ✅ `GET /api/devices` - 获取设备列表
- ✅ `GET /api/devices/{device_id}` - 获取设备详情
- ✅ `POST /api/devices/{device_id}/heartbeat` - 设备心跳

### 6.3 账号管理 (8个)
- ✅ `POST /api/accounts` - 创建账号
- ✅ `GET /api/accounts` - 获取账号列表
- ✅ `GET /api/accounts/{account_id}` - 获取账号详情
- ✅ `PUT /api/accounts/{account_id}/status` - 更新账号状态
- ✅ `DELETE /api/accounts/{account_id}` - 删除账号
- ✅ `GET /api/accounts/{account_id}/cookies` - 获取 Cookies
- ✅ `PUT /api/accounts/{account_id}/cookies` - 更新 Cookies
- ✅ `GET /api/accounts/{account_id}/cookies/file` - 获取 Cookies 文件

### 6.4 视频任务 (6个)
- ✅ `POST /api/video/upload` - 创建视频上传任务
- ✅ `GET /api/video/tasks` - 获取视频任务列表
- ✅ `GET /api/video/tasks/{task_id}` - 获取任务详情
- ✅ `DELETE /api/video/tasks/{task_id}` - 删除任务
- ✅ `POST /api/video/callback` - 视频上传回调
- ✅ `GET /api/video/download/{filename}` - 下载视频文件

### 6.5 对话任务 (4个)
- ✅ `POST /api/chat/send` - 创建对话发送任务
- ✅ `GET /api/chat/tasks` - 获取对话任务列表
- ✅ `GET /api/chat/tasks/{task_id}` - 获取任务详情
- ✅ `POST /api/chat/callback` - 对话任务回调

### 6.6 监听任务 (4个)
- ✅ `GET /api/listen/tasks` - 获取监听任务列表
- ✅ `GET /api/listen/tasks/{task_id}` - 获取任务详情
- ✅ `DELETE /api/listen/tasks/{task_id}` - 删除任务
- ✅ `POST /api/listen/callback` - 监听任务回调

### 6.7 社交功能 (5个)
- ✅ `POST /api/social/upload` - 上传视频
- ✅ `POST /api/social/listen/start` - 启动消息监听
- ✅ `POST /api/social/listen/stop` - 停止消息监听
- ✅ `GET /api/social/listen/messages` - 获取监听到的消息
- ✅ `POST /api/social/chat/reply` - 回复消息

### 6.8 消息管理 (4个)
- ✅ `GET /api/messages` - 获取消息列表
- ✅ `POST /api/messages` - 创建消息
- ✅ `DELETE /api/messages/{message_id}` - 删除消息
- ✅ `POST /api/messages/clear` - 清空消息

### 6.9 统计信息 (1个)
- ✅ `GET /api/stats` - 获取统计信息

### 6.10 登录流程 (1个)
- ✅ `POST /api/login/start` - 启动登录流程

### 6.11 发布计划 (6个)
- ✅ `GET /api/publish-plans` - 获取发布计划列表
- ✅ `POST /api/publish-plans` - 创建发布计划
- ✅ `GET /api/publish-plans/{plan_id}` - 获取计划详情
- ✅ `PUT /api/publish-plans/{plan_id}` - 更新发布计划
- ✅ `DELETE /api/publish-plans/{plan_id}` - 删除发布计划
- ✅ `POST /api/publish-plans/{plan_id}/videos` - 向计划添加视频

### 6.12 商家管理 (5个)
- ✅ `GET /api/merchants` - 获取商家列表
- ✅ `POST /api/merchants` - 创建商家
- ✅ `GET /api/merchants/{merchant_id}` - 获取商家详情
- ✅ `PUT /api/merchants/{merchant_id}` - 更新商家信息
- ✅ `DELETE /api/merchants/{merchant_id}` - 删除商家

### 6.13 视频库 (5个)
- ✅ `GET /api/video-library` - 获取视频列表
- ✅ `POST /api/video-library` - 上传视频
- ✅ `GET /api/video-library/{video_id}` - 获取视频详情
- ✅ `PUT /api/video-library/{video_id}` - 更新视频信息
- ✅ `DELETE /api/video-library/{video_id}` - 删除视频

### 6.14 数据中心 (2个)
- ✅ `GET /api/data-center/video-stats` - 获取视频数据统计
- ✅ `GET /api/data-center/account-stats` - 获取账号统计数据

**总计已实现接口: 58个**

## 七、预留接口列表（占位接口）

### 7.1 登录流程 (1个)
- ⚠️ `GET /api/login/qrcode` - 获取登录二维码
  - **功能**: 使用 Playwright 获取平台登录二维码
  - **状态**: 占位接口，返回 501 错误
  - **说明**: 建议使用登录助手页面完成账号登录

### 7.2 发布计划 (3个)
- ⚠️ `POST /api/publish-plans/{plan_id}/save-info` - 保存发布信息
  - **功能**: 保存发布计划的详细信息（分发规则、账号分配等）
  - **状态**: 占位接口，仅返回成功响应
  - **说明**: 需要实现分发规则、账号分配、发布计划配置的保存逻辑

- ⚠️ `POST /api/publish-plans/{plan_id}/distribute` - 分发发布计划
  - **功能**: 根据分发模式（manual/sms/qrcode/ai）将视频分发给账号
  - **状态**: 占位接口，仅返回成功响应
  - **说明**: 需要实现四种分发模式的逻辑：
    - manual: 手动指定账号列表
    - sms: 通过短信接收任务分配
    - qrcode: 通过扫描二维码领取任务
    - ai: AI智能分配任务给合适的账号

- ⚠️ `POST /api/publish-plans/{plan_id}/claim` - 领取发布计划中的视频
  - **功能**: 账号领取发布计划中的视频任务（适用于二维码分发模式）
  - **状态**: 占位接口，仅返回成功响应
  - **说明**: 需要实现视频任务分配和 claimed_count 更新逻辑

### 7.3 数据中心 (1个)
- ⚠️ `POST /api/data-center/account-stats` - 创建账号统计数据
  - **功能**: 由定时任务调用，定期更新账号统计数据
  - **状态**: 占位接口，仅返回成功响应
  - **说明**: 需要实现从平台API获取统计数据并保存到数据库的逻辑

### 7.4 AI视频剪辑 (15个)
- ⚠️ `GET /api/video-editor/projects` - 获取项目列表
  - **功能**: 获取当前用户的所有视频剪辑项目列表
  - **状态**: 占位接口，返回 501 错误
  - **说明**: 需要实现项目查询、搜索、分页功能

- ⚠️ `GET /api/video-editor/projects/{id}` - 获取项目详情
  - **功能**: 获取项目详细信息，包括关联的视频列表
  - **状态**: 占位接口，返回 501 错误
  - **说明**: 需要实现项目详情查询和关联视频查询

- ⚠️ `POST /api/video-editor/projects` - 创建项目
  - **功能**: 创建新的视频剪辑项目
  - **状态**: 占位接口，返回 501 错误
  - **说明**: 需要实现项目创建、参数验证、数据库保存

- ⚠️ `PUT /api/video-editor/projects/{id}` - 更新项目
  - **功能**: 更新项目的基本信息和剪辑参数
  - **状态**: 占位接口，返回 501 错误
  - **说明**: 需要实现项目信息更新功能

- ⚠️ `DELETE /api/video-editor/projects/{id}` - 删除项目
  - **功能**: 删除项目及其关联的视频和任务
  - **状态**: 占位接口，返回 501 错误
  - **说明**: 需要实现级联删除逻辑

- ⚠️ `POST /api/video-editor/upload` - 上传视频
  - **功能**: 上传视频文件到服务器
  - **状态**: 占位接口，返回 501 错误
  - **说明**: 需要实现文件上传、格式验证、缩略图生成、元数据提取

- ⚠️ `POST /api/video-editor/projects/{id}/start-edit` - 开始剪辑
  - **功能**: 启动AI视频剪辑任务
  - **状态**: 占位接口，返回 501 错误
  - **说明**: 需要实现剪辑任务创建、AI服务调用、异步任务处理

- ⚠️ `POST /api/video-editor/projects/{id}/export` - 导出视频
  - **功能**: 导出剪辑完成的视频
  - **状态**: 占位接口，返回 501 错误
  - **说明**: 需要实现视频导出任务创建、格式转换、质量设置

- ⚠️ `GET /api/video-editor/tasks/{id}` - 获取任务状态
  - **功能**: 获取剪辑或导出任务的当前状态和进度
  - **状态**: 占位接口，返回 501 错误
  - **说明**: 需要实现任务状态查询、进度更新

- ⚠️ `POST /api/video-editor/tasks/{id}/cancel` - 取消任务
  - **功能**: 取消正在进行的剪辑或导出任务
  - **状态**: 占位接口，返回 501 错误
  - **说明**: 需要实现任务取消、后台任务停止

- ⚠️ `DELETE /api/video-editor/projects/{id}/videos/{video_id}` - 删除项目视频
  - **功能**: 从项目中移除视频
  - **状态**: 占位接口，返回 501 错误
  - **说明**: 需要实现视频关联删除、文件清理

- ⚠️ `POST /api/video-editor/ai/cut` - AI智能裁剪
  - **功能**: 使用AI算法智能裁剪视频，自动识别精彩片段
  - **状态**: 占位接口，返回 501 错误
  - **说明**: 需要实现AI视频分析、精彩片段识别、自动裁剪

- ⚠️ `POST /api/video-editor/ai/subtitle` - AI生成字幕
  - **功能**: 使用AI语音识别生成视频字幕
  - **状态**: 占位接口，返回 501 错误
  - **说明**: 需要实现语音识别、字幕生成、样式设置

- ⚠️ `POST /api/video-editor/ai/filter` - AI滤镜美化
  - **功能**: 应用AI滤镜美化视频画面
  - **状态**: 占位接口，返回 501 错误
  - **说明**: 需要实现滤镜算法、画面美化、效果应用

- ⚠️ `POST /api/video-editor/ai/music` - AI配乐推荐
  - **功能**: 根据视频内容推荐合适的背景音乐
  - **状态**: 占位接口，返回 501 错误
  - **说明**: 需要实现视频内容分析、音乐库匹配、推荐算法

**总计预留接口: 20个**

## 八、数据模型说明

### 8.1 核心模型
- **User**: 用户表（管理员账号）
- **Device**: 设备表（客户端设备信息）
- **Account**: 账号表（社交媒体账号）
- **Message**: 消息表（监听到的消息）

### 8.2 任务模型
- **VideoTask**: 视频上传任务表
- **ChatTask**: 对话发送任务表
- **ListenTask**: 消息监听任务表

### 8.3 业务模型
- **PublishPlan**: 发布计划表
- **PlanVideo**: 计划视频表（发布计划中的视频列表）
- **Merchant**: 商家表
- **VideoLibrary**: 视频库表
- **AccountStats**: 账号统计数据表

## 九、功能模块说明

### 9.1 已实现功能
1. ✅ 用户认证（登录、登出、状态检查）
2. ✅ 设备管理（注册、查询、心跳）
3. ✅ 账号管理（CRUD、Cookies管理）
4. ✅ 视频任务管理（创建、查询、删除、回调）
5. ✅ 对话任务管理（创建、查询、回调）
6. ✅ 监听任务管理（查询、删除、回调）
7. ✅ 消息管理（查询、创建、删除、清空）
8. ✅ 发布计划管理（CRUD、添加视频）
9. ✅ 商家管理（CRUD）
10. ✅ 视频库管理（CRUD）
11. ✅ 数据统计（视频统计、账号统计）
12. ✅ 社交功能（视频上传、消息监听、消息回复）
13. ✅ AI视频剪辑（前端页面已实现，后端接口待实现）

### 9.2 待实现功能
1. ⚠️ 登录二维码生成（使用 Playwright）
2. ⚠️ 发布计划分发（manual/sms/qrcode/ai 四种模式）
3. ⚠️ 视频任务领取（二维码分发模式）
4. ⚠️ 账号统计数据自动更新（定时任务）
5. ⚠️ 净增粉丝数计算（数据统计）
6. ⚠️ AI视频剪辑后端功能（项目CRUD、视频上传、剪辑任务、AI功能）

## 十、开发说明

### 10.1 后端启动
```bash
cd center_code/backend
python app.py
```

### 10.2 前端启动
```bash
cd center_code/frontend
npm install
npm run dev
```

### 10.3 数据库初始化
```bash
cd center_code/backend
python init_database.py
python init_user.py
```

### 10.4 默认账号
- 用户名: `hbut`
- 密码: `dydy?123`

## 十一、注意事项

1. **环境变量**: 需要配置数据库连接信息（DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD）
2. **端口管理**: 后端自动检测可用端口（5000-5009），前端需要配置对应的代理地址
3. **Session 持久化**: 登录后 Session 有效期为 24 小时
4. **CORS 配置**: 开发环境已配置允许 localhost 跨域请求
5. **占位接口**: 预留接口仅提供接口定义和注释，具体实现待开发

## 十二、接口统计

- **已实现接口**: 58个
- **预留接口**: 20个
- **总计接口**: 78个

---

**文档版本**: v1.1  
**最后更新**: 2025-01-20

