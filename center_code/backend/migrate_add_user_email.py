"""
数据库迁移脚本：为 users 表添加 email 和 is_verified 字段

如果数据库中的 users 表缺少这些字段，运行此脚本添加。
"""
import os
import sys

# 添加当前目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from sqlalchemy import text, inspect
from db import engine, get_db
from config import get_db_config

def check_column_exists(table_name, column_name):
    """检查表中是否存在指定列"""
    with get_db() as db:
        result = db.execute(text(f"""
            SELECT COUNT(*) as count
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = '{table_name}'
            AND COLUMN_NAME = '{column_name}'
        """))
        row = result.fetchone()
        return row[0] > 0 if row else False

def migrate_users_table():
    """迁移 users 表，添加缺失的字段"""
    print("=" * 60)
    print("数据库迁移：添加 users 表缺失字段")
    print("=" * 60)
    print()
    
    config = get_db_config()
    print(f"数据库: {config['database']}")
    print(f"表: users")
    print()
    
    with get_db() as db:
        try:
            # 检查 email 字段
            if not check_column_exists('users', 'email'):
                print("添加 email 字段...")
                db.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN email VARCHAR(255) NULL AFTER username
                """))
                print("✓ email 字段已添加")
            else:
                print("✓ email 字段已存在")
            
            # 检查 is_verified 字段
            if not check_column_exists('users', 'is_verified'):
                print("添加 is_verified 字段...")
                db.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN is_verified BOOLEAN DEFAULT FALSE AFTER avatar_url
                """))
                print("✓ is_verified 字段已添加")
            else:
                print("✓ is_verified 字段已存在")
            
            # 为现有用户设置默认 email（如果 email 为空）
            print()
            print("更新现有用户的 email...")
            result = db.execute(text("""
                SELECT id, username FROM users WHERE email IS NULL OR email = ''
            """))
            users_without_email = result.fetchall()
            
            if users_without_email:
                print(f"找到 {len(users_without_email)} 个没有 email 的用户")
                for user_id, username in users_without_email:
                    # 为没有 email 的用户生成一个默认 email
                    default_email = f"{username}@autovideo.local"
                    db.execute(text("""
                        UPDATE users 
                        SET email = :email 
                        WHERE id = :user_id
                    """), {'email': default_email, 'user_id': user_id})
                    print(f"  用户 {username} (ID: {user_id}) 已设置默认 email: {default_email}")
            else:
                print("所有用户都已设置 email")
            
            # 设置 email 为 NOT NULL（在确保所有用户都有 email 后）
            print()
            print("设置 email 字段为 NOT NULL...")
            try:
                db.execute(text("""
                    ALTER TABLE users 
                    MODIFY COLUMN email VARCHAR(255) NOT NULL
                """))
                print("✓ email 字段已设置为 NOT NULL")
            except Exception as e:
                print(f"⚠️  设置 email 为 NOT NULL 失败: {e}")
                print("   可能还有用户的 email 为空，请先处理")
            
            # 添加唯一索引（如果不存在）
            print()
            print("检查 email 唯一索引...")
            result = db.execute(text("""
                SELECT COUNT(*) as count
                FROM information_schema.STATISTICS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'users'
                AND COLUMN_NAME = 'email'
                AND NON_UNIQUE = 0
            """))
            has_unique_index = result.fetchone()[0] > 0
            
            if not has_unique_index:
                print("添加 email 唯一索引...")
                try:
                    db.execute(text("""
                        CREATE UNIQUE INDEX idx_users_email ON users(email)
                    """))
                    print("✓ email 唯一索引已添加")
                except Exception as e:
                    print(f"⚠️  添加 email 唯一索引失败: {e}")
                    print("   可能已有重复的 email，请先处理")
            else:
                print("✓ email 唯一索引已存在")
            
            # 提交更改
            db.commit()
            print()
            print("=" * 60)
            print("✓ 迁移完成！")
            print("=" * 60)
            
        except Exception as e:
            db.rollback()
            print()
            print("=" * 60)
            print("❌ 迁移失败！")
            print("=" * 60)
            print(f"错误: {e}")
            import traceback
            traceback.print_exc()
            raise

if __name__ == '__main__':
    try:
        migrate_users_table()
    except Exception as e:
        print(f"\n迁移失败: {e}")
        sys.exit(1)

