# 腾讯云COS配置指南

## 概述

系统已集成腾讯云COS（对象存储）服务，用于存储视频库中的视频文件。上传的视频会自动存储到COS，并返回COS的访问URL。

## 配置步骤

### 1. 安装依赖

首先安装腾讯云COS SDK：

```bash
cd center_code/backend
pip install cos-python-sdk-v5>=1.9.24
```

或者安装所有依赖：

```bash
pip install -r requirements.txt
```

### 2. 创建子用户（推荐，更安全）

**⚠️ 重要：强烈建议使用子用户API密钥，而不是主账号密钥！**

1. 登录 [腾讯云控制台](https://console.cloud.tencent.com/)
2. 进入 [访问管理CAM](https://console.cloud.tencent.com/cam)
3. 点击左侧菜单"用户" -> "用户列表"
4. 点击"新建用户" -> "自定义创建"
5. 填写用户信息：
   - **用户名**: 例如 `cos-video-library`
   - **访问方式**: 选择"编程访问"（启用API密钥）
   - **用户权限**: 选择"从策略继承权限"
6. 添加权限策略：
   - 搜索并添加 `QcloudCOSDataReadWrite`（COS数据读写权限）
   - 或者更精确的权限：`QcloudCOSBucketReadWrite`（存储桶读写权限）
7. 创建完成后，在用户列表中点击该用户
8. 在"API密钥"标签页中，点击"新建密钥"
9. 保存好 **SecretId** 和 **SecretKey**（只显示一次，请妥善保管）

### 3. 创建存储桶

1. 进入 [对象存储COS](https://console.cloud.tencent.com/cos)
2. 创建存储桶（如果还没有）
   - **存储桶名称**: 例如 `ai-video-1391237756`
   - **所属地域**: 例如 `中国南京` (ap-nanjing)
   - **访问权限**: 建议选择 `私有读写`（更安全）
   - **版本控制**: 建议关闭（节省成本）
   - **日志存储**: 建议开启（便于排查问题）
   - **服务端加密**: 建议启用 `SSE-COS`（免费，更安全）
3. 获取以下信息：
   - **SecretId**: 子用户的SecretId（从步骤2获取）
   - **SecretKey**: 子用户的SecretKey（从步骤2获取）
   - **Region**: 存储桶所在地域代码，如 `ap-nanjing`（南京）
   - **Bucket**: 存储桶名称，如 `ai-video-1391237756`
   - **Domain**（可选）: 自定义域名，如 `https://cdn.example.com`
   - **请求域名**: 系统自动生成，如 `ai-video-1391237756.cos.ap-nanjing.myqcloud.com`

### 4. 配置环境变量

在Windows PowerShell中设置环境变量：

```powershell
# 必需配置（请替换为你的实际值）
$env:COS_SECRET_ID="your_secret_id"  # 从API密钥管理获取
$env:COS_SECRET_KEY="your_secret_key"  # 从API密钥管理获取
$env:COS_REGION="ap-nanjing"  # 存储桶地域代码
$env:COS_BUCKET="ai-video-1391237756"  # 你的存储桶名称

# 可选配置（如果使用自定义域名）
$env:COS_DOMAIN="https://cdn.example.com"  # 自定义域名（可选）
$env:COS_SCHEME="https"  # 协议，默认https
```

**示例配置**（基于你的存储桶）：
```powershell
$env:COS_SECRET_ID="AKIDxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
$env:COS_SECRET_KEY="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
$env:COS_REGION="ap-nanjing"
$env:COS_BUCKET="ai-video-1391237756"
```

或者在Linux/Mac中：

```bash
export COS_SECRET_ID="your_secret_id"
export COS_SECRET_KEY="your_secret_key"
export COS_REGION="ap-nanjing"
export COS_BUCKET="your-bucket-name"
export COS_DOMAIN="https://cdn.example.com"  # 可选
export COS_SCHEME="https"  # 可选，默认https
```

### 5. 或者直接修改配置文件

编辑 `center_code/backend/config.py`，直接修改COS配置：

```python
COS_SECRET_ID = "your_secret_id"  # 从API密钥管理获取
COS_SECRET_KEY = "your_secret_key"  # 从API密钥管理获取
COS_REGION = "ap-nanjing"  # 存储桶地域代码
COS_BUCKET = "ai-video-1391237756"  # 你的存储桶名称
COS_DOMAIN = "https://cdn.example.com"  # 可选，自定义域名
COS_SCHEME = "https"  # 可选，默认https
```

**示例配置**（基于你的存储桶）：
```python
COS_SECRET_ID = "AKIDxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
COS_SECRET_KEY = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
COS_REGION = "ap-nanjing"
COS_BUCKET = "ai-video-1391237756"
COS_DOMAIN = ""  # 如果使用默认域名，留空即可
COS_SCHEME = "https"
```

**⚠️ 重要提示**：
- 如果存储桶访问权限设置为"私有读写"，需要配置访问策略或使用临时密钥
- 建议使用环境变量配置，避免将密钥写入代码

## 使用说明

### 上传视频到视频库

1. **通过前端界面上传**：
   - 进入"视频库"页面
   - 点击"上传素材"按钮
   - 选择视频文件
   - 系统会自动上传到COS并保存到数据库

2. **通过API上传**：
   ```bash
   POST /api/video-library
   Content-Type: multipart/form-data
   
   file: 视频文件
   video_name: 视频名称（可选）
   platform: 平台（可选）
   tags: 标签（可选，逗号分隔）
   description: 描述（可选）
   ```

3. **只保存URL（不上传文件）**：
   ```bash
   POST /api/video-library
   Content-Type: application/json
   
   {
     "video_name": "视频名称",
     "video_url": "https://your-bucket.cos.ap-nanjing.myqcloud.com/video/2025/01/14/filename.mp4",
     "thumbnail_url": "https://...",
     "video_size": 1024000,
     "duration": 60,
     "platform": "douyin",
     "tags": "标签1,标签2",
     "description": "视频描述"
   }
   ```

### 文件存储结构

上传到COS的文件会按照以下结构存储：

```
video/
  └── 2025/
      └── 01/
          └── 14/
              └── filename.mp4

thumbnail/
  └── 2025/
      └── 01/
          └── 14/
              └── thumbnail.jpg
```

### 删除视频

删除视频时，如果视频URL是COS URL，系统会自动删除COS中的文件。

## 安全建议

### 1. 使用子用户API密钥（强烈推荐）

**为什么使用子用户？**
- ✅ **更安全**：主账号密钥拥有账号下所有资源的完全控制权，一旦泄露后果严重
- ✅ **权限隔离**：子用户可以精确配置所需权限，遵循"最小权限原则"
- ✅ **便于管理**：可以随时禁用或删除子用户密钥，不影响主账号
- ✅ **风险控制**：即使子用户密钥泄露，影响范围也仅限于分配的权限

**如何创建子用户？**
1. 进入 [访问管理CAM](https://console.cloud.tencent.com/cam)
2. 创建子用户，启用"编程访问"
3. 添加COS相关权限策略（如 `QcloudCOSDataReadWrite`）
4. 创建API密钥并保存

### 2. 存储桶权限配置

- **私有读写**（推荐）：
  - 更安全，只有通过API密钥才能访问
  - 子用户需要相应的COS权限才能操作
  - 适合生产环境

- **公有读私有写**：
  - 可以通过URL直接访问文件
  - 适合需要公开访问的场景
  - 注意：任何人都可以访问文件

### 3. 访问策略配置

如果使用"私有读写"权限：
- 子用户需要被授予COS相关权限策略
- 在CAM中为子用户添加策略：`QcloudCOSDataReadWrite` 或更精确的权限
- 不需要在存储桶级别额外配置策略（子用户权限已足够）

### 4. 密钥安全

- ⚠️ **不要将密钥提交到代码仓库**
- ⚠️ **使用环境变量或密钥管理服务存储密钥**
- ⚠️ **定期轮换密钥**
- ⚠️ **如果密钥泄露，立即禁用并创建新密钥**

2. **CDN加速**（可选）：
   - 如果使用自定义域名，建议配置CDN加速
   - 在COS控制台配置自定义域名和CDN加速

3. **费用**：
   - COS按存储容量和流量计费
   - 建议设置存储桶的生命周期规则，自动删除过期文件

4. **安全性**：
   - 不要将SecretId和SecretKey提交到代码仓库
   - 建议使用环境变量或密钥管理服务

5. **兼容性**：
   - 如果COS SDK未安装或配置不完整，系统会回退到本地存储
   - 不会影响现有功能

## 故障排查

### 问题1：上传失败，提示"COS配置不完整"

**解决方案**：
- 检查环境变量是否设置正确
- 检查config.py中的配置是否正确
- 确保COS_SECRET_ID、COS_SECRET_KEY和COS_BUCKET都已配置

### 问题2：上传失败，提示"COS客户端错误"

**解决方案**：
- 检查SecretId和SecretKey是否正确
- 检查存储桶名称是否正确
- 检查地域代码是否正确（如ap-nanjing）

### 问题3：文件上传成功但无法访问

**解决方案**：
- 检查存储桶的访问权限
- 检查自定义域名配置是否正确
- 检查CDN配置（如果使用）

## 相关文件

- `center_code/backend/utils/cos_service.py` - COS服务模块
- `center_code/backend/blueprints/video_library.py` - 视频库API
- `center_code/backend/config.py` - 配置文件
- `center_code/backend/requirements.txt` - 依赖列表

