# API 文档

## 新增 API 接口

### 1. 发布计划 API (`/api/publish-plans`)

#### 获取发布计划列表
- **GET** `/api/publish-plans`
- **参数**:
  - `platform` (可选): 平台筛选 (douyin/kuaishou/xiaohongshu)
  - `status` (可选): 状态筛选 (pending/publishing/completed/failed)
  - `limit` (可选): 每页数量，默认20
  - `offset` (可选): 偏移量，默认0

#### 创建发布计划
- **POST** `/api/publish-plans`
- **请求体**:
  ```json
  {
    "plan_name": "计划名称",
    "platform": "douyin",
    "merchant_id": 1,
    "distribution_mode": "manual",
    "publish_time": "2025-12-01 12:00:00"
  }
  ```

#### 获取发布计划详情
- **GET** `/api/publish-plans/{plan_id}`

#### 更新发布计划
- **PUT** `/api/publish-plans/{plan_id}`

#### 删除发布计划
- **DELETE** `/api/publish-plans/{plan_id}`

#### 向计划添加视频
- **POST** `/api/publish-plans/{plan_id}/videos`
- **请求体**:
  ```json
  {
    "video_url": "视频URL",
    "video_title": "视频标题",
    "thumbnail_url": "缩略图URL"
  }
  ```

#### 保存发布信息（占位接口）
- **POST** `/api/publish-plans/{plan_id}/save-info`

---

### 2. 商家管理 API (`/api/merchants`)

#### 获取商家列表
- **GET** `/api/merchants`
- **参数**:
  - `search` (可选): 搜索商家名称
  - `status` (可选): 状态筛选 (active/inactive)
  - `limit` (可选): 每页数量，默认50
  - `offset` (可选): 偏移量，默认0

#### 创建商家
- **POST** `/api/merchants`
- **请求体**:
  ```json
  {
    "merchant_name": "商家名称",
    "contact_person": "联系人",
    "contact_phone": "联系电话",
    "contact_email": "邮箱",
    "address": "地址",
    "status": "active"
  }
  ```

#### 获取商家详情
- **GET** `/api/merchants/{merchant_id}`

#### 更新商家
- **PUT** `/api/merchants/{merchant_id}`

#### 删除商家
- **DELETE** `/api/merchants/{merchant_id}`

---

### 3. 云视频库 API (`/api/video-library`)

#### 获取视频列表
- **GET** `/api/video-library`
- **参数**:
  - `search` (可选): 搜索视频名称
  - `platform` (可选): 平台筛选
  - `limit` (可选): 每页数量，默认50
  - `offset` (可选): 偏移量，默认0

#### 上传视频
- **POST** `/api/video-library`
- **请求体**:
  ```json
  {
    "video_name": "视频名称",
    "video_url": "视频URL",
    "thumbnail_url": "缩略图URL",
    "video_size": 1024000,
    "duration": 60,
    "platform": "douyin",
    "tags": "标签1,标签2",
    "description": "描述"
  }
  ```

#### 获取视频详情
- **GET** `/api/video-library/{video_id}`

#### 更新视频信息
- **PUT** `/api/video-library/{video_id}`

#### 删除视频
- **DELETE** `/api/video-library/{video_id}`

---

### 4. 数据中心 API (`/api/data-center`)

#### 获取视频统计数据
- **GET** `/api/data-center/video-stats`
- **参数**:
  - `account_id` (可选): 账号ID
  - `platform` (可选): 平台筛选
  - `start_date` (可选): 开始日期 (ISO格式)
  - `end_date` (可选): 结束日期 (ISO格式)

#### 获取账号统计数据
- **GET** `/api/data-center/account-stats`
- **参数**:
  - `account_id` (必需): 账号ID
  - `platform` (可选): 平台筛选
  - `days` (可选): 统计天数，默认7

#### 创建账号统计数据（占位接口）
- **POST** `/api/data-center/account-stats`

---

## 新增数据模型

### 1. PublishPlan (发布计划表)
- `id`: 主键
- `plan_name`: 计划名称
- `platform`: 平台
- `merchant_id`: 关联商家ID
- `video_count`: 视频数量
- `published_count`: 已发布数量
- `pending_count`: 待发布数量
- `claimed_count`: 已领取数量
- `account_count`: 账号数量
- `distribution_mode`: 分发模式 (manual/sms/qrcode/ai)
- `status`: 状态 (pending/publishing/completed/failed)
- `publish_time`: 发布时间
- `created_at`: 创建时间
- `updated_at`: 更新时间

### 2. PlanVideo (计划视频表)
- `id`: 主键
- `plan_id`: 计划ID
- `video_url`: 视频URL
- `video_title`: 视频标题
- `thumbnail_url`: 缩略图URL
- `status`: 状态
- `created_at`: 创建时间

### 3. Merchant (商家表)
- `id`: 主键
- `merchant_name`: 商家名称（唯一）
- `contact_person`: 联系人
- `contact_phone`: 联系电话
- `contact_email`: 邮箱
- `address`: 地址
- `status`: 状态 (active/inactive)
- `created_at`: 创建时间
- `updated_at`: 更新时间

### 4. VideoLibrary (云视频库表)
- `id`: 主键
- `video_name`: 视频名称
- `video_url`: 视频URL
- `thumbnail_url`: 缩略图URL
- `video_size`: 文件大小（字节）
- `duration`: 视频时长（秒）
- `platform`: 来源平台
- `tags`: 标签（逗号分隔）
- `description`: 描述
- `upload_time`: 上传时间
- `created_at`: 创建时间
- `updated_at`: 更新时间

### 5. AccountStats (账号统计表)
- `id`: 主键
- `account_id`: 账号ID
- `stat_date`: 统计日期
- `platform`: 平台
- `followers`: 粉丝数
- `playbacks`: 播放量
- `likes`: 点赞数
- `comments`: 评论数
- `shares`: 分享数
- `published_videos`: 发布视频数
- `created_at`: 创建时间

---

## 前端页面

### 1. Dashboard (仪表盘)
- 从 API 获取视频统计数据
- 显示 KPI 指标卡片
- 显示最近发布计划列表
- 支持平台筛选和时间范围筛选

### 2. Publish (立即发布)
- 选择账号
- 输入视频信息
- 创建发布任务

### 3. PublishPlan (发布计划)
- 发布计划列表（支持筛选和分页）
- 创建/编辑/删除发布计划
- 向计划添加视频

### 4. Accounts (授权管理)
- 账号列表（支持筛选和分页）
- 添加/编辑/删除账号
- 账号登录功能（占位）

### 5. DataCenter (数据中心)
- 统计数据展示
- 支持平台和账号筛选
- 支持日期范围筛选
- 图表展示（占位，待实现）

### 6. Merchants (商家管理)
- 商家列表（支持筛选和分页）
- 创建/编辑/删除商家

### 7. VideoLibrary (云视频库)
- 视频列表（网格展示）
- 上传/编辑/删除视频
- 支持平台筛选和搜索

---

## 注意事项

1. **复杂功能占位**: 以下功能只提供了 API 接口占位，具体实现待开发：
   - 保存发布信息 (`/api/publish-plans/{plan_id}/save-info`)
   - 创建账号统计数据 (`/api/data-center/account-stats` POST)
   - 账号登录功能
   - 视频预览功能
   - 数据图表展示

2. **数据库初始化**: 运行 `python init_database.py` 会自动创建所有新表。

3. **API 认证**: 所有 API 都需要登录认证（使用 `@login_required` 装饰器）。

4. **错误处理**: 所有 API 都返回统一的响应格式：
   ```json
   {
     "success": true/false,
     "data": {},
     "message": "消息"
   }
   ```

