"""
统计API
"""
from flask import Blueprint
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import response_success, response_error, login_required
from models import Device, Account, VideoTask, ChatTask, ListenTask
from db import get_db

stats_bp = Blueprint('stats', __name__, url_prefix='/api/stats')


@stats_bp.route('', methods=['GET'])
@login_required
def get_stats():
    """
    获取系统统计信息接口
    
    请求方法: GET
    路径: /api/stats
    认证: 需要登录
    
    查询参数: 无
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "success",
            "data": {
                "online_devices": int,          # 在线设备数
                "logged_in_accounts": int,      # 已登录账号数
                "pending_video_tasks": int,     # 待处理视频任务数
                "pending_chat_tasks": int,      # 待处理对话任务数
                "pending_listen_tasks": int     # 待处理监听任务数
            }
        }
        
        失败 (500):
        {
            "code": 500,
            "message": "错误信息",
            "data": null
        }
    
    说明:
        - 返回系统整体的统计信息
        - 用于仪表盘展示
    """
    try:
        with get_db() as db:
            online_devices = db.query(Device).filter(Device.status == 'online').count()
            logged_in_accounts = db.query(Account).filter(Account.login_status == 'logged_in').count()
            pending_video_tasks = db.query(VideoTask).filter(VideoTask.status == 'pending').count()
            pending_chat_tasks = db.query(ChatTask).filter(ChatTask.status == 'pending').count()
            pending_listen_tasks = db.query(ListenTask).filter(ListenTask.status == 'pending').count()
        
        return response_success({
            'online_devices': online_devices,
            'logged_in_accounts': logged_in_accounts,
            'pending_video_tasks': pending_video_tasks,
            'pending_chat_tasks': pending_chat_tasks,
            'pending_listen_tasks': pending_listen_tasks
        })
    except Exception as e:
        return response_error(str(e), 500)

