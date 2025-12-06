"""
测试数据库连接并初始化数据库表结构
"""
import os
import sys

# 添加当前目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from config import get_db_config, get_db_url
from models import Base
from db import engine, get_db
from sqlalchemy import text, inspect

def test_connection():
    """测试数据库连接"""
    print("=" * 60)
    print("正在测试数据库连接...")
    print("=" * 60)
    
    config = get_db_config()
    print(f"\n数据库配置：")
    print(f"  主机: {config['host']}")
    print(f"  端口: {config['port']}")
    print(f"  数据库: {config['database']}")
    print(f"  用户: {config['user']}")
    print(f"  密码: {'*' * len(config['password']) if config['password'] else '(未设置)'}")
    print()
    
    try:
        # 测试连接
        with get_db() as db:
            result = db.execute(text('SELECT 1'))
            print("✓ 数据库连接成功！")
            return True
    except Exception as e:
        error_msg = str(e)
        print("❌ 数据库连接失败！")
        print(f"\n错误信息: {error_msg}\n")
        
        if "Access denied" in error_msg or "1045" in error_msg:
            print("可能的原因：")
            print("  1. 用户名或密码错误")
            print("  2. MySQL 服务未启动")
            print("  3. 用户没有访问权限")
            print("\n解决方案：")
            print("  1. 检查 config.py 中的用户名和密码")
            print("  2. 确认 MySQL 服务正在运行")
            print("  3. 确认用户有足够的权限")
        elif "Unknown database" in error_msg or "1049" in error_msg:
            print("可能的原因：数据库不存在")
            print("\n解决方案：")
            print("  请先创建数据库：")
            print("  mysql -u root -p")
            print(f"  CREATE DATABASE {config['database']} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        elif "Can't connect" in error_msg or "2003" in error_msg:
            print("可能的原因：")
            print("  1. MySQL 服务未启动")
            print("  2. 主机地址或端口错误")
            print("  3. 防火墙阻止连接")
            print("\n解决方案：")
            print("  1. 启动 MySQL 服务")
            print("  2. 检查 config.py 中的主机和端口配置")
        else:
            print("请检查错误信息并解决相应问题")
        
        print("\n" + "=" * 60)
        return False

def check_tables():
    """检查已存在的表"""
    print("\n" + "=" * 60)
    print("检查数据库表...")
    print("=" * 60)
    
    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        if existing_tables:
            print(f"\n已存在的表 ({len(existing_tables)} 个):")
            for table in existing_tables:
                print(f"  - {table}")
        else:
            print("\n数据库中没有表")
        
        return existing_tables
    except Exception as e:
        print(f"❌ 检查表时出错: {e}")
        return []

def init_tables():
    """初始化数据库表"""
    print("\n" + "=" * 60)
    print("初始化数据库表结构...")
    print("=" * 60)
    
    try:
        # 获取所有模型类
        from models import (
            User, Device, Account, VideoTask, ChatTask, ListenTask, Message,
            PublishPlan, PlanVideo, Merchant, VideoLibrary, AccountStats
        )
        
        tables_to_create = [
            ('users', User),
            ('devices', Device),
            ('accounts', Account),
            ('video_tasks', VideoTask),
            ('chat_tasks', ChatTask),
            ('listen_tasks', ListenTask),
            ('messages', Message),
            ('publish_plans', PublishPlan),
            ('plan_videos', PlanVideo),
            ('merchants', Merchant),
            ('video_library', VideoLibrary),
            ('account_stats', AccountStats)
        ]
        
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        print(f"\n需要创建的表:")
        for table_name, model_class in tables_to_create:
            if table_name in existing_tables:
                print(f"  ✓ {table_name} (已存在)")
            else:
                print(f"  + {table_name} (将创建)")
        
        # 创建所有表
        Base.metadata.create_all(engine)
        
        # 再次检查
        inspector = inspect(engine)
        final_tables = inspector.get_table_names()
        
        print(f"\n✓ 数据库表初始化完成！")
        print(f"\n当前数据库中的表 ({len(final_tables)} 个):")
        for table in final_tables:
            print(f"  - {table}")
        
        return True
    except Exception as e:
        print(f"\n❌ 初始化表时出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("数据库连接测试和初始化工具")
    print("=" * 60 + "\n")
    
    # 测试连接
    if not test_connection():
        print("\n请先解决数据库连接问题，然后重新运行此脚本。")
        sys.exit(1)
    
    # 检查现有表
    existing_tables = check_tables()
    
    # 初始化表
    if init_tables():
        print("\n" + "=" * 60)
        print("✓ 所有操作完成！数据库已准备就绪。")
        print("=" * 60 + "\n")
    else:
        print("\n" + "=" * 60)
        print("❌ 初始化失败，请检查错误信息。")
        print("=" * 60 + "\n")
        sys.exit(1)

if __name__ == '__main__':
    main()

