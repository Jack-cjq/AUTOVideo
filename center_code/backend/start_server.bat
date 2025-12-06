@echo off
echo ========================================
echo 启动后端服务器
echo ========================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python
    pause
    exit /b 1
)

REM 设置数据库密码（如果还没有设置）
if "%DB_PASSWORD%"=="" (
    echo 提示: 如果数据库连接失败，请设置环境变量 DB_PASSWORD
    echo 示例: set DB_PASSWORD=your_password
    echo.
)

REM 启动服务器（默认端口5000，如果被占用会自动尝试5001-5009）
echo 正在启动服务器...
echo 如果端口5000被占用，将自动使用其他端口
echo.
python app.py

pause

