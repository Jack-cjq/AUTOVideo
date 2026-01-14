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
    'password': os.getenv('DB_PASSWORD', 'Yjy79378454678'),  # ⚠️ 请设置你的 MySQL 密码
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
    return f"mysql+pymysql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}?charset={config['charset']}&collation=utf8mb4_bin"


# =========================
# AI (DeepSeek/OpenAI-compatible)
# =========================
# 通过环境变量注入密钥，避免写入代码库
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "sk-84f80df638414e4e89f60a3507d356f1")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

# =========================
# TTS (Baidu Intelligent Cloud)
# =========================
BAIDU_APP_ID = os.environ.get("BAIDU_APP_ID", "7396532")
BAIDU_API_KEY = os.environ.get("BAIDU_API_KEY", "TTI6soTvhgaKdXATP7SYZWVp")
BAIDU_SECRET_KEY = os.environ.get("BAIDU_SECRET_KEY", "JksQ0PA545ChX9uzdtGPhPSVpvkvQu3I")
# 客户端唯一标识：可用机器名/UUID，留空则后端自动生成
BAIDU_CUID = os.environ.get("BAIDU_CUID", "")

# =========================
# FFmpeg 配置
# =========================
# FFmpeg 可执行文件路径（如果不在系统 PATH 中）
# 可以通过环境变量 FFMPEG_PATH 设置，例如：
# Windows: set FFMPEG_PATH=D:\软件\ffmpeg\bin\ffmpeg.exe
# 或者直接在这里设置：
FFMPEG_PATH = os.environ.get("FFMPEG_PATH", r"D:\ffmpeg\bin\ffmpeg.exe")