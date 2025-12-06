#!/bin/bash

echo "========================================"
echo "启动后端服务器"
echo "========================================"
echo ""

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python，请先安装Python"
    exit 1
fi

# 设置数据库密码（如果还没有设置）
if [ -z "$DB_PASSWORD" ]; then
    echo "提示: 如果数据库连接失败，请设置环境变量 DB_PASSWORD"
    echo "示例: export DB_PASSWORD=your_password"
    echo ""
fi

# 启动服务器（默认端口5000，如果被占用会自动尝试5001-5009）
echo "正在启动服务器..."
echo "如果端口5000被占用，将自动使用其他端口"
echo ""
python3 app.py

