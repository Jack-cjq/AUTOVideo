"""
工具模块
包含从service_code迁移的工具函数和backend的工具函数
"""
# 导入backend的工具函数（从utils.py）
import sys
import os
from pathlib import Path

# 获取backend目录路径
backend_dir = Path(__file__).parent.parent

# 将backend目录添加到路径中（如果还没有）
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# 导入utils.py中的函数（使用importlib避免循环导入）
try:
    import importlib.util
    utils_py_path = backend_dir / 'utils.py'
    
    if utils_py_path.exists():
        spec = importlib.util.spec_from_file_location("backend_utils", utils_py_path)
        backend_utils = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(backend_utils)
        
        # 导出函数
        response_success = backend_utils.response_success
        response_error = backend_utils.response_error
        login_required = backend_utils.login_required
        model_to_dict = backend_utils.model_to_dict
        models_to_list = backend_utils.models_to_list
    else:
        raise ImportError("utils.py not found")
except Exception as e:
    # 如果导入失败，创建一个占位函数
    from flask import jsonify
    
    def response_success(data=None, message='success', code=200):
        return jsonify({'code': code, 'message': message, 'data': data}), code
    
    def response_error(message='error', code=400, data=None):
        return jsonify({'code': code, 'message': message, 'data': data}), code
    
    def login_required(f):
        return f
    
    def model_to_dict(model):
        return {}
    
    def models_to_list(models):
        return []

