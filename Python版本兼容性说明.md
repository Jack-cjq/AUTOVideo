# Python 版本兼容性说明

## ✅ Python 3.9.5 完全兼容

你的服务器上的 **Python 3.9.5** 完全兼容本项目，可以正常使用。

## 依赖兼容性检查

### 核心依赖
- ✅ **Flask 3.0.0** - 需要 Python >= 3.8
- ✅ **SQLAlchemy 2.0.23** - 需要 Python >= 3.8
- ✅ **playwright >=1.40.0** - 支持 Python 3.8+
- ✅ **werkzeug 3.0.1** - 支持 Python 3.8+
- ✅ **aiohttp 3.9.5** - 支持 Python 3.8+
- ✅ **opencv-python 4.8.1.78** - 支持 Python 3.8+

### Python 版本要求
- **最低要求**: Python 3.8+
- **推荐版本**: Python 3.9+（你的版本 ✅）
- **最佳版本**: Python 3.10+ 或 3.11+（性能更好）

## 使用 Python 3.9 创建虚拟环境

### 方法一：使用更新后的部署脚本（推荐）

部署脚本已更新，会自动检测并使用 `python3.9`：

```bash
cd /var/www/autovideo/AUTOVideo
./deploy.sh
```

### 方法二：手动指定 Python 3.9

如果脚本没有自动使用 Python 3.9，可以手动创建虚拟环境：

```bash
cd /var/www/autovideo/AUTOVideo/center_code/backend

# 使用 python3.9 创建虚拟环境
python3.9 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 验证 Python 版本
python --version  # 应该显示 Python 3.9.5

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt
```

## 验证兼容性

安装完依赖后，可以验证：

```bash
# 激活虚拟环境
source venv/bin/activate

# 测试导入主要模块
python -c "import flask; print('Flask:', flask.__version__)"
python -c "import sqlalchemy; print('SQLAlchemy:', sqlalchemy.__version__)"
python -c "import playwright; print('Playwright:', playwright.__version__)"

# 测试应用启动
python app.py
```

## 常见问题

### Q: 为什么部署脚本检测到的是 Python 3.8？

A: 如果系统默认 `python3` 指向 3.8，但已安装 3.9，可以：

```bash
# 检查所有 Python 版本
ls -la /usr/bin/python*

# 使用 python3.9 明确指定
python3.9 -m venv venv
```

### Q: 可以升级到 Python 3.10 或 3.11 吗？

A: 可以，但需要：
1. 安装新版本 Python
2. 重新创建虚拟环境
3. 重新安装所有依赖

Python 3.9.5 已经足够，除非有特殊需求，否则不需要升级。

### Q: 虚拟环境创建失败？

A: 确保安装了 `python3.9-venv`：

```bash
sudo apt install python3.9-venv
```

## 总结

✅ **Python 3.9.5 完全兼容，可以直接使用！**

- 所有依赖都支持 Python 3.9
- 性能良好
- 稳定可靠

继续使用 Python 3.9.5 进行部署即可。

