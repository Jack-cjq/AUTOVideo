"""
初始化默认用户
"""
import sys
import os

# 添加当前目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from models import User, Base
from db import engine
from config import get_db_config

def init_default_user():
    """初始化默认用户"""
    print("=" * 60)
    print("初始化默认用户...")
    print("=" * 60)
    
    try:
        # 确保表已创建
        Base.metadata.create_all(engine)
        
        from db import get_db
        with get_db() as db:
            # 检查是否已存在用户
            existing_user = db.query(User).filter(User.username == 'hbut').first()
            
            if existing_user:
                print(f"\n用户 'hbut' 已存在，跳过创建")
                return True
            
            # 创建默认用户
            default_user = User(username='hbut', email=os.getenv('DEFAULT_ADMIN_EMAIL', 'admin@example.com'), is_verified=True)
            default_user.set_password('dydy?123')
            
            db.add(default_user)
            db.commit()
            
            print(f"\n✓ 默认用户创建成功！")
            print(f"  用户名: hbut")
            print(f"  密码: dydy?123")
            return True
            
    except Exception as e:
        print(f"\n❌ 初始化用户失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    init_default_user()

