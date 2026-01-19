"""
发布计划API
"""
from flask import Blueprint, request
from datetime import datetime
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import response_success, response_error, login_required
from models import PublishPlan, PlanVideo, Merchant
from db import get_db

publish_plans_bp = Blueprint('publish_plans', __name__, url_prefix='/api/publish-plans')


@publish_plans_bp.route('', methods=['GET'])
@login_required
def get_publish_plans():
    """
    获取发布计划列表接口
    
    请求方法: GET
    路径: /api/publish-plans
    认证: 需要登录
    
    查询参数:
        platform (string, 可选): 平台类型，筛选指定平台的计划（douyin/kuaishou/xiaohongshu）
        status (string, 可选): 状态筛选（pending/publishing/completed/failed）
        limit (int, 可选): 每页数量，默认 20
        offset (int, 可选): 偏移量，默认 0
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "success",
            "data": {
                "plans": [
                    {
                        "id": int,
                        "plan_name": "string",
                        "platform": "string",
                        "merchant_id": int,
                        "merchant_name": "string",
                        "video_count": int,
                        "published_count": int,
                        "pending_count": int,
                        "claimed_count": int,
                        "account_count": int,
                        "distribution_mode": "string",
                        "status": "string",
                        "publish_time": "string",
                        "created_at": "string"
                    }
                ],
                "total": int,
                "limit": int,
                "offset": int
            }
        }
    
    说明:
        - 支持按平台和状态筛选
        - 结果按创建时间倒序排列
        - 自动关联商家名称和视频数量
    """
    try:
        platform = request.args.get('platform')
        status = request.args.get('status')
        limit = request.args.get('limit', type=int, default=20)
        offset = request.args.get('offset', type=int, default=0)
        
        with get_db() as db:
            query = db.query(PublishPlan)
            
            if platform:
                query = query.filter(PublishPlan.platform == platform)
            
            if status:
                query = query.filter(PublishPlan.status == status)
            
            total = query.count()
            plans = query.order_by(PublishPlan.created_at.desc()).limit(limit).offset(offset).all()
            
            plans_list = []
            for plan in plans:
                # 获取关联的商家名称
                merchant_name = None
                if plan.merchant_id:
                    merchant = db.query(Merchant).filter(Merchant.id == plan.merchant_id).first()
                    merchant_name = merchant.merchant_name if merchant else None
                
                # 获取计划中的视频数量
                video_count = db.query(PlanVideo).filter(PlanVideo.plan_id == plan.id).count()
                
                plans_list.append({
                    'id': plan.id,
                    'plan_name': plan.plan_name,
                    'platform': plan.platform,
                    'merchant_id': plan.merchant_id,
                    'merchant_name': merchant_name,
                    'video_count': video_count,
                    'published_count': plan.published_count,
                    'pending_count': plan.pending_count,
                    'claimed_count': plan.claimed_count,
                    'account_count': plan.account_count,
                    'distribution_mode': plan.distribution_mode,
                    'status': plan.status,
                    'publish_time': plan.publish_time.isoformat() if plan.publish_time else None,
                    'created_at': plan.created_at.isoformat() if plan.created_at else None
                })
        
        return response_success({
            'plans': plans_list,
            'total': total,
            'limit': limit,
            'offset': offset
        })
    except Exception as e:
        return response_error(str(e), 500)


@publish_plans_bp.route('', methods=['POST'])
@login_required
def create_publish_plan():
    """
    创建发布计划接口
    
    请求方法: POST
    路径: /api/publish-plans
    认证: 需要登录
    
    请求体 (JSON):
        {
            "plan_name": "string",           # 必填，计划名称
            "platform": "string",            # 可选，平台类型，默认 douyin
            "merchant_id": int,              # 可选，关联商家ID
            "distribution_mode": "string",   # 可选，分发模式（manual/sms/qrcode/ai），默认 manual
            "publish_time": "string"         # 可选，发布时间（ISO 格式）
        }
    
    返回数据:
        成功 (201):
        {
            "code": 201,
            "message": "Publish plan created",
            "data": {
                "id": int,
                "plan_name": "string",
                "platform": "string",
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
        - 创建的计划初始状态为 pending（待发布）
        - 分发模式：manual（手动分发）、sms（接收短信派发）、qrcode（扫二维码派发）、ai（AI智能分发）
    """
    try:
        data = request.json
        plan_name = data.get('plan_name')
        platform = data.get('platform', 'douyin')
        merchant_id = data.get('merchant_id')
        distribution_mode = data.get('distribution_mode', 'manual')
        publish_time = data.get('publish_time')
        
        if not plan_name:
            return response_error('plan_name is required', 400)
        
        # 先解析 publish_time，确保格式正确
        parsed_publish_time = None
        if publish_time:
            try:
                parsed_publish_time = datetime.fromisoformat(publish_time)
            except ValueError:
                return response_error('Invalid publish_time format. Please use ISO format (YYYY-MM-DD HH:mm:ss)', 400)
        
        with get_db() as db:
            plan = PublishPlan(
                plan_name=plan_name,
                platform=platform,
                merchant_id=merchant_id,
                distribution_mode=distribution_mode,
                publish_time=parsed_publish_time,
                status='pending'
            )
            db.add(plan)
            db.flush()
            db.commit()
            
            return response_success({
                'id': plan.id,
                'plan_name': plan.plan_name,
                'platform': plan.platform,
                'status': plan.status
            }, 'Publish plan created', 201)
    except Exception as e:
        return response_error(str(e), 500)


@publish_plans_bp.route('/<int:plan_id>', methods=['GET'])
@login_required
def get_publish_plan(plan_id):
    """
    获取发布计划详情接口
    
    请求方法: GET
    路径: /api/publish-plans/{plan_id}
    认证: 需要登录
    
    路径参数:
        plan_id (int): 发布计划ID
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "success",
            "data": {
                "id": int,
                "plan_name": "string",
                "platform": "string",
                "merchant_id": int,
                "merchant_name": "string",
                "video_count": int,
                "videos": [
                    {
                        "id": int,
                        "video_url": "string",
                        "video_title": "string",
                        "thumbnail_url": "string",
                        "status": "string"
                    }
                ],
                "published_count": int,
                "pending_count": int,
                "claimed_count": int,
                "account_count": int,
                "distribution_mode": "string",
                "status": "string",
                "publish_time": "string",
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
        - 返回计划详情及关联的视频列表
        - 如果计划不存在，返回 404 错误
    """
    try:
        with get_db() as db:
            plan = db.query(PublishPlan).filter(PublishPlan.id == plan_id).first()
            
            if not plan:
                return response_error('Publish plan not found', 404)
            
            # 获取关联的商家
            merchant_name = None
            if plan.merchant_id:
                merchant = db.query(Merchant).filter(Merchant.id == plan.merchant_id).first()
                merchant_name = merchant.merchant_name if merchant else None
            
            # 获取计划中的视频
            videos = db.query(PlanVideo).filter(PlanVideo.plan_id == plan_id).all()
            videos_list = []
            for video in videos:
                videos_list.append({
                    'id': video.id,
                    'video_url': video.video_url,
                    'video_title': video.video_title,
                    'thumbnail_url': video.thumbnail_url,
                    'status': video.status
                })
            
            return response_success({
                'id': plan.id,
                'plan_name': plan.plan_name,
                'platform': plan.platform,
                'merchant_id': plan.merchant_id,
                'merchant_name': merchant_name,
                'video_count': len(videos_list),
                'videos': videos_list,
                'published_count': plan.published_count,
                'pending_count': plan.pending_count,
                'claimed_count': plan.claimed_count,
                'account_count': plan.account_count,
                'distribution_mode': plan.distribution_mode,
                'status': plan.status,
                'publish_time': plan.publish_time.isoformat() if plan.publish_time else None,
                'created_at': plan.created_at.isoformat() if plan.created_at else None
            })
    except Exception as e:
        return response_error(str(e), 500)


@publish_plans_bp.route('/<int:plan_id>', methods=['PUT'])
@login_required
def update_publish_plan(plan_id):
    """
    更新发布计划接口
    
    请求方法: PUT
    路径: /api/publish-plans/{plan_id}
    认证: 需要登录
    
    路径参数:
        plan_id (int): 发布计划ID
    
    请求体 (JSON):
        {
            "plan_name": "string",      # 可选，计划名称
            "status": "string",          # 可选，状态（pending/publishing/completed/failed）
            "publish_time": "string"     # 可选，发布时间（ISO 格式）
        }
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "Publish plan updated",
            "data": {
                "id": int,
                "plan_name": "string",
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
        - 只更新提供的字段，未提供的字段保持不变
        - 如果计划不存在，返回 404 错误
    """
    try:
        data = request.json
        with get_db() as db:
            plan = db.query(PublishPlan).filter(PublishPlan.id == plan_id).first()
            
            if not plan:
                return response_error('Publish plan not found', 404)
            
            if 'plan_name' in data:
                plan.plan_name = data['plan_name']
            if 'status' in data:
                plan.status = data['status']
            if 'publish_time' in data:
                if data['publish_time']:
                    try:
                        plan.publish_time = datetime.fromisoformat(data['publish_time'])
                    except ValueError:
                        return response_error('Invalid publish_time format. Please use ISO format (YYYY-MM-DD HH:mm:ss)', 400)
                else:
                    plan.publish_time = None
            
            plan.updated_at = datetime.now()
            
            db.commit()
            
            return response_success({
                'id': plan.id,
                'plan_name': plan.plan_name,
                'status': plan.status
            }, 'Publish plan updated')
    except Exception as e:
        return response_error(str(e), 500)


@publish_plans_bp.route('/<int:plan_id>', methods=['DELETE'])
@login_required
def delete_publish_plan(plan_id):
    """
    删除发布计划接口
    
    请求方法: DELETE
    路径: /api/publish-plans/{plan_id}
    认证: 需要登录
    
    路径参数:
        plan_id (int): 发布计划ID
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "Publish plan deleted",
            "data": {
                "plan_id": int
            }
        }
        
        失败 (404/500):
        {
            "code": 404/500,
            "message": "错误信息",
            "data": null
        }
    
    说明:
        - 删除计划时会级联删除关联的所有视频（PlanVideo）
        - 如果计划不存在，返回 404 错误
    """
    try:
        with get_db() as db:
            plan = db.query(PublishPlan).filter(PublishPlan.id == plan_id).first()
            
            if not plan:
                return response_error('Publish plan not found', 404)
            
            # 删除关联的视频
            db.query(PlanVideo).filter(PlanVideo.plan_id == plan_id).delete()
            
            # 删除计划
            db.delete(plan)
            db.commit()
            
            return response_success({'plan_id': plan_id}, 'Publish plan deleted')
    except Exception as e:
        return response_error(str(e), 500)


@publish_plans_bp.route('/<int:plan_id>/videos', methods=['POST'])
@login_required
def add_video_to_plan(plan_id):
    """
    向发布计划添加视频接口
    
    请求方法: POST
    路径: /api/publish-plans/{plan_id}/videos
    认证: 需要登录
    
    路径参数:
        plan_id (int): 发布计划ID
    
    请求体 (JSON):
        {
            "video_url": "string",       # 必填，视频URL
            "video_title": "string",     # 可选，视频标题
            "thumbnail_url": "string"     # 可选，缩略图URL
        }
    
    返回数据:
        成功 (201):
        {
            "code": 201,
            "message": "Video added to plan",
            "data": {
                "id": int,
                "video_url": "string",
                "video_title": "string"
            }
        }
        
        失败 (400/404/500):
        {
            "code": 400/404/500,
            "message": "错误信息",
            "data": null
        }
    
    说明:
        - 添加视频后会自动更新计划的 video_count
        - 如果计划不存在，返回 404 错误
    """
    try:
        data = request.json
        video_url = data.get('video_url')
        video_title = data.get('video_title')
        thumbnail_url = data.get('thumbnail_url')
        
        if not video_url:
            return response_error('video_url is required', 400)
        
        with get_db() as db:
            plan = db.query(PublishPlan).filter(PublishPlan.id == plan_id).first()
            if not plan:
                return response_error('Publish plan not found', 404)
            
            video = PlanVideo(
                plan_id=plan_id,
                video_url=video_url,
                video_title=video_title,
                thumbnail_url=thumbnail_url,
                status='pending'
            )
            db.add(video)
            
            # 更新计划的视频数量
            plan.video_count = db.query(PlanVideo).filter(PlanVideo.plan_id == plan_id).count()
            plan.updated_at = datetime.now()
            
            db.commit()
            
            # 如果发布时间接近当前时间（1分钟内），立即触发任务处理
            now = datetime.now()
            if plan.publish_time and (now - plan.publish_time).total_seconds() <= 60:
                print(f"[发布计划] 检测到发布时间接近当前时间，立即触发任务处理: {plan.plan_name} (ID: {plan.id})")
                # 导入任务处理器并触发处理
                from services.task_processor import TaskProcessor
                task_processor = TaskProcessor(poll_interval=0)  # 创建临时处理器，无轮询间隔
                task_processor._process_pending_tasks()  # 立即处理待处理任务
            
            return response_success({
                'id': video.id,
                'video_url': video.video_url,
                'video_title': video.video_title
            }, 'Video added to plan', 201)
    except Exception as e:
        return response_error(str(e), 500)


@publish_plans_bp.route('/<int:plan_id>/save-info', methods=['POST'])
@login_required
def save_publish_info(plan_id):
    """
    保存发布信息接口（占位接口，复杂功能待实现）
    
    请求方法: POST
    路径: /api/publish-plans/{plan_id}/save-info
    认证: 需要登录
    
    路径参数:
        plan_id (int): 发布计划ID
    
    请求体 (JSON):
        {
            "distribution_rules": {},      # 可选，分发规则配置（待实现）
            "account_assignment": [],      # 可选，账号分配列表（待实现）
            "publish_schedule": {},        # 可选，发布计划配置（待实现）
            "sms_config": {},              # 可选，短信分发配置（待实现）
            "qrcode_config": {},           # 可选，二维码分发配置（待实现）
            "ai_config": {}                # 可选，AI智能分发配置（待实现）
        }
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "Publish info saved (placeholder)",
            "data": {
                "plan_id": int
            }
        }
        
        失败 (404/500):
        {
            "code": 404/500,
            "message": "错误信息",
            "data": null
        }
    
    说明:
        - 此接口为占位接口，具体实现待开发
        - 用于保存发布计划的详细信息，包括：
          * 分发规则：手动分发、短信分发、二维码分发、AI智能分发的配置
          * 账号分配：指定哪些账号参与发布计划
          * 发布计划：定时发布、批量发布等配置
        - 如果计划不存在，返回 404 错误
    """
    try:
        data = request.json
        # TODO: 实现保存发布信息的逻辑
        return response_success({'plan_id': plan_id}, 'Publish info saved (placeholder)')
    except Exception as e:
        return response_error(str(e), 500)


@publish_plans_bp.route('/<int:plan_id>/distribute', methods=['POST'])
@login_required
def distribute_plan(plan_id):
    """
    分发发布计划接口（占位接口，复杂功能待实现）
    
    请求方法: POST
    路径: /api/publish-plans/{plan_id}/distribute
    认证: 需要登录
    
    路径参数:
        plan_id (int): 发布计划ID
    
    请求体 (JSON):
        {
            "distribution_mode": "string",  # 可选，分发模式（manual/sms/qrcode/ai），默认使用计划配置
            "account_ids": []               # 可选，指定账号ID列表（手动分发时使用）
        }
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "Plan distributed (placeholder)",
            "data": {
                "plan_id": int,
                "distribution_mode": "string",
                "distributed_count": int
            }
        }
        
        失败 (404/500):
        {
            "code": 404/500,
            "message": "错误信息",
            "data": null
        }
    
    说明:
        - 此接口为占位接口，具体实现待开发
        - 根据分发模式（manual/sms/qrcode/ai）将发布计划中的视频分发给账号
        - manual: 手动指定账号列表
        - sms: 通过短信接收任务分配
        - qrcode: 通过扫描二维码领取任务
        - ai: AI智能分配任务给合适的账号
        - 如果计划不存在，返回 404 错误
    """
    try:
        data = request.json
        # TODO: 实现分发逻辑
        return response_success({
            'plan_id': plan_id,
            'distribution_mode': data.get('distribution_mode', 'manual'),
            'distributed_count': 0
        }, 'Plan distributed (placeholder)')
    except Exception as e:
        return response_error(str(e), 500)


@publish_plans_bp.route('/<int:plan_id>/claim', methods=['POST'])
@login_required
def claim_plan_video(plan_id):
    """
    领取发布计划中的视频接口（占位接口，复杂功能待实现）
    
    请求方法: POST
    路径: /api/publish-plans/{plan_id}/claim
    认证: 需要登录
    
    路径参数:
        plan_id (int): 发布计划ID
    
    请求体 (JSON):
        {
            "account_id": int,        # 必填，账号ID
            "video_id": int           # 可选，视频ID，如果不指定则自动分配一个待发布的视频
        }
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "Video claimed (placeholder)",
            "data": {
                "plan_id": int,
                "account_id": int,
                "video_id": int,
                "status": "string"
            }
        }
        
        失败 (400/404/500):
        {
            "code": 400/404/500,
            "message": "错误信息",
            "data": null
        }
    
    说明:
        - 此接口为占位接口，具体实现待开发
        - 用于账号领取发布计划中的视频任务（适用于二维码分发模式）
        - 如果指定了 video_id，则领取指定的视频
        - 如果未指定 video_id，则自动分配一个待发布的视频给该账号
        - 领取成功后会更新 claimed_count
        - 如果计划或账号不存在，返回 404 错误
    """
    try:
        data = request.json
        account_id = data.get('account_id')
        video_id = data.get('video_id')
        
        if not account_id:
            return response_error('account_id is required', 400)
        
        # TODO: 实现领取逻辑
        return response_success({
            'plan_id': plan_id,
            'account_id': account_id,
            'video_id': video_id,
            'status': 'claimed'
        }, 'Video claimed (placeholder)')
    except Exception as e:
        return response_error(str(e), 500)

