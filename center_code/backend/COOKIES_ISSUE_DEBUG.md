# Cookies失效问题诊断

## 问题描述

Cookies在授权页面可以登录成功，但在发布视频时失效。

## 可能的原因

### 1. Cookies不完整（最可能）

**问题**：前端提取的cookies可能缺少HttpOnly的cookies

**原因**：
- 前端JavaScript只能获取非HttpOnly的cookies（通过`document.cookie`）
- 关键的登录cookies（如`sessionid`、`passport_auth`）通常是HttpOnly的
- 这些cookies无法通过JavaScript获取

**解决方案**：
1. **使用Network标签页获取完整cookies**（推荐）
   - 在登录助手页面的步骤3中，使用"方法1：从Network标签页获取"
   - 打开开发者工具的Network标签页
   - 刷新页面或执行任意操作
   - 找到任意一个请求，查看Request Headers中的Cookie值
   - 使用提供的`parseCookieHeader()`函数解析

2. **使用浏览器扩展**
   - 安装支持获取HttpOnly cookies的浏览器扩展
   - 提取完整的cookies

### 2. Cookies格式问题

**问题**：从数据库读取时格式可能不正确

**检查点**：
- cookies必须是Playwright的storage_state格式
- 必须包含`cookies`数组和`origins`数组
- 每个cookie必须有`name`、`value`、`domain`、`path`字段

**已修复**：
- `save_cookies_to_temp()`函数会自动修复格式
- 自动补充缺失的字段
- 自动从cookies推断origins

### 3. Cookies过期

**问题**：虽然授权页面能用，但cookies可能已经过期

**检查方法**：
- 查看cookies中的`expires`字段
- 检查`last_login_time`是否很久以前

**解决方案**：
- 重新登录获取新的cookies

### 4. 域名/路径不匹配

**问题**：授权页面和发布页面的域名可能不同

**检查点**：
- 授权页面：`https://creator.douyin.com/`
- 发布页面：`https://creator.douyin.com/creator-micro/content/upload`

**已处理**：
- 代码会自动从cookies推断并添加必要的origins
- 包括`https://douyin.com`和`https://creator.douyin.com`

### 5. localStorage缺失

**问题**：前端提取的cookies可能缺少localStorage数据

**影响**：
- localStorage中可能存储了重要的登录状态
- 缺少localStorage可能导致登录失效

**已处理**：
- 前端提取代码会尝试获取localStorage
- 后端会自动修复localStorage格式

## 诊断步骤

### 1. 检查cookies完整性

查看后端日志，应该能看到：
```
Loaded cookies for account X: N cookies, M origins
Missing important cookies: [...]
```

如果看到"Missing important cookies"，说明cookies不完整。

### 2. 检查cookies格式

查看临时文件内容（在日志中会显示路径）：
```python
# 临时文件路径通常在日志中显示
# 例如：C:\Users\...\AppData\Local\Temp\tmpXXXXXX.json
```

检查文件内容：
- 是否有`cookies`数组
- 是否有`origins`数组
- cookies中是否有关键的登录cookies

### 3. 验证cookies有效性

在浏览器中手动验证：
1. 打开开发者工具
2. 清除所有cookies
3. 导入cookies（使用浏览器扩展或手动设置）
4. 访问`https://creator.douyin.com/creator-micro/content/upload`
5. 检查是否能正常访问

## 解决方案

### 方案1：使用Network标签页获取完整cookies（推荐）

1. 在登录助手页面，选择"方法1：从Network标签页获取"
2. 按照提示操作，获取完整的Cookie头
3. 使用`parseCookieHeader()`函数解析
4. 提交完整的cookies

### 方案2：使用Playwright直接获取（最可靠）

修改登录流程，使用Playwright直接获取storage_state：
1. 打开浏览器
2. 用户手动登录
3. 使用`context.storage_state()`获取完整的storage_state
4. 保存到数据库

### 方案3：添加cookies验证和自动刷新

在任务执行前验证cookies有效性：
1. 先访问一个简单的页面验证cookies
2. 如果失效，自动触发重新登录流程
3. 更新cookies后继续执行任务

## 当前代码的改进

已添加：
1. ✅ Cookies格式自动修复
2. ✅ 关键cookies检查
3. ✅ 详细的日志输出
4. ✅ 临时文件验证

建议：
1. ⚠️ 使用Network标签页获取完整cookies
2. ⚠️ 定期检查cookies是否过期
3. ⚠️ 考虑添加cookies自动刷新机制

