# Cookies 获取流程说明

## 📋 概述

发布视频时，系统从**数据库的 `accounts` 表**中获取cookies，不再依赖文件系统。

## 🔄 完整流程

### 1. Cookies 存储位置

**数据库表：`accounts`**
- **字段名**：`cookies` (Text类型)
- **存储格式**：JSON字符串（Playwright的storage_state格式）
- **示例**：
```json
{
  "cookies": [...],
  "origins": [
    {
      "origin": "https://creator.douyin.com",
      "localStorage": [...]
    }
  ]
}
```

### 2. 发布视频时的Cookies获取流程

```
视频上传任务创建
    ↓
任务处理器检测到pending任务
    ↓
execute_video_upload(task_id)
    ↓
从数据库获取账号信息
    ↓
get_account_from_db(account_id, db)
    ↓
查询 accounts 表
    ↓
获取 account.cookies (JSON字符串)
    ↓
解析JSON字符串为字典
    ↓
保存到临时文件
    ↓
传递给上传器使用
```

### 3. 代码位置

#### 获取Cookies的代码
**文件**：`center_code/backend/services/task_executor.py`

```python
# 第53-76行：从数据库获取账号信息（包括cookies）
def get_account_from_db(account_id: int, db: Session) -> Optional[Dict]:
    account = db.query(Account).filter(Account.id == account_id).first()
    return {
        'id': account.id,
        'cookies': account.cookies  # 从数据库字段获取
    }

# 第170-188行：在视频上传任务中使用
account_info = get_account_from_db(task.account_id, db)
cookies_json = account_info.get('cookies')  # 获取cookies JSON字符串
cookies_data = json.loads(cookies_json)     # 解析为字典
account_file = save_cookies_to_temp(cookies_data, task.account_id)  # 保存到临时文件
```

### 4. Cookies 的更新方式

#### 方式1：通过API更新
**接口**：`PUT /api/accounts/{account_id}/cookies`

**文件**：`center_code/backend/blueprints/accounts.py` (第402-521行)

```python
# 更新cookies到数据库
account.cookies = cookies_json  # 保存JSON字符串
account.login_status = 'logged_in'
account.last_login_time = datetime.now()
db.commit()
```

#### 方式2：上传完成后自动更新
**文件**：`center_code/backend/services/task_executor.py` (第79-102行)

```python
# 视频上传完成后，自动更新cookies
def save_cookies_to_db(account_id: int, cookies: Dict, db: Session):
    account.cookies = cookies_json  # 更新数据库中的cookies
    account.login_status = 'logged_in'
    account.last_login_time = datetime.now()
    db.commit()
```

### 5. 数据库表结构

**表名**：`accounts`

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | Integer | 主键 |
| device_id | Integer | 关联设备ID |
| account_name | String(255) | 账号名称 |
| platform | String(50) | 平台（douyin/kuaishou等） |
| **cookies** | **Text** | **Cookies JSON字符串（关键字段）** |
| login_status | String(50) | 登录状态 |
| last_login_time | DateTime | 最后登录时间 |

### 6. 临时文件处理

虽然cookies存储在数据库中，但在执行上传时：
1. 从数据库读取cookies（JSON字符串）
2. 解析为字典格式
3. **保存到临时文件**（因为Playwright需要文件路径）
4. 上传完成后，如果cookies有更新，会写回数据库
5. 临时文件会被自动清理

**代码位置**：`center_code/backend/services/task_executor.py` (第104-147行)

```python
def save_cookies_to_temp(cookies_data: Dict, account_id: Optional[int] = None) -> str:
    # 保存到临时文件
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8')
    temp_file.write(cookies_json)
    temp_file.close()
    return temp_file.name
```

## 🔍 查询Cookies的方法

### 方法1：通过API查询
```bash
GET /api/accounts/{account_id}/cookies
```

### 方法2：直接查询数据库
```sql
SELECT id, account_name, cookies, login_status 
FROM accounts 
WHERE id = {account_id};
```

### 方法3：查看代码日志
在 `task_executor.py` 中，获取cookies时会记录日志：
```python
douyin_logger.info(f"Loading cookies from: {account_file}")
```

## ⚠️ 注意事项

1. **Cookies格式**：必须是Playwright的storage_state格式（包含cookies和origins）
2. **存储方式**：以JSON字符串形式存储在数据库Text字段中
3. **自动更新**：上传完成后，如果cookies有变化，会自动更新回数据库
4. **临时文件**：执行时使用临时文件，完成后自动清理
5. **数据来源**：**完全从数据库获取，不再使用文件系统**

## 📝 总结

- ✅ **Cookies存储在数据库**：`accounts.cookies` 字段
- ✅ **获取方式**：通过 `get_account_from_db()` 函数从数据库查询
- ✅ **更新方式**：通过API或上传完成后自动更新
- ✅ **使用方式**：读取后保存到临时文件供Playwright使用
- ✅ **数据流**：数据库 → 临时文件 → Playwright → 更新回数据库

