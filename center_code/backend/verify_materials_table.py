"""
验证 materials 表结构是否正确
"""
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from sqlalchemy import inspect, text
from db import engine, get_db

def verify_materials_table():
    """验证 materials 表结构"""
    print("=" * 60)
    print("验证 materials 表结构")
    print("=" * 60)
    print()
    
    try:
        inspector = inspect(engine)
        
        # 检查表是否存在
        tables = inspector.get_table_names()
        if 'materials' not in tables:
            print("❌ materials 表不存在！")
            return False
        
        print("✓ materials 表存在")
        print()
        
        # 获取所有列
        columns = inspector.get_columns('materials')
        column_names = [col['name'] for col in columns]
        
        print(f"当前表中的字段 ({len(column_names)} 个):")
        for col in columns:
            nullable = "NULL" if col.get('nullable', True) else "NOT NULL"
            default = f" DEFAULT {col.get('default', '')}" if col.get('default') else ""
            print(f"  - {col['name']}: {col['type']} {nullable}{default}")
        
        print()
        
        # 检查必需的字段
        required_fields = ['id', 'name', 'status', 'path', 'original_path', 'meta_json', 'type', 'duration', 'width', 'height', 'size', 'created_at', 'updated_at']
        missing_fields = [field for field in required_fields if field not in column_names]
        
        if missing_fields:
            print(f"❌ 缺少以下字段: {', '.join(missing_fields)}")
            return False
        else:
            print("✓ 所有必需字段都存在")
            return True
            
    except Exception as e:
        print(f"❌ 验证时出错: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = verify_materials_table()
    print()
    print("=" * 60)
    if success:
        print("✓ 验证通过")
    else:
        print("❌ 验证失败，请运行迁移脚本: python migrate_material_transcode_tasks.py")
    print("=" * 60)

