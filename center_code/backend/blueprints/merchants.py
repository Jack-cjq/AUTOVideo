"""
商家管理API
"""
from flask import Blueprint, request
from datetime import datetime
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import response_success, response_error, login_required
from models import Merchant
from db import get_db

merchants_bp = Blueprint('merchants', __name__, url_prefix='/api/merchants')


@merchants_bp.route('', methods=['GET'])
@login_required
def get_merchants():
    """
    获取商家列表接口
    
    请求方法: GET
    路径: /api/merchants
    认证: 需要登录
    
    查询参数:
        search (string, 可选): 搜索关键词，模糊匹配商家名称
        status (string, 可选): 状态筛选（active/inactive）
        limit (int, 可选): 每页数量，默认 50
        offset (int, 可选): 偏移量，默认 0
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "success",
            "data": {
                "merchants": [
                    {
                        "id": int,
                        "merchant_name": "string",
                        "contact_person": "string",
                        "contact_phone": "string",
                        "contact_email": "string",
                        "address": "string",
                        "status": "string",
                        "created_at": "string"
                    }
                ],
                "total": int,
                "limit": int,
                "offset": int
            }
        }
    
    说明:
        - 支持按商家名称搜索和状态筛选
        - 结果按创建时间倒序排列
    """
    try:
        search = request.args.get('search')
        status = request.args.get('status')
        limit = request.args.get('limit', type=int, default=50)
        offset = request.args.get('offset', type=int, default=0)
        
        with get_db() as db:
            query = db.query(Merchant)
            
            if search:
                query = query.filter(Merchant.merchant_name.like(f'%{search}%'))
            
            if status:
                query = query.filter(Merchant.status == status)
            
            total = query.count()
            merchants = query.order_by(Merchant.created_at.desc()).limit(limit).offset(offset).all()
            
            merchants_list = []
            for merchant in merchants:
                merchants_list.append({
                    'id': merchant.id,
                    'merchant_name': merchant.merchant_name,
                    'contact_person': merchant.contact_person,
                    'contact_phone': merchant.contact_phone,
                    'contact_email': merchant.contact_email,
                    'address': merchant.address,
                    'status': merchant.status,
                    'created_at': merchant.created_at.isoformat() if merchant.created_at else None
                })
        
        return response_success({
            'merchants': merchants_list,
            'total': total,
            'limit': limit,
            'offset': offset
        })
    except Exception as e:
        return response_error(str(e), 500)


@merchants_bp.route('', methods=['POST'])
@login_required
def create_merchant():
    """
    创建商家接口
    
    请求方法: POST
    路径: /api/merchants
    认证: 需要登录
    
    请求体 (JSON):
        {
            "merchant_name": "string",    # 必填，商家名称（必须唯一）
            "contact_person": "string",  # 可选，联系人
            "contact_phone": "string",    # 可选，联系电话
            "contact_email": "string",   # 可选，邮箱
            "address": "string",          # 可选，地址
            "status": "string"            # 可选，状态（active/inactive），默认 active
        }
    
    返回数据:
        成功 (201):
        {
            "code": 201,
            "message": "Merchant created",
            "data": {
                "id": int,
                "merchant_name": "string"
            }
        }
        
        失败 (400/500):
        {
            "code": 400/500,
            "message": "错误信息",
            "data": null
        }
    
    说明:
        - 商家名称必须唯一，如果已存在返回 400 错误
    """
    try:
        data = request.json
        merchant_name = data.get('merchant_name')
        
        if not merchant_name:
            return response_error('merchant_name is required', 400)
        
        with get_db() as db:
            # 检查商家名称是否已存在
            existing = db.query(Merchant).filter(Merchant.merchant_name == merchant_name).first()
            if existing:
                return response_error('Merchant name already exists', 400)
            
            merchant = Merchant(
                merchant_name=merchant_name,
                contact_person=data.get('contact_person'),
                contact_phone=data.get('contact_phone'),
                contact_email=data.get('contact_email'),
                address=data.get('address'),
                status=data.get('status', 'active')
            )
            db.add(merchant)
            db.flush()
            db.commit()
            
            return response_success({
                'id': merchant.id,
                'merchant_name': merchant.merchant_name
            }, 'Merchant created', 201)
    except Exception as e:
        return response_error(str(e), 500)


@merchants_bp.route('/<int:merchant_id>', methods=['GET'])
@login_required
def get_merchant(merchant_id):
    """
    获取商家详情接口
    
    请求方法: GET
    路径: /api/merchants/{merchant_id}
    认证: 需要登录
    
    路径参数:
        merchant_id (int): 商家ID
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "success",
            "data": {
                "id": int,
                "merchant_name": "string",
                "contact_person": "string",
                "contact_phone": "string",
                "contact_email": "string",
                "address": "string",
                "status": "string",
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
        - 如果商家不存在，返回 404 错误
    """
    try:
        with get_db() as db:
            merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
            
            if not merchant:
                return response_error('Merchant not found', 404)
            
            return response_success({
                'id': merchant.id,
                'merchant_name': merchant.merchant_name,
                'contact_person': merchant.contact_person,
                'contact_phone': merchant.contact_phone,
                'contact_email': merchant.contact_email,
                'address': merchant.address,
                'status': merchant.status,
                'created_at': merchant.created_at.isoformat() if merchant.created_at else None
            })
    except Exception as e:
        return response_error(str(e), 500)


@merchants_bp.route('/<int:merchant_id>', methods=['PUT'])
@login_required
def update_merchant(merchant_id):
    """
    更新商家信息接口
    
    请求方法: PUT
    路径: /api/merchants/{merchant_id}
    认证: 需要登录
    
    路径参数:
        merchant_id (int): 商家ID
    
    请求体 (JSON):
        {
            "merchant_name": "string",    # 可选，商家名称
            "contact_person": "string",  # 可选，联系人
            "contact_phone": "string",    # 可选，联系电话
            "contact_email": "string",   # 可选，邮箱
            "address": "string",          # 可选，地址
            "status": "string"            # 可选，状态（active/inactive）
        }
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "Merchant updated",
            "data": {
                "id": int,
                "merchant_name": "string"
            }
        }
        
        失败 (404/500):
        {
            "code": 404/500,
            "message": "错误信息",
            "data": null
        }
    
    说明:
        - 只更新提供的字段，未提供的字段保持不变
        - 如果商家不存在，返回 404 错误
    """
    try:
        data = request.json
        with get_db() as db:
            merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
            
            if not merchant:
                return response_error('Merchant not found', 404)
            
            if 'merchant_name' in data:
                merchant.merchant_name = data['merchant_name']
            if 'contact_person' in data:
                merchant.contact_person = data['contact_person']
            if 'contact_phone' in data:
                merchant.contact_phone = data['contact_phone']
            if 'contact_email' in data:
                merchant.contact_email = data['contact_email']
            if 'address' in data:
                merchant.address = data['address']
            if 'status' in data:
                merchant.status = data['status']
            
            merchant.updated_at = datetime.now()
            db.commit()
            
            return response_success({
                'id': merchant.id,
                'merchant_name': merchant.merchant_name
            }, 'Merchant updated')
    except Exception as e:
        return response_error(str(e), 500)


@merchants_bp.route('/<int:merchant_id>', methods=['DELETE'])
@login_required
def delete_merchant(merchant_id):
    """
    删除商家接口
    
    请求方法: DELETE
    路径: /api/merchants/{merchant_id}
    认证: 需要登录
    
    路径参数:
        merchant_id (int): 商家ID
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "Merchant deleted",
            "data": {
                "merchant_id": int
            }
        }
        
        失败 (404/500):
        {
            "code": 404/500,
            "message": "错误信息",
            "data": null
        }
    
    说明:
        - 如果商家不存在，返回 404 错误
        - 注意：删除商家不会删除关联的发布计划，发布计划的 merchant_id 会变为 null
    """
    try:
        with get_db() as db:
            merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
            
            if not merchant:
                return response_error('Merchant not found', 404)
            
            db.delete(merchant)
            db.commit()
            
            return response_success({'merchant_id': merchant_id}, 'Merchant deleted')
    except Exception as e:
        return response_error(str(e), 500)

