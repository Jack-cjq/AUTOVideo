"""
数据库连接管理
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from config import get_db_url

# 创建数据库引擎
# 配置说明：
# - pool_pre_ping=True: 在使用连接前检查连接是否有效，自动重连断开的连接
# - pool_recycle=3600: 连接池中的连接在1小时后回收，避免长时间连接超时
# - connect_args: 增加连接超时和重试参数，确保启动时能正确连接数据库
engine = create_engine(
    get_db_url(),
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # 自动检测并重连断开的连接
    pool_recycle=3600,  # 1小时后回收连接，避免长时间连接超时
    echo=False,
    connect_args={
        'connect_timeout': 10,  # 连接超时时间（秒）
        'read_timeout': 10,    # 读取超时时间（秒）
        'write_timeout': 10,   # 写入超时时间（秒）
    } if 'mysql' in get_db_url() else {}  # 仅对MySQL连接添加超时参数
)

SessionLocal = scoped_session(sessionmaker(bind=engine, autocommit=False, autoflush=False))


@contextmanager
def get_db():
    """获取数据库会话"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

