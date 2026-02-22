"""
设备管理API
"""
from flask import Blueprint, request
from datetime import datetime
import sys
import os
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import response_success, response_error
from models import Device
from db import get_db

devices_bp = Blueprint('devices', __name__, url_prefix='/api/devices')


@devices_bp.route('/register', methods=['POST'])
def register_device():
    """
    设备注册接口
    
    请求方法: POST
    路径: /api/devices/register
    认证: 不需要（设备端调用）
    
    请求体 (JSON):
        {
            "device_id": "string",      # 必填，设备ID（字符串格式，唯一标识）
            "device_name": "string",    # 可选，设备名称
            "ip_address": "string"      # 可选，IP地址
        }
    
    返回数据:
        成功 (201):
        {
            "code": 201,
            "message": "Device registered successfully",
            "data": {
                "id": int,
                "device_id": "string",
                "device_name": "string",
                "ip_address": "string",
                "status": "string"
            }
        }
        
        失败 (400/500):
        {
            "code": 400/500,
            "message": "错误信息",
            "data": null
        }
    
    说明:
        - 如果设备已存在，会更新设备信息并设置为 online 状态
        - 如果设备不存在，会创建新设备
        - 设备注册后状态自动设置为 online
        - 支持数据库连接重试机制，解决启动时连接未就绪的问题
    """
    try:
        data = request.json
        device_id = data.get('device_id')
        device_name = data.get('device_name')
        ip_address = data.get('ip_address')
        
        if not device_id:
            return response_error('device_id is required', 400)
        
        # 数据库连接重试机制（最多重试3次，每次间隔0.5秒）
        max_retries = 3
        retry_delay = 0.5
        last_error = None
        
        for attempt in range(max_retries):
            try:
                with get_db() as db:
                    # 检查设备是否已存在
                    existing_device = db.query(Device).filter(Device.device_id == device_id).first()
                    
                    if existing_device:
                        # 更新设备信息
                        existing_device.device_name = device_name
                        existing_device.ip_address = ip_address
                        existing_device.status = 'online'
                        existing_device.last_heartbeat = datetime.now()
                        existing_device.updated_at = datetime.now()
                        device = existing_device
                    else:
                        # 创建新设备
                        device = Device(
                            device_id=device_id,
                            device_name=device_name,
                            ip_address=ip_address,
                            status='online',
                            last_heartbeat=datetime.now()
                        )
                        db.add(device)
                        db.flush()
                    
                    db.commit()
                    return response_success({
                        'id': device.id,
                        'device_id': device.device_id,
                        'device_name': device.device_name,
                        'ip_address': device.ip_address,
                        'status': device.status
                    }, 'Device registered successfully', 201)
            except Exception as e:
                last_error = e
                # 如果是数据库连接错误，进行重试
                error_str = str(e).lower()
                if any(keyword in error_str for keyword in ['connection', 'timeout', 'lost', 'closed', 'operational']):
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                # 其他错误直接抛出
                raise
        
        # 如果所有重试都失败，返回错误
        return response_error(f'Database connection failed after {max_retries} attempts: {str(last_error)}', 500)
    except Exception as e:
        return response_error(str(e), 500)


@devices_bp.route('', methods=['GET'])
def get_devices():
    """
    获取设备列表接口
    
    请求方法: GET
    路径: /api/devices
    认证: 不需要
    
    查询参数: 无
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "success",
            "data": [
                {
                    "id": int,
                    "device_id": "string",
                    "device_name": "string",
                    "ip_address": "string",
                    "status": "string",
                    "last_heartbeat": "string",
                    "created_at": "string",
                    "updated_at": "string"
                }
            ]
        }
    
    说明:
        - 自动检查设备是否离线（超过60秒未心跳的设备会被标记为 offline）
        - 返回所有设备信息
        - 支持数据库连接重试机制，解决启动时连接未就绪的问题
    """
    # 数据库连接重试机制（最多重试3次，每次间隔0.5秒）
    max_retries = 3
    retry_delay = 0.5
    last_error = None
    
    for attempt in range(max_retries):
        try:
            with get_db() as db:
                devices = db.query(Device).all()
                
                # 检查设备是否离线（超过60秒未心跳）
                now = datetime.now()
                for device in devices:
                    if device.last_heartbeat:
                        delta = (now - device.last_heartbeat).total_seconds()
                        if delta > 60 and device.status == 'online':
                            device.status = 'offline'
                            device.updated_at = datetime.now()
                            db.commit()
                
                devices_list = []
                for device in devices:
                    devices_list.append({
                        'id': device.id,
                        'device_id': device.device_id,
                        'device_name': device.device_name,
                        'ip_address': device.ip_address,
                        'status': device.status,
                        'last_heartbeat': device.last_heartbeat.isoformat() if device.last_heartbeat else None,
                        'created_at': device.created_at.isoformat() if device.created_at else None,
                        'updated_at': device.updated_at.isoformat() if device.updated_at else None
                    })
            
            return response_success(devices_list)
        except Exception as e:
            last_error = e
            # 如果是数据库连接错误，进行重试
            error_str = str(e).lower()
            if any(keyword in error_str for keyword in ['connection', 'timeout', 'lost', 'closed', 'operational']):
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
            # 其他错误直接返回
            return response_error(str(e), 500)
    
    # 如果所有重试都失败，返回错误
    return response_error(f'Database connection failed after {max_retries} attempts: {str(last_error)}', 500)


@devices_bp.route('/<device_id>', methods=['GET'])
def get_device(device_id):
    """
    获取设备详情接口
    
    请求方法: GET
    路径: /api/devices/{device_id}
    认证: 不需要
    
    路径参数:
        device_id (string): 设备ID（字符串格式）
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "success",
            "data": {
                "id": int,
                "device_id": "string",
                "device_name": "string",
                "ip_address": "string",
                "status": "string",
                "last_heartbeat": "string",
                "created_at": "string"
            }
        }
        
        失败 (404/500):
        {
            "code": 404/500,
            "message": "错误信息",
            "data": null
        }
    
    说明:
        - 如果设备不存在，返回 404 错误
        - 支持数据库连接重试机制，解决启动时连接未就绪的问题
    """
    # 数据库连接重试机制（最多重试3次，每次间隔0.5秒）
    max_retries = 3
    retry_delay = 0.5
    last_error = None
    
    for attempt in range(max_retries):
        try:
            with get_db() as db:
                device = db.query(Device).filter(Device.device_id == device_id).first()
                
                if not device:
                    return response_error('Device not found', 404)
                
                return response_success({
                    'id': device.id,
                    'device_id': device.device_id,
                    'device_name': device.device_name,
                    'ip_address': device.ip_address,
                    'status': device.status,
                    'last_heartbeat': device.last_heartbeat.isoformat() if device.last_heartbeat else None,
                    'created_at': device.created_at.isoformat() if device.created_at else None
                })
        except Exception as e:
            last_error = e
            # 如果是数据库连接错误，进行重试
            error_str = str(e).lower()
            if any(keyword in error_str for keyword in ['connection', 'timeout', 'lost', 'closed', 'operational']):
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
            # 其他错误直接返回
            return response_error(str(e), 500)
    
    # 如果所有重试都失败，返回错误
    return response_error(f'Database connection failed after {max_retries} attempts: {str(last_error)}', 500)


@devices_bp.route('/<device_id>/heartbeat', methods=['POST'])
def device_heartbeat(device_id):
    """
    设备心跳接口
    
    请求方法: POST
    路径: /api/devices/{device_id}/heartbeat
    认证: 不需要（设备端调用）
    
    路径参数:
        device_id (string): 设备ID（字符串格式）
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "success",
            "data": {
                "id": int,
                "device_id": "string",
                "status": "string"
            }
        }
        
        失败 (404/500):
        {
            "code": 404/500,
            "message": "错误信息",
            "data": null
        }
    
    说明:
        - 设备应定期调用此接口（建议每30秒）以保持在线状态
        - 调用后设备状态会自动更新为 online，并更新 last_heartbeat 时间
        - 如果设备不存在，返回 404 错误
        - 支持数据库连接重试机制，解决启动时连接未就绪的问题
    """
    # 数据库连接重试机制（最多重试3次，每次间隔0.5秒）
    max_retries = 3
    retry_delay = 0.5
    last_error = None
    
    for attempt in range(max_retries):
        try:
            with get_db() as db:
                device = db.query(Device).filter(Device.device_id == device_id).first()
                
                if not device:
                    return response_error('Device not found', 404)
                
                device.status = 'online'
                device.last_heartbeat = datetime.now()
                device.updated_at = datetime.now()
                db.commit()
                
                return response_success({
                    'id': device.id,
                    'device_id': device.device_id,
                    'status': device.status
                })
        except Exception as e:
            last_error = e
            # 如果是数据库连接错误，进行重试
            error_str = str(e).lower()
            if any(keyword in error_str for keyword in ['connection', 'timeout', 'lost', 'closed', 'operational']):
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
            # 其他错误直接返回
            return response_error(str(e), 500)
    
    # 如果所有重试都失败，返回错误
    return response_error(f'Database connection failed after {max_retries} attempts: {str(last_error)}', 500)

