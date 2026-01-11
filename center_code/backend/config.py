"""
数据库配置文件
使用 MySQL 数据库

配置方式：
1. 设置环境变量（推荐）
2. 直接修改下面的 MYSQL_CONFIG 字典
"""
import os

# MySQL 配置
# 如果设置了环境变量，优先使用环境变量
# 否则使用下面的默认值
MYSQL_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'database': os.getenv('DB_NAME', 'autovideo'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', 'Yjy793784546'),  # ⚠️ 请设置你的 MySQL 密码
    'charset': 'utf8mb4'
}

# 如果密码为空，提示用户配置
if not MYSQL_CONFIG['password']:
    print("\n⚠️  警告：数据库密码未配置！")
    print("请设置环境变量 DB_PASSWORD 或修改 config.py 中的 MYSQL_CONFIG")
    print("示例：export DB_PASSWORD=your_password\n")

def get_db_config():
    """获取数据库配置"""
    return MYSQL_CONFIG

def get_db_url():
    """获取数据库连接URL"""
    config = get_db_config()
    return f"mysql+pymysql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}?charset={config['charset']}"
