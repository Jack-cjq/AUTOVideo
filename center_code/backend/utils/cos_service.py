"""
腾讯云COS服务模块
用于上传、下载、删除文件到腾讯云COS
"""
import os
import sys
from typing import Optional
from datetime import datetime
from qcloud_cos import CosConfig
from qcloud_cos import CosS3Client
from qcloud_cos.cos_exception import CosClientError, CosServiceError
try:
    from config import (
        COS_SECRET_ID, COS_SECRET_KEY, COS_REGION, COS_BUCKET, 
        COS_DOMAIN, COS_SCHEME
    )
except ImportError:
    # 如果config中没有这些配置，使用默认值
    import os
    COS_SECRET_ID = os.environ.get("COS_SECRET_ID", "")
    COS_SECRET_KEY = os.environ.get("COS_SECRET_KEY", "")
    COS_REGION = os.environ.get("COS_REGION", "ap-nanjing")
    COS_BUCKET = os.environ.get("COS_BUCKET", "")
    COS_DOMAIN = os.environ.get("COS_DOMAIN", "")
    COS_SCHEME = os.environ.get("COS_SCHEME", "https")

# 初始化COS客户端
_cos_client = None

def get_cos_client():
    """获取COS客户端（单例模式）"""
    global _cos_client
    
    if _cos_client is None:
        if not COS_SECRET_ID or not COS_SECRET_KEY or not COS_BUCKET:
            raise ValueError("COS配置不完整，请设置COS_SECRET_ID、COS_SECRET_KEY和COS_BUCKET")
        
        config = CosConfig(
            Region=COS_REGION,
            SecretId=COS_SECRET_ID,
            SecretKey=COS_SECRET_KEY,
            Scheme=COS_SCHEME
        )
        _cos_client = CosS3Client(config)
    
    return _cos_client


def upload_file_to_cos(local_file_path: str, cos_key: str, content_type: Optional[str] = None) -> dict:
    """
    上传文件到COS
    
    Args:
        local_file_path: 本地文件路径
        cos_key: COS中的对象键（文件路径）
        content_type: 文件MIME类型（可选）
    
    Returns:
        {
            'success': bool,
            'url': str,  # 文件访问URL
            'key': str,  # COS对象键
            'message': str
        }
    """
    try:
        if not os.path.exists(local_file_path):
            return {
                'success': False,
                'url': None,
                'key': None,
                'message': f'本地文件不存在: {local_file_path}'
            }
        
        client = get_cos_client()
        
        # 如果没有指定content_type，根据文件扩展名自动判断
        if not content_type:
            ext = os.path.splitext(local_file_path)[1].lower()
            content_type_map = {
                '.mp4': 'video/mp4',
                '.mov': 'video/quicktime',
                '.avi': 'video/x-msvideo',
                '.flv': 'video/x-flv',
                '.wmv': 'video/x-ms-wmv',
                '.webm': 'video/webm',
                '.mkv': 'video/x-matroska',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.webp': 'image/webp'
            }
            content_type = content_type_map.get(ext, 'application/octet-stream')
        
        # 上传文件
        with open(local_file_path, 'rb') as fp:
            response = client.put_object(
                Bucket=COS_BUCKET,
                Body=fp,
                Key=cos_key,
                ContentType=content_type
            )
        
        # 生成文件URL（对于私有存储桶，使用预签名URL）
        # 注意：上传成功后，返回的URL应该是预签名URL，以便客户端可以直接访问
        try:
            file_url = get_file_url(cos_key, use_presigned=True, expires_in=86400 * 7)  # 7天有效期
        except Exception as url_error:
            # 如果生成预签名URL失败，使用普通URL
            print(f"[COS] 生成预签名URL失败: {url_error}，使用普通URL")
            if COS_DOMAIN:
                file_url = f"{COS_DOMAIN.rstrip('/')}/{cos_key.lstrip('/')}"
            else:
                file_url = f"{COS_SCHEME}://{COS_BUCKET}.cos.{COS_REGION}.myqcloud.com/{cos_key.lstrip('/')}"
        
        return {
            'success': True,
            'url': file_url,
            'key': cos_key,
            'message': '上传成功'
        }
        
    except CosClientError as e:
        return {
            'success': False,
            'url': None,
            'key': None,
            'message': f'COS客户端错误: {str(e)}'
        }
    except CosServiceError as e:
        return {
            'success': False,
            'url': None,
            'key': None,
            'message': f'COS服务错误: {str(e)}'
        }
    except Exception as e:
        return {
            'success': False,
            'url': None,
            'key': None,
            'message': f'上传失败: {str(e)}'
        }


def upload_file_data_to_cos(file_data: bytes, cos_key: str, content_type: Optional[str] = None) -> dict:
    """
    上传文件数据到COS（从内存中上传）
    
    Args:
        file_data: 文件数据（bytes）
        cos_key: COS中的对象键（文件路径）
        content_type: 文件MIME类型（可选）
    
    Returns:
        {
            'success': bool,
            'url': str,  # 文件访问URL
            'key': str,  # COS对象键
            'message': str
        }
    """
    try:
        client = get_cos_client()
        
        # 如果没有指定content_type，根据文件扩展名自动判断
        if not content_type:
            ext = os.path.splitext(cos_key)[1].lower()
            content_type_map = {
                '.mp4': 'video/mp4',
                '.mov': 'video/quicktime',
                '.avi': 'video/x-msvideo',
                '.flv': 'video/x-flv',
                '.wmv': 'video/x-ms-wmv',
                '.webm': 'video/webm',
                '.mkv': 'video/x-matroska',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.webp': 'image/webp'
            }
            content_type = content_type_map.get(ext, 'application/octet-stream')
        
        # 上传文件数据
        response = client.put_object(
            Bucket=COS_BUCKET,
            Body=file_data,
            Key=cos_key,
            ContentType=content_type
        )
        
        # 生成文件URL
        if COS_DOMAIN:
            # 使用自定义域名
            file_url = f"{COS_DOMAIN.rstrip('/')}/{cos_key.lstrip('/')}"
        else:
            # 使用默认域名
            file_url = f"{COS_SCHEME}://{COS_BUCKET}.cos.{COS_REGION}.myqcloud.com/{cos_key.lstrip('/')}"
        
        return {
            'success': True,
            'url': file_url,
            'key': cos_key,
            'message': '上传成功'
        }
        
    except CosClientError as e:
        return {
            'success': False,
            'url': None,
            'key': None,
            'message': f'COS客户端错误: {str(e)}'
        }
    except CosServiceError as e:
        return {
            'success': False,
            'url': None,
            'key': None,
            'message': f'COS服务错误: {str(e)}'
        }
    except Exception as e:
        return {
            'success': False,
            'url': None,
            'key': None,
            'message': f'上传失败: {str(e)}'
        }


def delete_file_from_cos(cos_key: str) -> dict:
    """
    从COS删除文件
    
    Args:
        cos_key: COS中的对象键（文件路径）
    
    Returns:
        {
            'success': bool,
            'message': str
        }
    """
    try:
        client = get_cos_client()
        
        response = client.delete_object(
            Bucket=COS_BUCKET,
            Key=cos_key
        )
        
        return {
            'success': True,
            'message': '删除成功'
        }
        
    except CosClientError as e:
        return {
            'success': False,
            'message': f'COS客户端错误: {str(e)}'
        }
    except CosServiceError as e:
        return {
            'success': False,
            'message': f'COS服务错误: {str(e)}'
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'删除失败: {str(e)}'
        }


def get_file_url(cos_key: str, use_presigned: bool = True, expires_in: int = 3600) -> str:
    """
    获取文件的访问URL
    
    Args:
        cos_key: COS中的对象键（文件路径）
        use_presigned: 是否使用预签名URL（对于私有存储桶必须为True），默认True
        expires_in: 预签名URL有效期（秒），默认3600秒（1小时）
    
    Returns:
        文件访问URL（如果是私有存储桶，返回预签名URL）
    """
    try:
        if use_presigned:
            # 对于私有存储桶，生成预签名URL
            client = get_cos_client()
            url = client.get_presigned_download_url(
                Bucket=COS_BUCKET,
                Key=cos_key,
                Expired=expires_in
            )
            return url
        else:
            # 对于公有存储桶，使用普通URL
            if COS_DOMAIN:
                # 使用自定义域名
                return f"{COS_DOMAIN.rstrip('/')}/{cos_key.lstrip('/')}"
            else:
                # 使用默认域名
                return f"{COS_SCHEME}://{COS_BUCKET}.cos.{COS_REGION}.myqcloud.com/{cos_key.lstrip('/')}"
    except Exception as e:
        # 如果生成预签名URL失败，回退到普通URL
        print(f"[COS] 生成预签名URL失败: {e}，使用普通URL")
        if COS_DOMAIN:
            return f"{COS_DOMAIN.rstrip('/')}/{cos_key.lstrip('/')}"
        else:
            return f"{COS_SCHEME}://{COS_BUCKET}.cos.{COS_REGION}.myqcloud.com/{cos_key.lstrip('/')}"


def list_objects_from_cos(prefix: str = 'video/', max_keys: int = 1000) -> dict:
    """
    从COS列出对象（文件）
    
    Args:
        prefix: 对象键前缀，用于筛选（例如 'video/' 只列出video目录下的文件）
        max_keys: 最多返回的对象数量，默认1000
    
    Returns:
        {
            'success': bool,
            'objects': list,  # 对象列表，每个对象包含 {'key': str, 'size': int, 'last_modified': str, 'url': str}
            'count': int,     # 对象数量
            'message': str
        }
    """
    try:
        client = get_cos_client()
        
        # 列出对象
        response = client.list_objects(
            Bucket=COS_BUCKET,
            Prefix=prefix,
            MaxKeys=max_keys
        )
        
        objects = []
        if 'Contents' in response:
            for obj in response['Contents']:
                cos_key = obj['Key']
                # 只返回视频文件
                if cos_key.lower().endswith(('.mp4', '.mov', '.avi', '.flv', '.wmv', '.webm', '.mkv')):
                    # 生成预签名URL（私有存储桶需要）
                    file_url = get_file_url(cos_key, use_presigned=True, expires_in=3600)
                    objects.append({
                        'key': cos_key,
                        'size': obj.get('Size', 0),
                        'last_modified': obj.get('LastModified', ''),
                        'url': file_url,
                        'filename': os.path.basename(cos_key)
                    })
        
        return {
            'success': True,
            'objects': objects,
            'count': len(objects),
            'message': f'成功获取 {len(objects)} 个对象'
        }
        
    except CosClientError as e:
        return {
            'success': False,
            'objects': [],
            'count': 0,
            'message': f'COS客户端错误: {str(e)}'
        }
    except CosServiceError as e:
        error_msg = str(e)
        # 检查是否是权限错误
        if 'AccessDenied' in error_msg or 'access denied' in error_msg.lower():
            error_msg = ('COS访问权限不足，请检查SecretId和SecretKey是否有以下权限：\n'
                        '1. 列出对象权限（ListBucket）- 需要添加 QcloudCOSDataRead 或 QcloudCOSDataReadWrite 策略\n'
                        '2. 如果只有 OnlyRead 和 OnlyWrite，需要添加包含 ListBucket 操作的权限策略\n'
                        '3. 建议使用 QcloudCOSDataReadWrite（COS数据读写权限）或 QcloudCOSBucketReadWrite（存储桶读写权限）')
        return {
            'success': False,
            'objects': [],
            'count': 0,
            'message': f'COS服务错误: {error_msg}'
        }
    except Exception as e:
        return {
            'success': False,
            'objects': [],
            'count': 0,
            'message': f'列出对象失败: {str(e)}'
        }


def generate_cos_key(file_type: str = 'video', filename: str = None) -> str:
    """
    生成COS对象键（文件路径）
    
    Args:
        file_type: 文件类型（video/thumbnail/audio等）
        filename: 文件名（可选，如果不提供则自动生成）
    
    Returns:
        COS对象键，格式：{file_type}/{year}/{month}/{day}/{filename}
    """
    if not filename:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        filename = f"{timestamp}.mp4"
    
    # 生成日期路径
    date_path = datetime.now().strftime('%Y/%m/%d')
    
    # 生成COS键
    cos_key = f"{file_type}/{date_path}/{filename}"
    
    return cos_key

