"""
数据库配置文件
使用 MySQL 数据库

配置方式：
1. 创建 .env 文件（推荐，本地开发使用）
2. 设置系统环境变量（生产环境推荐）
3. 直接修改下面的 MYSQL_CONFIG 字典（不推荐）

.env 文件示例请参考 env.example 文件
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
# 从当前文件所在目录查找 .env 文件
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ 已加载环境变量文件: {env_path}")
else:
    # 如果当前目录没有，尝试从项目根目录查找
    root_env_path = Path(__file__).parent.parent / '.env'
    if root_env_path.exists():
        load_dotenv(root_env_path)
        print(f"✅ 已加载环境变量文件: {root_env_path}")
    else:
        print("ℹ️  未找到 .env 文件，将使用系统环境变量或默认值")

# MySQL 配置
# 所有配置都从环境变量读取，避免硬编码敏感信息
# 请在 .env 文件中配置这些值
MYSQL_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '3306') or '3306'),
    'database': os.getenv('DB_NAME', ''),
    'user': os.getenv('DB_USER', ''),
    'password': os.getenv('DB_PASSWORD', ''),  # 必须通过环境变量配置
    'charset': 'utf8mb4'
}

# 检查必要的数据库配置
missing_config = []
if not MYSQL_CONFIG['database']:
    missing_config.append('DB_NAME')
if not MYSQL_CONFIG['user']:
    missing_config.append('DB_USER')
if not MYSQL_CONFIG['password']:
    missing_config.append('DB_PASSWORD')

if missing_config:
    print("\n⚠️  警告：数据库配置不完整！")
    print(f"缺少以下配置项: {', '.join(missing_config)}")
    print("请在 .env 文件中设置这些环境变量，或参考 env.example 文件")
    print("示例：")
    print("  DB_HOST=localhost")
    print("  DB_PORT=3306")
    print("  DB_NAME=autovideo")
    print("  DB_USER=root")
    print("  DB_PASSWORD=your_password")
    print()

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
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

# 如果缺少必要的AI配置，给出提示
if not DEEPSEEK_API_KEY:
    print("\n⚠️  警告：DeepSeek API密钥未配置！")
    print("请设置环境变量 DEEPSEEK_API_KEY")
    print("示例：set DEEPSEEK_API_KEY=your_api_key\n")

# =========================
# TTS (Baidu Intelligent Cloud)
# =========================
BAIDU_APP_ID = os.environ.get("BAIDU_APP_ID", "")
BAIDU_API_KEY = os.environ.get("BAIDU_API_KEY", "")
BAIDU_SECRET_KEY = os.environ.get("BAIDU_SECRET_KEY", "")
# 客户端唯一标识：可用机器名/UUID，留空则后端自动生成
BAIDU_CUID = os.environ.get("BAIDU_CUID", "")

# 如果缺少必要的百度TTS配置，给出提示
if not BAIDU_APP_ID or not BAIDU_API_KEY or not BAIDU_SECRET_KEY:
    print("\n⚠️  警告：百度TTS配置不完整！")
    print("请设置环境变量：BAIDU_APP_ID, BAIDU_API_KEY, BAIDU_SECRET_KEY")
    print("示例：")
    print("  set BAIDU_APP_ID=your_app_id")
    print("  set BAIDU_API_KEY=your_api_key")
    print("  set BAIDU_SECRET_KEY=your_secret_key\n")

# =========================
# FFmpeg 配置
# =========================
# FFmpeg 可执行文件路径（如果不在系统 PATH 中）
# 可以通过环境变量 FFMPEG_PATH 设置
# Windows: set FFMPEG_PATH=D:\ffmpeg\bin\ffmpeg.exe
# Linux/Mac: export FFMPEG_PATH=/usr/bin/ffmpeg
# 如果未设置，将尝试使用系统 PATH 中的 ffmpeg
FFMPEG_PATH = os.environ.get("FFMPEG_PATH", "")


# =========================
# SMTP 邮件配置
# =========================
# SMTP 服务器配置
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.qq.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", "")
SMTP_USE_SSL = os.environ.get("SMTP_USE_SSL", "true").lower() == "true"
SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "false").lower() == "true"

# 如果缺少必要的SMTP配置，给出提示
if not SMTP_HOST or not SMTP_USER or not SMTP_PASSWORD or not SMTP_FROM:
    print("\n⚠️  警告：SMTP邮件配置不完整！")
    print("请设置环境变量或修改config.py中的SMTP配置")
    print("示例：")
    print("  set SMTP_HOST=smtp.qq.com")
    print("  set SMTP_PORT=465")
    print("  set SMTP_USER=your_qq_email@qq.com")
    print("  set SMTP_PASSWORD=your_qq_authorization_code")
    print("  set SMTP_FROM=your_qq_email@qq.com")
    print("  set SMTP_USE_SSL=true")
    print("  set SMTP_USE_TLS=false")
    print()

# =========================
# 腾讯云COS配置
# =========================
# 腾讯云COS配置
COS_SECRET_ID = os.environ.get("COS_SECRET_ID", "")
COS_SECRET_KEY = os.environ.get("COS_SECRET_KEY", "")
COS_REGION = os.environ.get("COS_REGION", "ap-nanjing")  # 默认南京
COS_BUCKET = os.environ.get("COS_BUCKET", "")  # 存储桶名称
COS_DOMAIN = os.environ.get("COS_DOMAIN", "")  # 自定义域名（可选），如：https://your-bucket.cos.ap-nanjing.myqcloud.com
COS_SCHEME = os.environ.get("COS_SCHEME", "https")  # 协议，https或http

# 如果缺少必要的COS配置，给出提示
if not COS_SECRET_ID or not COS_SECRET_KEY or not COS_BUCKET:
    print("\n⚠️  警告：腾讯云COS配置不完整！")
    print("请设置环境变量或修改config.py中的COS配置")
    print("示例：")
    print("  set COS_SECRET_ID=your_secret_id")
    print("  set COS_SECRET_KEY=your_secret_key")
    print("  set COS_REGION=ap-nanjing")
    print("  set COS_BUCKET=your-bucket-name")
    print("  set COS_DOMAIN=https://your-bucket.cos.ap-nanjing.myqcloud.com  # 可选")
    print()