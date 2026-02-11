"""
数据库迁移脚本：为video_library和video_edit_tasks表添加user_id字段

此脚本会：
1. 为video_library表添加user_id字段
2. 为video_edit_tasks表添加user_id字段
3. 对于现有数据，需要手动处理（删除或分配给默认用户）

注意：运行此脚本前，请备份数据库！
"""
import os
import sys

# 添加当前目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from sqlalchemy import text, inspect
from db import engine, get_db
from models import Base

def check_column_exists(table_name, column_name):
    """检查列是否存在"""
    try:
        with get_db() as db:
            inspector = inspect(engine)
            columns = [col['name'] for col in inspector.get_columns(table_name)]
            return column_name in columns
    except Exception as e:
        print(f"检查列时出错: {e}")
        return False

def migrate_video_library():
    """迁移video_library表"""
    print("\n" + "=" * 60)
    print("迁移 video_library 表...")
    print("=" * 60)
    
    try:
        # 检查表是否存在
        inspector = inspect(engine)
        if 'video_library' not in inspector.get_table_names():
            print("⚠️  video_library 表不存在，跳过迁移")
            return True
        
        # 检查user_id列是否已存在
        if check_column_exists('video_library', 'user_id'):
            print("✓ user_id 列已存在，跳过")
            return True
        
        # 检查是否有现有数据
        with get_db() as db:
            result = db.execute(text("SELECT COUNT(*) as count FROM video_library"))
            count = result.fetchone()[0]
            
            if count > 0:
                print(f"\n⚠️  警告：video_library 表中有 {count} 条现有数据")
                print("   这些数据没有关联的用户ID。")
                print("   选项：")
                print("   1. 删除所有现有数据（推荐，因为无法确定数据归属）")
                print("   2. 手动为每条数据分配用户ID")
                print("   3. 取消迁移")
                
                choice = input("\n请选择操作 (1/2/3，默认1): ").strip() or "1"
                
                if choice == "1":
                    # 删除现有数据
                    db.execute(text("DELETE FROM video_library"))
                    db.commit()
                    print("✓ 已删除所有现有数据")
                elif choice == "2":
                    # 需要手动处理
                    print("\n⚠️  请手动为现有数据分配用户ID后再继续")
                    print("   可以使用以下SQL语句：")
                    print("   UPDATE video_library SET user_id = <用户ID> WHERE id = <视频ID>;")
                    input("   完成后按回车继续...")
                else:
                    print("❌ 迁移已取消")
                    return False
        
        # 添加user_id列
        print("\n正在添加 user_id 列...")
        with get_db() as db:
            # 先添加列（允许NULL，因为可能有现有数据）
            db.execute(text("""
                ALTER TABLE video_library 
                ADD COLUMN user_id INT NULL
            """))
            
            # 添加外键约束
            db.execute(text("""
                ALTER TABLE video_library 
                ADD CONSTRAINT fk_video_library_user_id 
                FOREIGN KEY (user_id) REFERENCES users(id)
            """))
            
            # 添加索引
            db.execute(text("""
                CREATE INDEX idx_video_library_user_id 
                ON video_library(user_id)
            """))
            
            # 将列设置为NOT NULL（如果表中没有数据）
            try:
                db.execute(text("""
                    ALTER TABLE video_library 
                    MODIFY COLUMN user_id INT NOT NULL
                """))
            except Exception as e:
                print(f"⚠️  无法将user_id设置为NOT NULL（可能因为现有数据）: {e}")
                print("   请手动处理现有数据后，运行以下SQL：")
                print("   ALTER TABLE video_library MODIFY COLUMN user_id INT NOT NULL;")
            
            db.commit()
        
        print("✓ video_library 表迁移完成")
        return True
        
    except Exception as e:
        print(f"❌ 迁移 video_library 表时出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def migrate_video_edit_tasks():
    """迁移video_edit_tasks表"""
    print("\n" + "=" * 60)
    print("迁移 video_edit_tasks 表...")
    print("=" * 60)
    
    try:
        # 检查表是否存在
        inspector = inspect(engine)
        if 'video_edit_tasks' not in inspector.get_table_names():
            print("⚠️  video_edit_tasks 表不存在，跳过迁移")
            return True
        
        # 检查user_id列是否已存在
        if check_column_exists('video_edit_tasks', 'user_id'):
            print("✓ user_id 列已存在，跳过")
            return True
        
        # 检查是否有现有数据
        with get_db() as db:
            result = db.execute(text("SELECT COUNT(*) as count FROM video_edit_tasks"))
            count = result.fetchone()[0]
            
            if count > 0:
                print(f"\n⚠️  警告：video_edit_tasks 表中有 {count} 条现有数据")
                print("   这些数据没有关联的用户ID。")
                print("   选项：")
                print("   1. 删除所有现有数据（推荐）")
                print("   2. 手动为每条数据分配用户ID")
                print("   3. 取消迁移")
                
                choice = input("\n请选择操作 (1/2/3，默认1): ").strip() or "1"
                
                if choice == "1":
                    # 删除现有数据
                    db.execute(text("DELETE FROM video_edit_tasks"))
                    db.commit()
                    print("✓ 已删除所有现有数据")
                elif choice == "2":
                    # 需要手动处理
                    print("\n⚠️  请手动为现有数据分配用户ID后再继续")
                    print("   可以使用以下SQL语句：")
                    print("   UPDATE video_edit_tasks SET user_id = <用户ID> WHERE id = <任务ID>;")
                    input("   完成后按回车继续...")
                else:
                    print("❌ 迁移已取消")
                    return False
        
        # 添加user_id列
        print("\n正在添加 user_id 列...")
        with get_db() as db:
            # 先添加列（允许NULL，因为可能有现有数据）
            db.execute(text("""
                ALTER TABLE video_edit_tasks 
                ADD COLUMN user_id INT NULL
            """))
            
            # 添加外键约束
            db.execute(text("""
                ALTER TABLE video_edit_tasks 
                ADD CONSTRAINT fk_video_edit_tasks_user_id 
                FOREIGN KEY (user_id) REFERENCES users(id)
            """))
            
            # 添加索引
            db.execute(text("""
                CREATE INDEX idx_video_edit_tasks_user_id 
                ON video_edit_tasks(user_id)
            """))
            
            # 将列设置为NOT NULL（如果表中没有数据）
            try:
                db.execute(text("""
                    ALTER TABLE video_edit_tasks 
                    MODIFY COLUMN user_id INT NOT NULL
                """))
            except Exception as e:
                print(f"⚠️  无法将user_id设置为NOT NULL（可能因为现有数据）: {e}")
                print("   请手动处理现有数据后，运行以下SQL：")
                print("   ALTER TABLE video_edit_tasks MODIFY COLUMN user_id INT NOT NULL;")
            
            db.commit()
        
        print("✓ video_edit_tasks 表迁移完成")
        return True
        
    except Exception as e:
        print(f"❌ 迁移 video_edit_tasks 表时出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("数据库迁移：添加 user_id 字段")
    print("=" * 60)
    print("\n此脚本将为以下表添加 user_id 字段：")
    print("  1. video_library")
    print("  2. video_edit_tasks")
    print("\n⚠️  重要提示：")
    print("  - 运行前请备份数据库！")
    print("  - 现有数据需要手动处理（删除或分配用户ID）")
    print("  - 此操作不可逆！")
    
    confirm = input("\n是否继续？(yes/no，默认no): ").strip().lower()
    if confirm != 'yes':
        print("❌ 迁移已取消")
        return
    
    # 测试数据库连接
    try:
        with get_db() as db:
            db.execute(text('SELECT 1'))
        print("\n✓ 数据库连接成功")
    except Exception as e:
        print(f"\n❌ 数据库连接失败: {e}")
        sys.exit(1)
    
    # 执行迁移
    success = True
    success = migrate_video_library() and success
    success = migrate_video_edit_tasks() and success
    
    if success:
        print("\n" + "=" * 60)
        print("✓ 迁移完成！")
        print("=" * 60)
        print("\n现在所有视频和任务都会关联到创建它们的用户。")
        print("每个用户只能看到自己的视频和任务，确保数据隔离。\n")
    else:
        print("\n" + "=" * 60)
        print("❌ 迁移过程中出现错误，请检查上面的错误信息")
        print("=" * 60 + "\n")
        sys.exit(1)

if __name__ == '__main__':
    main()

