"""
数据库连接管理
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from config import get_db_url

# 创建数据库引擎
engine = create_engine(
    get_db_url(),
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=False
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

