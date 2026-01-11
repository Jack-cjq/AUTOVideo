"""
创建数据库并初始化表结构
"""
import os
import sys

# 添加当前目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import pymysql
from config import get_db_config

def create_database():
    """创建数据库（如果不存在）"""
    print("=" * 60)
    print("创建数据库...")
    print("=" * 60)
    
    config = get_db_config()
    
    # 先连接到 MySQL 服务器（不指定数据库）
    try:
        print(f"\n正在连接到 MySQL 服务器 ({config['host']}:{config['port']})...")
        connection = pymysql.connect(
            host=config['host'],
            port=config['port'],
            user=config['user'],
            password=config['password'],
            charset=config['charset']
        )
        print("✓ MySQL 服务器连接成功！")
        
        # 检查数据库是否存在
        with connection.cursor() as cursor:
            cursor.execute("SHOW DATABASES LIKE %s", (config['database'],))
            result = cursor.fetchone()
            
            if result:
                print(f"\n数据库 '{config['database']}' 已存在")
                connection.close()
                return True
            else:
                # 创建数据库
                print(f"\n正在创建数据库 '{config['database']}'...")
                cursor.execute(
                    f"CREATE DATABASE {config['database']} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
                connection.commit()
                print(f"✓ 数据库 '{config['database']}' 创建成功！")
                connection.close()
                return True
                
    except pymysql.Error as e:
        print(f"\n❌ 创建数据库失败: {e}")
        if "Access denied" in str(e) or e.args[0] == 1045:
            print("\n可能的原因：用户名或密码错误")
            print("请检查 config.py 中的配置")
        return False
    except Exception as e:
        print(f"\n❌ 连接失败: {e}")
        return False

def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("数据库初始化工具")
    print("=" * 60 + "\n")
    
    # 创建数据库
    if not create_database():
        print("\n请先解决数据库连接问题。")
        sys.exit(1)
    
    # 现在运行测试和初始化脚本
    print("\n" + "=" * 60)
    print("现在运行数据库表初始化...")
    print("=" * 60 + "\n")
    
    # 导入并运行测试脚本
    from test_db import test_connection, init_tables, check_tables
    from init_user import init_default_user
    
    if test_connection():
        check_tables()
        if init_tables():
            # 初始化默认用户
            if init_default_user():
                print("\n" + "=" * 60)
                print("✓ 数据库初始化完成！")
                print("=" * 60)
                print("\n默认账号信息：")
                print("  用户名: hbut")
                print("  密码: dydy?123")
                print("\n现在可以运行 'python app.py' 启动应用了。\n")
            else:
                print("\n⚠️  表初始化成功，但用户初始化失败")
                print("可以手动运行 'python init_user.py' 创建用户\n")
        else:
            print("\n❌ 表初始化失败")
            sys.exit(1)
    else:
        print("\n❌ 数据库连接测试失败")
        sys.exit(1)

if __name__ == '__main__':
    main()

