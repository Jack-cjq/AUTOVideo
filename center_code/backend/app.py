"""
抖音中心管理平台 - Flask应用主文件
模块化设计，支持 MySQL 数据库
"""

import os
import sys

# 添加当前目录到 Python 路径，确保可以导入模块
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from flask import Flask, send_from_directory
from flask_cors import CORS

from models import Base
from db import engine

# 导入所有 Blueprint
from blueprints.auth import auth_bp
from blueprints.devices import devices_bp
from blueprints.accounts import accounts_bp
from blueprints.video import video_bp
from blueprints.chat import chat_bp
from blueprints.listen import listen_bp
from blueprints.social import social_bp
from blueprints.messages import messages_bp
from blueprints.stats import stats_bp
from blueprints.login import login_bp
from blueprints.publish_plans import publish_plans_bp
from blueprints.merchants import merchants_bp
from blueprints.video_library import video_library_bp
from blueprints.data_center import data_center_bp
from blueprints.video_editor import video_editor_bp
from blueprints.publish import publish_bp

app = Flask(__name__, static_folder='../frontend/dist', static_url_path='')
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')

# 配置 session
app.config['SESSION_COOKIE_NAME'] = 'session'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # 允许跨站请求携带 cookie
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24小时（秒）

# 配置 CORS，允许携带凭证
# 开发环境允许所有 localhost 和 127.0.0.1 的端口
cors_origins = [
    'http://localhost:3000', 'http://localhost:3001', 'http://localhost:5173',
    'http://127.0.0.1:3000', 'http://127.0.0.1:3001', 'http://127.0.0.1:5173'
]
# 如果环境变量设置了允许的源，则使用环境变量
if os.getenv('CORS_ORIGINS'):
    cors_origins = os.getenv('CORS_ORIGINS').split(',')

CORS(app, 
     supports_credentials=True,
     origins=cors_origins,
     allow_headers=['Content-Type', 'Authorization'],
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])

# 注册所有 Blueprint
app.register_blueprint(auth_bp)
app.register_blueprint(devices_bp)
app.register_blueprint(accounts_bp)
app.register_blueprint(video_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(listen_bp)
app.register_blueprint(social_bp)
app.register_blueprint(messages_bp)
app.register_blueprint(stats_bp)
app.register_blueprint(login_bp)
app.register_blueprint(publish_plans_bp)
app.register_blueprint(merchants_bp)
app.register_blueprint(video_library_bp)
app.register_blueprint(data_center_bp)
app.register_blueprint(video_editor_bp)
app.register_blueprint(publish_bp)


def init_db():
    """初始化数据库表"""
    try:
        # 测试数据库连接
        from db import get_db
        from sqlalchemy import text
        with get_db() as db:
            db.execute(text('SELECT 1'))
        print("✓ 数据库连接成功")
        
        # 创建表
        Base.metadata.create_all(engine)
        print("✓ 数据库表初始化成功")
    except Exception as e:
        error_msg = str(e)
        if "Access denied" in error_msg or "1045" in error_msg:
            print("\n" + "="*60)
            print("❌ 数据库连接失败：用户名或密码错误")
            print("="*60)
            print("\n请配置 MySQL 数据库连接信息：")
            print("\n方法1：设置环境变量")
            print("  export DB_HOST=localhost")
            print("  export DB_PORT=3306")
            print("  export DB_NAME=autovideo")
            print("  export DB_USER=root")
            print("  export DB_PASSWORD=your_password")
            print("\n方法2：直接修改 backend/config.py 文件")
            print("  修改 MYSQL_CONFIG 字典中的配置项")
            print("\n方法3：创建数据库（如果还没有）")
            print("  mysql -u root -p")
            print("  CREATE DATABASE autovideo CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            print("="*60 + "\n")
        elif "Unknown database" in error_msg or "1049" in error_msg:
            print("\n" + "="*60)
            print("❌ 数据库不存在")
            print("="*60)
            print("\n请先创建数据库：")
            print("  mysql -u root -p")
            print("  CREATE DATABASE autovideo CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            print("="*60 + "\n")
        else:
            print(f"\n❌ 数据库连接失败: {error_msg}\n")
        raise


# ==================== 前端页面路由 ====================

@app.route('/')
def index():
    """提供前端页面"""
    return send_from_directory('../frontend/dist', 'index.html')


@app.route('/login-helper')
def login_helper():
    """提供登录助手页面"""
    return send_from_directory('../frontend/dist', 'index.html')


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    try:
        from db import get_db
        from sqlalchemy import text
        # 测试数据库连接
        with get_db() as db:
            db.execute(text('SELECT 1'))
        
        return {
            'status': 'healthy',
            'database': 'mysql',
            'message': 'Service is running'
        }, 200
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e)
        }, 500


def is_port_available(port):
    """检查端口是否可用"""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('0.0.0.0', port))
            return True
        except OSError:
            return False

if __name__ == '__main__':
    # 初始化数据库
    init_db()
    
    # 从环境变量或命令行参数获取端口，默认5000
    port = int(os.getenv('PORT', 5000))
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"警告: 无效的端口号 '{sys.argv[1]}', 使用默认端口 {port}")
    
    # 检查端口是否可用
    original_port = port
    if not is_port_available(port):
        print(f"⚠️  警告: 端口 {port} 已被占用，尝试其他端口...")
        # 尝试 5001-5010
        for alt_port in range(5001, 5010):
            if is_port_available(alt_port):
                port = alt_port
                print(f"✓ 使用端口 {port} 启动服务器")
                break
        else:
            print(f"❌ 错误: 无法找到可用端口（尝试了 {original_port}-5009）")
            print("\n解决方案：")
            print(f"  1. 关闭占用端口 {original_port} 的程序")
            print(f"  2. 使用其他端口: python app.py <端口号>")
            print(f"  3. 设置环境变量: $env:PORT=8080")
            sys.exit(1)
    
    print(f"\n正在启动服务器...")
    print(f"访问地址: http://localhost:{port}")
    print(f"数据库类型: MySQL")
    print(f"按 Ctrl+C 停止服务器\n")
    
    try:
        app.run(
            debug=True,
            host='0.0.0.0',
            port=port
        )
    except OSError as e:
        if "以一种访问权限不允许的方式做了一个访问套接字的尝试" in str(e) or "permission denied" in str(e).lower():
            print(f"\n❌ 错误: 端口 {port} 访问被拒绝")
            print("可能的原因：")
            print("  1. 端口被其他程序占用")
            print("  2. 需要管理员权限")
            print("  3. 防火墙阻止")
            print("\n解决方案：")
            print(f"  1. 关闭占用端口 {port} 的程序")
            print(f"  2. 使用其他端口: python app.py <端口号>")
            print(f"  3. 以管理员身份运行")
        else:
            print(f"\n❌ 启动服务器时出错: {e}")
        sys.exit(1)
