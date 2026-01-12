#!/bin/bash

# 数据库配置修复脚本

echo "=========================================="
echo "数据库配置诊断和修复工具"
echo "=========================================="
echo ""

BACKEND_DIR="/var/www/autovideo/AUTOVideo/center_code/backend"
ENV_FILE="$BACKEND_DIR/.env"

if [ ! -f "$ENV_FILE" ]; then
    echo "❌ .env 文件不存在: $ENV_FILE"
    exit 1
fi

echo "📋 当前 .env 文件内容："
echo "----------------------------------------"
cat $ENV_FILE
echo "----------------------------------------"
echo ""

# 检查 DB_USER 配置
DB_USER=$(grep "^DB_USER=" $ENV_FILE | cut -d'=' -f2 | tr -d ' ' | tr -d '"' | tr -d "'")

if [ -z "$DB_USER" ]; then
    echo "⚠️  DB_USER 未设置，使用默认值 'root'"
    DB_USER="root"
fi

# 检查是否包含 @ 符号
if [[ "$DB_USER" == *"@"* ]]; then
    echo "❌ 错误：DB_USER 包含 '@' 符号: $DB_USER"
    echo "   这会导致连接字符串解析错误"
    echo ""
    echo "🔧 修复建议："
    echo "   DB_USER 应该只是用户名，不包含 @ 符号"
    echo "   例如：DB_USER=root 或 DB_USER=autovideo"
    echo ""
    
    # 提取正确的用户名（@ 之前的部分）
    CORRECT_USER=$(echo $DB_USER | cut -d'@' -f1)
    echo "   检测到可能的用户名: $CORRECT_USER"
    echo ""
    read -p "是否要修复为 $CORRECT_USER? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # 备份原文件
        cp $ENV_FILE ${ENV_FILE}.backup
        echo "✓ 已备份原文件到 ${ENV_FILE}.backup"
        
        # 修复 DB_USER
        sed -i "s/^DB_USER=.*/DB_USER=$CORRECT_USER/" $ENV_FILE
        echo "✓ 已修复 DB_USER=$CORRECT_USER"
    fi
fi

# 检查其他配置
echo ""
echo "📊 配置检查："
echo "----------------------------------------"

# 加载环境变量（安全方式）
set -a
source $ENV_FILE 2>/dev/null || export $(cat $ENV_FILE | grep -v '^#' | grep -v '^$' | xargs)
set +a

echo "DB_HOST=${DB_HOST:-未设置}"
echo "DB_PORT=${DB_PORT:-未设置}"
echo "DB_NAME=${DB_NAME:-未设置}"
echo "DB_USER=${DB_USER:-未设置}"
echo "DB_PASSWORD=${DB_PASSWORD:+已设置（隐藏）}"

if [ -z "$DB_PASSWORD" ]; then
    echo "⚠️  DB_PASSWORD 未设置！"
fi

echo "----------------------------------------"
echo ""

# 测试 MySQL 连接
echo "🔍 测试 MySQL 连接..."
echo "----------------------------------------"

if command -v mysql &> /dev/null; then
    if [ -n "$DB_PASSWORD" ]; then
        mysql -h${DB_HOST:-localhost} -P${DB_PORT:-3306} -u${DB_USER:-root} -p"${DB_PASSWORD}" -e "SELECT 1;" 2>&1 | head -1
        if [ $? -eq 0 ]; then
            echo "✓ MySQL 连接成功！"
        else
            echo "❌ MySQL 连接失败"
            echo ""
            echo "可能的原因："
            echo "  1. MySQL 服务未启动: sudo systemctl start mysql"
            echo "  2. 用户名或密码错误"
            echo "  3. 数据库用户没有权限"
        fi
    else
        echo "⚠️  无法测试连接（DB_PASSWORD 未设置）"
    fi
else
    echo "⚠️  mysql 客户端未安装，跳过连接测试"
fi

echo ""
echo "=========================================="
echo "诊断完成"
echo "=========================================="
echo ""
echo "如果问题已修复，请重新运行："
echo "  cd $BACKEND_DIR"
echo "  source venv/bin/activate"
echo "  export \$(cat .env | grep -v '^#' | xargs)"
echo "  python init_database.py"
echo "  python init_user.py"
echo ""

