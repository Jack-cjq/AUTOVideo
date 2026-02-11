"""
云视频库API
"""
from flask import Blueprint, request
from datetime import datetime
import sys
import os
from werkzeug.utils import secure_filename
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import response_success, response_error, login_required, get_current_user_id
from models import VideoLibrary
from db import get_db
try:
    from utils.cos_service import (
        upload_file_to_cos, 
        upload_file_data_to_cos,
        delete_file_from_cos,
        generate_cos_key,
        get_file_url
    )
    COS_AVAILABLE = True
except ImportError:
    COS_AVAILABLE = False
    print("警告：腾讯云COS SDK未安装，视频库将使用本地存储")

video_library_bp = Blueprint('video_library', __name__, url_prefix='/api/video-library')


def _extract_cos_key_from_url(url: str) -> str:
    """
    从COS URL中提取COS key（对象键）
    
    Args:
        url: COS URL（可能是预签名URL或普通URL）
    
    Returns:
        COS key，如果无法提取则返回None
    """
    if not url:
        return None
    
    try:
        from config import COS_DOMAIN, COS_SCHEME, COS_BUCKET, COS_REGION
        
        # 如果是预签名URL，先提取基础URL部分（去掉查询参数）
        if '?' in url:
            url = url.split('?')[0]
        
        # 方法1：使用自定义域名
        if COS_DOMAIN and COS_DOMAIN in url:
            cos_key = url.replace(COS_DOMAIN.rstrip('/') + '/', '').lstrip('/')
            return cos_key
        
        # 方法2：使用默认域名格式
        # https://bucket.cos.region.myqcloud.com/key
        prefix = f"{COS_SCHEME}://{COS_BUCKET}.cos.{COS_REGION}.myqcloud.com/"
        if url.startswith(prefix):
            cos_key = url.replace(prefix, '').lstrip('/')
            return cos_key
        
        # 方法3：尝试从URL路径中提取（如果URL包含video/等路径）
        # 假设URL格式为：.../video/2024/01/15/filename.mp4
        if '/video/' in url:
            parts = url.split('/video/')
            if len(parts) > 1:
                return 'video/' + parts[1].split('?')[0].lstrip('/')
        
        return None
    except Exception as e:
        print(f"[VideoLibrary] 提取COS key失败: {e}")
        return None


def _refresh_cos_url_if_needed(url: str) -> str:
    """
    如果需要，刷新COS URL（生成新的预签名URL）
    
    Args:
        url: 原始URL
    
    Returns:
        刷新后的URL（如果是COS URL）或原始URL
    """
    if not url or not COS_AVAILABLE:
        return url
    
    # 检查是否是COS URL
    try:
        from config import COS_DOMAIN, COS_BUCKET
        is_cos_url = False
        
        if COS_DOMAIN and COS_DOMAIN in url:
            is_cos_url = True
        elif COS_BUCKET and (f'cos.' in url or COS_BUCKET in url):
            is_cos_url = True
        
        if not is_cos_url:
            return url
        
        # 提取COS key
        cos_key = _extract_cos_key_from_url(url)
        if not cos_key:
            return url
        
        # 生成新的预签名URL（7天有效期）
        try:
            new_url = get_file_url(cos_key, use_presigned=True, expires_in=86400 * 7)
            return new_url
        except Exception as e:
            print(f"[VideoLibrary] 生成预签名URL失败: {e}，使用原始URL")
            return url
    except Exception as e:
        print(f"[VideoLibrary] 刷新COS URL时出错: {e}")
        return url


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
        # 获取当前用户ID，确保数据隔离
        user_id = get_current_user_id()
        if not user_id:
            return response_error('请先登录', 401)
        
        search = request.args.get('search')
        platform = request.args.get('platform')
        limit = request.args.get('limit', type=int, default=50)
        offset = request.args.get('offset', type=int, default=0)
        
        with get_db() as db:
            # 只查询当前用户的视频
            query = db.query(VideoLibrary).filter(VideoLibrary.user_id == user_id)
            
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
                # 动态刷新COS URL，确保预签名URL不会过期
                video_url = _refresh_cos_url_if_needed(video.video_url)
                thumbnail_url = _refresh_cos_url_if_needed(video.thumbnail_url) if video.thumbnail_url else None
                
                videos_list.append({
                    'id': video.id,
                    'video_name': video.video_name,
                    'video_url': video_url,
                    'thumbnail_url': thumbnail_url,
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
    
    请求体 (multipart/form-data 或 JSON):
        - 如果上传文件：使用 multipart/form-data
            file: 视频文件（必填）
            thumbnail: 缩略图文件（可选）
            video_name: 视频名称（可选，默认使用文件名）
            platform: 来源平台（可选）
            tags: 标签（可选，逗号分隔）
            description: 描述（可选）
        
        - 如果只保存信息：使用 JSON
            {
                "video_name": "string",       # 必填，视频名称
                "video_url": "string",        # 必填，视频URL（COS URL或本地URL）
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
                "video_url": "string",  # COS URL或本地URL
                "thumbnail_url": "string"
            }
        }
        
        失败 (400/500):
        {
            "code": 400/500,
            "message": "错误信息",
            "data": null
        }
    
    说明:
        - 如果提供了文件，会自动上传到腾讯云COS
        - 如果只提供了URL，则直接保存到数据库
    """
    try:
        # 获取当前用户ID，确保数据隔离
        user_id = get_current_user_id()
        if not user_id:
            return response_error('请先登录', 401)
        
        # 检查是否有文件上传
        if 'file' in request.files and COS_AVAILABLE:
            # 处理文件上传
            file = request.files['file']
            
            if file.filename == '':
                return response_error('No file selected', 400)
            
            # 检查文件类型
            allowed_extensions = {'.mp4', '.mov', '.avi', '.flv', '.wmv', '.webm', '.mkv'}
            filename = secure_filename(file.filename)
            file_ext = os.path.splitext(filename)[1].lower()
            
            if file_ext not in allowed_extensions:
                return response_error(f'File type not allowed. Allowed types: {", ".join(allowed_extensions)}', 400)
            
            # 获取其他参数
            video_name = request.form.get('video_name') or filename
            platform = request.form.get('platform')
            tags = request.form.get('tags')
            description = request.form.get('description')
            
            # 先保存到临时文件
            import tempfile
            temp_dir = tempfile.gettempdir()
            temp_file_path = os.path.join(temp_dir, filename)
            file.save(temp_file_path)
            
            try:
                # 生成COS键
                cos_key = generate_cos_key('video', filename)
                
                # 上传到COS
                upload_result = upload_file_to_cos(temp_file_path, cos_key)
                
                if not upload_result['success']:
                    return response_error(f'上传到COS失败: {upload_result["message"]}', 500)
                
                video_url = upload_result['url']
                video_size = os.path.getsize(temp_file_path)
                
                # 处理缩略图
                thumbnail_url = None
                if 'thumbnail' in request.files:
                    thumbnail_file = request.files['thumbnail']
                    if thumbnail_file.filename:
                        thumbnail_temp_path = os.path.join(temp_dir, secure_filename(thumbnail_file.filename))
                        thumbnail_file.save(thumbnail_temp_path)
                        
                        thumbnail_cos_key = generate_cos_key('thumbnail', secure_filename(thumbnail_file.filename))
                        thumbnail_result = upload_file_to_cos(thumbnail_temp_path, thumbnail_cos_key)
                        
                        if thumbnail_result['success']:
                            thumbnail_url = thumbnail_result['url']
                        
                        # 清理临时文件
                        try:
                            os.remove(thumbnail_temp_path)
                        except:
                            pass
                
                # 保存到数据库
                with get_db() as db:
                    video = VideoLibrary(
                        user_id=user_id,  # 关联当前用户
                        video_name=video_name,
                        video_url=video_url,
                        thumbnail_url=thumbnail_url,
                        video_size=video_size,
                        platform=platform,
                        tags=tags,
                        description=description
                    )
                    db.add(video)
                    db.flush()
                    db.commit()
                    
                    return response_success({
                        'id': video.id,
                        'video_name': video.video_name,
                        'video_url': video.video_url,
                        'thumbnail_url': video.thumbnail_url
                    }, 'Video uploaded to COS', 201)
                
            finally:
                # 清理临时文件
                try:
                    os.remove(temp_file_path)
                except:
                    pass
        
        else:
            # 处理JSON数据（只保存信息，不上传文件）
            data = request.json
            if not data:
                return response_error('No file or data provided', 400)
            
            video_name = data.get('video_name')
            video_url = data.get('video_url')
            
            if not video_name or not video_url:
                return response_error('video_name and video_url are required', 400)
            
            with get_db() as db:
                video = VideoLibrary(
                    user_id=user_id,  # 关联当前用户
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
        import traceback
        traceback.print_exc()
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
            
            # 动态刷新COS URL，确保预签名URL不会过期
            video_url = _refresh_cos_url_if_needed(video.video_url)
            thumbnail_url = _refresh_cos_url_if_needed(video.thumbnail_url) if video.thumbnail_url else None
            
            return response_success({
                'id': video.id,
                'video_name': video.video_name,
                'video_url': video_url,
                'thumbnail_url': thumbnail_url,
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
        # 获取当前用户ID，确保数据隔离
        user_id = get_current_user_id()
        if not user_id:
            return response_error('请先登录', 401)
        
        data = request.json
        with get_db() as db:
            # 只查询当前用户的视频
            video = db.query(VideoLibrary).filter(
                VideoLibrary.id == video_id,
                VideoLibrary.user_id == user_id
            ).first()
            
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
        - 如果视频URL是COS URL，会同时删除COS中的文件
        - 如果视频不存在，返回 404 错误
    """
    try:
        # 获取当前用户ID，确保数据隔离
        user_id = get_current_user_id()
        if not user_id:
            return response_error('请先登录', 401)
        
        with get_db() as db:
            # 只查询当前用户的视频
            video = db.query(VideoLibrary).filter(
                VideoLibrary.id == video_id,
                VideoLibrary.user_id == user_id
            ).first()
            
            if not video:
                return response_error('Video not found', 404)
            
            # 如果视频URL是COS URL，尝试删除COS中的文件
            if COS_AVAILABLE:
                video_url = video.video_url
                from config import COS_DOMAIN, COS_SCHEME, COS_BUCKET, COS_REGION
                if video_url and ('cos.' in video_url or (COS_DOMAIN and COS_DOMAIN in video_url)):
                    try:
                        # 从URL中提取COS键
                        # URL格式：https://bucket.cos.region.myqcloud.com/key 或 https://domain/key
                        if COS_DOMAIN and COS_DOMAIN in video_url:
                            cos_key = video_url.replace(COS_DOMAIN.rstrip('/') + '/', '').lstrip('/')
                        else:
                            # 从默认域名中提取
                            prefix = f"{COS_SCHEME}://{COS_BUCKET}.cos.{COS_REGION}.myqcloud.com/"
                            if video_url.startswith(prefix):
                                cos_key = video_url.replace(prefix, '').lstrip('/')
                            else:
                                cos_key = None
                        
                        if cos_key:
                            delete_result = delete_file_from_cos(cos_key)
                            if not delete_result['success']:
                                print(f"删除COS文件失败: {delete_result['message']}")
                    except Exception as e:
                        print(f"删除COS文件时出错: {e}")
                        # 继续删除数据库记录
                
                # 如果缩略图URL是COS URL，也尝试删除
                if video.thumbnail_url:
                    thumbnail_url = video.thumbnail_url
                    if thumbnail_url and ('cos.' in thumbnail_url or (COS_DOMAIN and COS_DOMAIN in thumbnail_url)):
                        try:
                            if COS_DOMAIN and COS_DOMAIN in thumbnail_url:
                                cos_key = thumbnail_url.replace(COS_DOMAIN.rstrip('/') + '/', '').lstrip('/')
                            else:
                                prefix = f"{COS_SCHEME}://{COS_BUCKET}.cos.{COS_REGION}.myqcloud.com/"
                                if thumbnail_url.startswith(prefix):
                                    cos_key = thumbnail_url.replace(prefix, '').lstrip('/')
                                else:
                                    cos_key = None
                            
                            if cos_key:
                                delete_file_from_cos(cos_key)
                        except Exception as e:
                            print(f"删除COS缩略图时出错: {e}")
            
            db.delete(video)
            db.commit()
            
            return response_success({'video_id': video_id}, 'Video deleted')
    except Exception as e:
        return response_error(str(e), 500)

