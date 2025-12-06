"""
云视频库API
"""
from flask import Blueprint, request
from datetime import datetime
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import response_success, response_error, login_required
from models import VideoLibrary
from db import get_db

video_library_bp = Blueprint('video_library', __name__, url_prefix='/api/video-library')


@video_library_bp.route('', methods=['GET'])
@login_required
def get_videos():
    """
    获取视频列表接口
    
    请求方法: GET
    路径: /api/video-library
    认证: 需要登录
    
    查询参数:
        search (string, 可选): 搜索关键词，模糊匹配视频名称
        platform (string, 可选): 平台筛选（douyin/kuaishou/xiaohongshu）
        limit (int, 可选): 每页数量，默认 50
        offset (int, 可选): 偏移量，默认 0
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "success",
            "data": {
                "videos": [
                    {
                        "id": int,
                        "video_name": "string",
                        "video_url": "string",
                        "thumbnail_url": "string",
                        "video_size": int,        # 文件大小（字节）
                        "duration": int,          # 视频时长（秒）
                        "platform": "string",
                        "tags": "string",         # 标签，逗号分隔
                        "description": "string",
                        "upload_time": "string",
                        "created_at": "string"
                    }
                ],
                "total": int,
                "limit": int,
                "offset": int
            }
        }
    
    说明:
        - 支持按视频名称搜索和平台筛选
        - 结果按创建时间倒序排列
    """
    try:
        search = request.args.get('search')
        platform = request.args.get('platform')
        limit = request.args.get('limit', type=int, default=50)
        offset = request.args.get('offset', type=int, default=0)
        
        with get_db() as db:
            query = db.query(VideoLibrary)
            
            if search:
                query = query.filter(
                    VideoLibrary.video_name.like(f'%{search}%')
                )
            
            if platform:
                query = query.filter(VideoLibrary.platform == platform)
            
            total = query.count()
            videos = query.order_by(VideoLibrary.created_at.desc()).limit(limit).offset(offset).all()
            
            videos_list = []
            for video in videos:
                videos_list.append({
                    'id': video.id,
                    'video_name': video.video_name,
                    'video_url': video.video_url,
                    'thumbnail_url': video.thumbnail_url,
                    'video_size': video.video_size,
                    'duration': video.duration,
                    'platform': video.platform,
                    'tags': video.tags,
                    'description': video.description,
                    'upload_time': video.upload_time.isoformat() if video.upload_time else None,
                    'created_at': video.created_at.isoformat() if video.created_at else None
                })
        
        return response_success({
            'videos': videos_list,
            'total': total,
            'limit': limit,
            'offset': offset
        })
    except Exception as e:
        return response_error(str(e), 500)


@video_library_bp.route('', methods=['POST'])
@login_required
def upload_video():
    """
    上传视频到视频库接口
    
    请求方法: POST
    路径: /api/video-library
    认证: 需要登录
    
    请求体 (JSON):
        {
            "video_name": "string",       # 必填，视频名称
            "video_url": "string",        # 必填，视频URL
            "thumbnail_url": "string",   # 可选，缩略图URL
            "video_size": int,            # 可选，文件大小（字节）
            "duration": int,              # 可选，视频时长（秒）
            "platform": "string",        # 可选，来源平台
            "tags": "string",             # 可选，标签（逗号分隔）
            "description": "string"       # 可选，描述
        }
    
    返回数据:
        成功 (201):
        {
            "code": 201,
            "message": "Video uploaded",
            "data": {
                "id": int,
                "video_name": "string",
                "video_url": "string"
            }
        }
        
        失败 (400/500):
        {
            "code": 400/500,
            "message": "错误信息",
            "data": null
        }
    
    说明:
        - 此接口仅保存视频信息到数据库，不处理实际文件上传
        - 实际文件上传需要先上传到文件服务器，然后调用此接口保存信息
    """
    try:
        data = request.json
        video_name = data.get('video_name')
        video_url = data.get('video_url')
        
        if not video_name or not video_url:
            return response_error('video_name and video_url are required', 400)
        
        with get_db() as db:
            video = VideoLibrary(
                video_name=video_name,
                video_url=video_url,
                thumbnail_url=data.get('thumbnail_url'),
                video_size=data.get('video_size'),
                duration=data.get('duration'),
                platform=data.get('platform'),
                tags=data.get('tags'),
                description=data.get('description')
            )
            db.add(video)
            db.flush()
            db.commit()
            
            return response_success({
                'id': video.id,
                'video_name': video.video_name,
                'video_url': video.video_url
            }, 'Video uploaded', 201)
    except Exception as e:
        return response_error(str(e), 500)


@video_library_bp.route('/<int:video_id>', methods=['GET'])
@login_required
def get_video(video_id):
    """
    获取视频详情接口
    
    请求方法: GET
    路径: /api/video-library/{video_id}
    认证: 需要登录
    
    路径参数:
        video_id (int): 视频ID
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "success",
            "data": {
                "id": int,
                "video_name": "string",
                "video_url": "string",
                "thumbnail_url": "string",
                "video_size": int,
                "duration": int,
                "platform": "string",
                "tags": "string",
                "description": "string",
                "upload_time": "string"
            }
        }
        
        失败 (404/500):
        {
            "code": 404/500,
            "message": "错误信息",
            "data": null
        }
    
    说明:
        - 如果视频不存在，返回 404 错误
    """
    try:
        with get_db() as db:
            video = db.query(VideoLibrary).filter(VideoLibrary.id == video_id).first()
            
            if not video:
                return response_error('Video not found', 404)
            
            return response_success({
                'id': video.id,
                'video_name': video.video_name,
                'video_url': video.video_url,
                'thumbnail_url': video.thumbnail_url,
                'video_size': video.video_size,
                'duration': video.duration,
                'platform': video.platform,
                'tags': video.tags,
                'description': video.description,
                'upload_time': video.upload_time.isoformat() if video.upload_time else None
            })
    except Exception as e:
        return response_error(str(e), 500)


@video_library_bp.route('/<int:video_id>', methods=['PUT'])
@login_required
def update_video(video_id):
    """
    更新视频信息接口
    
    请求方法: PUT
    路径: /api/video-library/{video_id}
    认证: 需要登录
    
    路径参数:
        video_id (int): 视频ID
    
    请求体 (JSON):
        {
            "video_name": "string",   # 可选，视频名称
            "tags": "string",         # 可选，标签（逗号分隔）
            "description": "string"   # 可选，描述
        }
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "Video updated",
            "data": {
                "id": int,
                "video_name": "string"
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
        - 如果视频不存在，返回 404 错误
    """
    try:
        data = request.json
        with get_db() as db:
            video = db.query(VideoLibrary).filter(VideoLibrary.id == video_id).first()
            
            if not video:
                return response_error('Video not found', 404)
            
            if 'video_name' in data:
                video.video_name = data['video_name']
            if 'tags' in data:
                video.tags = data['tags']
            if 'description' in data:
                video.description = data['description']
            
            video.updated_at = datetime.now()
            db.commit()
            
            return response_success({
                'id': video.id,
                'video_name': video.video_name
            }, 'Video updated')
    except Exception as e:
        return response_error(str(e), 500)


@video_library_bp.route('/<int:video_id>', methods=['DELETE'])
@login_required
def delete_video(video_id):
    """
    删除视频接口
    
    请求方法: DELETE
    路径: /api/video-library/{video_id}
    认证: 需要登录
    
    路径参数:
        video_id (int): 视频ID
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "Video deleted",
            "data": {
                "video_id": int
            }
        }
        
        失败 (404/500):
        {
            "code": 404/500,
            "message": "错误信息",
            "data": null
        }
    
    说明:
        - 此接口仅删除数据库记录，不删除实际视频文件
        - 如果视频不存在，返回 404 错误
    """
    try:
        with get_db() as db:
            video = db.query(VideoLibrary).filter(VideoLibrary.id == video_id).first()
            
            if not video:
                return response_error('Video not found', 404)
            
            db.delete(video)
            db.commit()
            
            return response_success({'video_id': video_id}, 'Video deleted')
    except Exception as e:
        return response_error(str(e), 500)

