"""
完整修复 users 表：根据模型定义自动添加所有缺失字段

此脚本会检查 User 模型定义，并自动添加所有缺失的字段。
"""
import os
import sys

# 添加当前目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from sqlalchemy import text, inspect
from db import get_db, engine
from config import get_db_config
from models import User

def get_model_columns():
    """获取 User 模型定义的所有列"""
    inspector = inspect(engine)
    try:
        # 尝试从数据库获取现有列信息
        columns = inspector.get_columns('users')
        return {col['name']: col for col in columns}
    except:
        return {}

def fix_users_table_complete():
    """完整修复 users 表，添加所有缺失字段"""
    print("=" * 60)
    print("完整修复 users 表")
    print("=" * 60)
    print()
    
    config = get_db_config()
    print(f"数据库: {config['database']}")
    print()
    
    # 获取模型定义的所有字段
    model_columns = {
        'id': {'type': 'INTEGER', 'primary_key': True, 'autoincrement': True},
        'username': {'type': 'VARCHAR(100)', 'unique': True, 'nullable': False},
        'email': {'type': 'VARCHAR(255)', 'unique': True, 'nullable': False},
        'password_hash': {'type': 'VARCHAR(255)', 'nullable': False},
        'avatar_url': {'type': 'VARCHAR(500)', 'nullable': True},
        'is_verified': {'type': 'BOOLEAN', 'default': 'FALSE', 'nullable': True},
        'created_at': {'type': 'DATETIME', 'default': 'CURRENT_TIMESTAMP', 'nullable': True},
        'updated_at': {'type': 'DATETIME', 'default': 'CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP', 'nullable': True},
    }
    
    with get_db() as db:
        try:
            # 检查表是否存在
            result = db.execute(text("""
                SELECT COUNT(*) as count
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'users'
            """))
            if result.fetchone()[0] == 0:
                print("❌ users 表不存在，请先运行 init_database.py")
                return False
            
            # 获取现有列
            result = db.execute(text("""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'users'
                ORDER BY ORDINAL_POSITION
            """))
            existing_columns = {row[0]: {'type': row[1], 'nullable': row[2], 'default': row[3]} 
                              for row in result.fetchall()}
            
            print(f"现有列 ({len(existing_columns)} 个):")
            for col_name in sorted(existing_columns.keys()):
                print(f"  - {col_name}")
            print()
            
            # 检查并添加缺失的字段
            missing_columns = []
            for col_name, col_def in model_columns.items():
                if col_name not in existing_columns:
                    missing_columns.append((col_name, col_def))
            
            if not missing_columns:
                print("✓ 所有字段都已存在，无需修复")
                return True
            
            print(f"发现 {len(missing_columns)} 个缺失字段，开始添加...")
            print()
            
            # 添加缺失字段
            for col_name, col_def in missing_columns:
                if col_name == 'id':
                    continue  # id 字段应该已存在
                
                print(f"添加 {col_name} 字段...")
                
                # 构建 ALTER TABLE 语句
                col_type = col_def['type']
                nullable = 'NULL' if col_def.get('nullable', True) else 'NOT NULL'
                default = ''
                if 'default' in col_def:
                    default_val = col_def['default']
                    if default_val == 'CURRENT_TIMESTAMP':
                        default = 'DEFAULT CURRENT_TIMESTAMP'
                    elif default_val == 'FALSE':
                        default = 'DEFAULT FALSE'
                    elif default_val:
                        default = f"DEFAULT '{default_val}'"
                
                # 确定字段位置
                after_clause = ''
                if col_name == 'email':
                    after_clause = 'AFTER username'
                elif col_name == 'avatar_url':
                    after_clause = 'AFTER password_hash'
                elif col_name == 'is_verified':
                    after_clause = 'AFTER avatar_url'
                elif col_name == 'created_at':
                    after_clause = 'AFTER is_verified'
                elif col_name == 'updated_at':
                    after_clause = 'AFTER created_at'
                
                alter_sql = f"""
                    ALTER TABLE users 
                    ADD COLUMN {col_name} {col_type} {nullable} {default} {after_clause}
                """
                
                try:
                    db.execute(text(alter_sql.strip()))
                    print(f"  ✓ {col_name} 字段已添加")
                except Exception as e:
                    print(f"  ⚠️  添加 {col_name} 字段失败: {e}")
            
            # 特殊处理 email 字段
            if 'email' in [col[0] for col in missing_columns]:
                print()
                print("处理 email 字段...")
                
                # 为现有用户设置默认 email
                result = db.execute(text("""
                    SELECT id, username FROM users WHERE email IS NULL OR email = ''
                """))
                users = result.fetchall()
                if users:
                    print(f"为 {len(users)} 个用户设置默认 email...")
                    for user_id, username in users:
                        default_email = f"{username}@autovideo.local"
                        db.execute(text("""
                            UPDATE users SET email = :email WHERE id = :user_id
                        """), {'email': default_email, 'user_id': user_id})
                    print("✓ 默认 email 已设置")
                
                # 设置 email 为 NOT NULL
                try:
                    db.execute(text("""
                        ALTER TABLE users 
                        MODIFY COLUMN email VARCHAR(255) NOT NULL
                    """))
                    print("✓ email 字段已设置为 NOT NULL")
                except Exception as e:
                    print(f"⚠️  设置 email 为 NOT NULL 失败: {e}")
                
                # 添加唯一索引
                try:
                    db.execute(text("""
                        CREATE UNIQUE INDEX idx_users_email ON users(email)
                    """))
                    print("✓ email 唯一索引已添加")
                except Exception as e:
                    print(f"⚠️  添加 email 唯一索引失败（可能已存在）: {e}")
            
            # 提交更改
            db.commit()
            print()
            print("=" * 60)
            print("✓ users 表修复完成！")
            print("=" * 60)
            
            # 验证修复结果
            print()
            print("验证修复结果...")
            result = db.execute(text("""
                SELECT COLUMN_NAME 
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'users'
                ORDER BY ORDINAL_POSITION
            """))
            final_columns = {row[0] for row in result.fetchall()}
            
            required_columns = set(model_columns.keys())
            still_missing = required_columns - final_columns
            
            if still_missing:
                print(f"⚠️  仍有缺失字段: {', '.join(still_missing)}")
                return False
            else:
                print("✓ 所有必需字段都已存在")
                return True
            
        except Exception as e:
            db.rollback()
            print()
            print("=" * 60)
            print("❌ 修复失败！")
            print("=" * 60)
            print(f"错误: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    try:
        if fix_users_table_complete():
            print("\n✅ 修复成功！现在可以重新尝试登录了。")
        else:
            print("\n❌ 修复失败，请检查错误信息。")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

