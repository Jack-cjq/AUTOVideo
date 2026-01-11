"""
数据库直接读取模块
用于 service_code 直接读取 center_code 的数据库，避免 API 认证问题
"""
import os
import sys
from pathlib import Path
from typing import Optional, Dict
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from utils.log import douyin_logger

# 尝试导入数据库配置
# 优先使用环境变量，如果不存在则尝试从 center_code 的 config 导入
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'database': os.getenv('DB_NAME', 'autovideo'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', '123456'),
    'charset': 'utf8mb4'
}

# 如果环境变量没有设置密码，尝试从 center_code 的 config 导入
if not os.getenv('DB_PASSWORD') or DB_CONFIG['password'] == '123456':
    try:
        # 尝试从 center_code 的 config 导入
        center_backend_path = Path(__file__).parent.parent.parent / "center_code" / "backend"
        if center_backend_path.exists():
            sys.path.insert(0, str(center_backend_path))
            try:
                from config import get_db_url, get_db_config
                DB_CONFIG = get_db_config()
                DB_URL = get_db_url()
                douyin_logger.info("Loaded database config from center_code/config.py")
            except ImportError as e:
                douyin_logger.warning(f"Failed to import from center_code/config.py: {e}, using environment variables")
                DB_URL = f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}?charset={DB_CONFIG['charset']}"
        else:
            DB_URL = f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}?charset={DB_CONFIG['charset']}"
    except Exception as e:
        douyin_logger.warning(f"Failed to load database config, using defaults: {e}")
        DB_URL = f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}?charset={DB_CONFIG['charset']}"
else:
    DB_URL = f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}?charset={DB_CONFIG['charset']}"

# 创建数据库引擎
_engine = None
_SessionLocal = None

def get_db_engine():
    """获取数据库引擎（单例模式）"""
    global _engine
    if _engine is None:
        try:
            _engine = create_engine(
                DB_URL,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False
            )
            douyin_logger.info(f"Database engine created: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
        except Exception as e:
            douyin_logger.error(f"Failed to create database engine: {e}")
            raise
    return _engine

def get_db_session():
    """获取数据库会话"""
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_db_engine()
        _SessionLocal = sessionmaker(bind=engine)
    return _SessionLocal()

def get_account_from_db(account_id: int) -> Optional[Dict]:
    """
    直接从数据库读取账号信息（包括cookies）
    
    Args:
        account_id: 账号ID
        
    Returns:
        Optional[Dict]: 账号信息字典，如果不存在则返回None
        格式：
        {
            'id': int,
            'device_id': int,
            'account_name': str,
            'platform': str,
            'login_status': str,
            'last_login_time': str or None,
            'cookies': str or None  # JSON字符串
        }
    """
    session = None
    try:
        session = get_db_session()
        
        # 直接执行 SQL 查询，避免导入 models
        query = text("""
            SELECT 
                id, 
                device_id, 
                account_name, 
                platform, 
                login_status, 
                last_login_time,
                cookies
            FROM accounts 
            WHERE id = :account_id
        """)
        
        result = session.execute(query, {'account_id': account_id})
        row = result.fetchone()
        
        if not row:
            douyin_logger.warning(f"Account {account_id} not found in database")
            return None
        
        # 转换为字典
        account_info = {
            'id': row[0],
            'device_id': row[1],
            'account_name': row[2],
            'platform': row[3],
            'login_status': row[4],
            'last_login_time': row[5].isoformat() if row[5] else None,
            'cookies': row[6]  # 已经是字符串格式
        }
        
        douyin_logger.info(f"Successfully retrieved account {account_id} from database")
        return account_info
        
    except Exception as e:
        douyin_logger.error(f"Error reading account {account_id} from database: {e}")
        return None
    finally:
        if session:
            session.close()

def get_account_by_device_id(device_id: str) -> Optional[Dict]:
    """
    根据 device_id 从数据库读取账号信息
    
    Args:
        device_id: 设备ID
        
    Returns:
        Optional[Dict]: 账号信息字典，如果不存在则返回None
    """
    session = None
    try:
        session = get_db_session()
        
        # 直接执行 SQL 查询
        query = text("""
            SELECT 
                id, 
                device_id, 
                account_name, 
                platform, 
                login_status, 
                last_login_time,
                cookies
            FROM accounts 
            WHERE device_id = :device_id
            LIMIT 1
        """)
        
        result = session.execute(query, {'device_id': device_id})
        row = result.fetchone()
        
        if not row:
            douyin_logger.warning(f"Account with device_id {device_id} not found in database")
            return None
        
        # 转换为字典
        account_info = {
            'id': row[0],
            'device_id': row[1],
            'account_name': row[2],
            'platform': row[3],
            'login_status': row[4],
            'last_login_time': row[5].isoformat() if row[5] else None,
            'cookies': row[6] if row[6] else None
        }
        
        douyin_logger.info(f"Successfully retrieved account {row[0]} (device_id: {device_id}) from database")
        return account_info
        
    except Exception as e:
        douyin_logger.error(f"Error reading account with device_id {device_id} from database: {e}")
        return None
    finally:
        if session:
            session.close()

