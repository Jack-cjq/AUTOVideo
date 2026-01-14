"""Auth API (JWT + email registration)"""

import os
import re
import random
import uuid
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText

from flask import Blueprint, request
from werkzeug.utils import secure_filename

from utils import response_success, response_error, create_access_token, decode_access_token
from models import User, EmailVerification
from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM, SMTP_USE_SSL, SMTP_USE_TLS
from db import get_db


auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


EMAIL_REGEX = re.compile(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
# 密码正则表达式：至少8个字符，包含大小写字母、数字和特殊字符
PASSWORD_REGEX = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$')


def _is_valid_email(email):
    return bool(email and EMAIL_REGEX.match(email))


def _send_verification_email(to_email, code):
    smtp_host = SMTP_HOST
    smtp_port = SMTP_PORT
    smtp_user = SMTP_USER
    smtp_password = SMTP_PASSWORD
    smtp_from = SMTP_FROM
    use_tls = SMTP_USE_TLS
    use_ssl = SMTP_USE_SSL

    if not smtp_host or not smtp_user or not smtp_password or not smtp_from:
        raise RuntimeError('SMTP config missing')

    subject = 'Your verification code'
    body = f'Your verification code is: {code}. It expires in 10 minutes.'
    message = MIMEText(body, 'plain', 'utf-8')
    message['Subject'] = subject
    message['From'] = smtp_from
    message['To'] = to_email

    if smtp_port == 465 or use_ssl:
        server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
    else:
        server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)

    try:
        if use_tls and smtp_port != 465 and not use_ssl:
            server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_from, [to_email], message.as_string())
    finally:
        server.quit()


def _normalize_avatar_url(avatar_url):
    if not avatar_url:
        return ''
    if avatar_url.startswith('http://') or avatar_url.startswith('https://'):
        return avatar_url
    return request.host_url.rstrip('/') + avatar_url


def _issue_code(email):
    code = f"{random.randint(0, 999999):06d}"
    expires_at = datetime.utcnow() + timedelta(minutes=10)
    with get_db() as db:
        record = EmailVerification(
            email=email,
            code=code,
            expires_at=expires_at
        )
        db.add(record)
        db.commit()
    return code


@auth_bp.route('/send-code', methods=['POST'])
def send_code():
    data = request.json or {}
    email = (data.get('email') or '').strip().lower()

    if not _is_valid_email(email):
        return response_error('无效的邮箱', 400)

    code = _issue_code(email)
    try:
        _send_verification_email(email, code)
    except Exception as exc:
        return response_error(f'发送邮件失败: {exc}', 500)

    return response_success({'email': email}, '验证码已发送', 200)


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.json or {}
    username = (data.get('username') or '').strip()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    code = (data.get('code') or '').strip()

    if not username:
        return response_error('用户名不能为空', 400)
    if not _is_valid_email(email):
        return response_error('无效的邮箱', 400)
    if not password:
        return response_error('密码不能为空', 400)
    if not PASSWORD_REGEX.match(password):
        return response_error('密码必须包含至少8个字符，包括大小写字母、数字和特殊字符', 400)
    if not code:
        return response_error('验证码不能为空', 400)

    with get_db() as db:
        existing_name = db.query(User).filter(User.username == username).first()
        if existing_name:
            return response_error('用户名已被注册', 400)
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            return response_error('邮箱已被注册', 400)

        verif = db.query(EmailVerification).filter(
            EmailVerification.email == email,
            EmailVerification.code == code,
            EmailVerification.used_at.is_(None)
        ).order_by(EmailVerification.created_at.desc()).first()

        if not verif:
            return response_error('无效的验证码', 400)
        if verif.expires_at < datetime.utcnow():
            return response_error('验证码已过期', 400)

        user = User(username=username, email=email, is_verified=True)
        user.set_password(password)
        db.add(user)
        verif.used_at = datetime.utcnow()
        db.commit()

    return response_success({'email': email}, '注册成功', 201)


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json or {}
    mode = (data.get('mode') or 'password').strip().lower()

    if mode == 'code':
        email = (data.get('email') or '').strip().lower()
        code = (data.get('code') or '').strip()
        if not _is_valid_email(email):
            return response_error('无效的邮箱', 400)
        if not code:
                return response_error('验证码不能为空', 400)

        with get_db() as db:
            verif = db.query(EmailVerification).filter(
                EmailVerification.email == email,
                EmailVerification.code == code,
                EmailVerification.used_at.is_(None)
            ).order_by(EmailVerification.created_at.desc()).first()

            if not verif:
                return response_error('无效的验证码', 401)
            if verif.expires_at < datetime.utcnow():
                return response_error('验证码已过期', 401)

            user = db.query(User).filter(User.email == email).first()
            if not user:
                return response_error('用户不存在', 404)
            
            # 用户使用邮箱验证码登录，验证成功后自动设置为已验证
            user.is_verified = True

            verif.used_at = datetime.utcnow()
            user_id = user.id
            username = user.username
            email_value = user.email
            avatar_url = _normalize_avatar_url(user.avatar_url)
            token = create_access_token(user_id, username, email_value)

        return response_success({
            'token': token,
            'username': username,
            'email': email_value,
            'avatar_url': avatar_url
        }, '登录成功', 200)

    login_id = (data.get('username') or data.get('email') or '').strip()
    password = data.get('password') or ''

    if not login_id or not password:
        return response_error('用户名或邮箱和密码不能为空', 400)

    with get_db() as db:
        user = db.query(User).filter(
            (User.email == login_id.lower()) | (User.username == login_id)
        ).first()

        if not user or not user.check_password(password):
            return response_error('用户名或密码错误', 401)
        
        # 密码登录时，如果使用用户名登录，可以绕过邮箱验证检查
        # 这样用户即使更换邮箱后未验证也能登录
        if not user.is_verified and login_id.lower() != user.email:
            # 用户使用用户名登录，允许登录
            pass
        elif not user.is_verified:
            # 用户使用邮箱登录，但邮箱未验证，阻止登录
            return response_error('邮箱未验证', 403)

        user_id = user.id
        username = user.username
        email_value = user.email
        avatar_url = _normalize_avatar_url(user.avatar_url)
        token = create_access_token(user_id, username, email_value)

    return response_success({
        'token': token,
        'username': username,
        'email': email_value,
        'avatar_url': avatar_url
    }, 'Login success', 200)


@auth_bp.route('/logout', methods=['POST'])
def logout():
    return response_success(None, '退出成功', 200)


@auth_bp.route('/check', methods=['GET'])
def check():
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return response_success({'logged_in': False}, 'success', 200)

    token = auth_header.split(' ', 1)[1].strip()
    try:
        payload = decode_access_token(token)
    except Exception:
        return response_success({'logged_in': False}, 'success', 200)

    user_id = payload.get('sub')
    if not user_id:
        return response_success({'logged_in': False}, 'success', 200)
    try:
        user_id = int(user_id)
    except ValueError:
        return response_success({'logged_in': False}, 'success', 200)

    with get_db() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return response_success({'logged_in': False}, 'success', 200)
        avatar_url = _normalize_avatar_url(user.avatar_url)

    return response_success({
        'logged_in': True,
        'username': payload.get('username'),
        'email': payload.get('email'),
        'avatar_url': avatar_url
    }, 'success', 200)


def _get_current_user_id():
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    token = auth_header.split(' ', 1)[1].strip()
    try:
        payload = decode_access_token(token)
    except Exception:
        return None
    user_id = payload.get('sub')
    if not user_id:
        return None
    try:
        user_id = int(user_id)
    except ValueError:
        return None
    return user_id


@auth_bp.route('/profile', methods=['GET'])
def get_profile():
    user_id = _get_current_user_id()
    if not user_id:
        return response_error('请先登录', 401)
    with get_db() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return response_error('用户不存在', 404)
        payload = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'avatar_url': _normalize_avatar_url(user.avatar_url),
            'is_verified': user.is_verified
        }
    return response_success(payload)


@auth_bp.route('/profile', methods=['PUT'])
def update_profile():
    user_id = _get_current_user_id()
    if not user_id:
        return response_error('Please log in', 401)

    data = request.json or {}
    username = (data.get('username') or '').strip()
    email = (data.get('email') or '').strip().lower()
    
    if not username:
        return response_error('用户名不能为空', 400)
    
    with get_db() as db:
        existing = db.query(User).filter(User.username == username, User.id != user_id).first()
        if existing:
            return response_error('用户名已被注册', 400)
        
        # 检查邮箱是否已被其他用户使用
        if email and email != '':
            existing_email = db.query(User).filter(User.email == email, User.id != user_id).first()
            if existing_email:
                return response_error('邮箱已被注册', 400)
        
        target = db.query(User).filter(User.id == user_id).first()
        if not target:
            return response_error('User not found', 404)
            
        target.username = username
        if email and email != '':
            target.email = email
            target.is_verified = False  # 更换邮箱后需要重新验证
        
        db.commit()

    return response_success({'username': username, 'email': target.email}, 'Profile updated')


@auth_bp.route('/verify-password', methods=['POST'])
def verify_password():
    user_id = _get_current_user_id()
    if not user_id:
        return response_error('Please log in', 401)

    data = request.json or {}
    old_password = data.get('old_password') or ''
    if not old_password:
        return response_error('旧密码不能为空', 400)

    with get_db() as db:
        target = db.query(User).filter(User.id == user_id).first()
        if not target:
            return response_error('User not found', 404)
        if not target.check_password(old_password):
            return response_error('旧密码错误', 400)

    return response_success(None, 'Password verified')


@auth_bp.route('/password', methods=['POST'])
def change_password():
    user_id = _get_current_user_id()
    if not user_id:
        return response_error('Please log in', 401)

    data = request.json or {}
    old_password = data.get('old_password') or ''
    new_password = data.get('new_password') or ''
    if not old_password or not new_password:
        return response_error('旧密码和新密码不能为空', 400)
    
    # 检查新密码与原密码是否相同
    if new_password == old_password:
        return response_error('新密码不能与原密码相同', 400)
    
    # 检查密码长度
    if len(new_password) < 8 or len(new_password) > 20:
        return response_error('密码长度必须在8-20个字符之间', 400)
    
    # 检查密码复杂度（包含大小写字母、数字和特殊字符）
    has_lower = any(c.islower() for c in new_password)
    has_upper = any(c.isupper() for c in new_password)
    has_digit = any(c.isdigit() for c in new_password)
    has_special = any(c in '@$!%*?&' for c in new_password)
    
    if not (has_lower and has_upper and has_digit and has_special):
        return response_error('密码必须包含至少一个大写字母、一个小写字母、一个数字和一个特殊字符', 400)

    with get_db() as db:
        target = db.query(User).filter(User.id == user_id).first()
        if not target:
            return response_error('User not found', 404)
        if not target.check_password(old_password):
            return response_error('旧密码错误', 400)
        target.set_password(new_password)
        db.commit()

    return response_success(None, 'Password updated')


@auth_bp.route('/avatar', methods=['POST'])
def upload_avatar():
    user_id = _get_current_user_id()
    if not user_id:
        return response_error('Please log in', 401)

    if 'avatar' not in request.files:
        return response_error('未提供头像文件', 400)

    file = request.files['avatar']
    if not file or not file.filename:
        return response_error('No avatar file provided', 400)

    filename = secure_filename(file.filename)
    ext = os.path.splitext(filename)[1].lower()
    if ext not in {'.png', '.jpg', '.jpeg', '.gif', '.webp'}:
        return response_error('Unsupported file type', 400)

    upload_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'uploads',
        'avatars'
    )
    os.makedirs(upload_dir, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(upload_dir, stored_name)
    file.save(file_path)

    avatar_url = f"/uploads/avatars/{stored_name}"
    with get_db() as db:
        target = db.query(User).filter(User.id == user_id).first()
        if not target:
            return response_error('User not found', 404)
        target.avatar_url = avatar_url
        db.commit()

    return response_success({'avatar_url': _normalize_avatar_url(avatar_url)}, 'Avatar updated')


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """
    发送重置密码验证码接口
    
    请求方法: POST
    路径: /api/auth/forgot-password
    认证: 不需要登录
    
    请求数据:
        {
            "email": "user@example.com"
        }
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "Code sent",
            "data": {"email": "user@example.com"}
        }
        
        失败 (400/500):
        {
            "code": 400,
            "message": "错误信息",
            "data": null
        }
    """
    data = request.json or {}
    email = (data.get('email') or '').strip().lower()

    if not _is_valid_email(email):
        return response_error('无效的邮箱', 400)

    # 检查用户是否存在
    with get_db() as db:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            # 为了安全，即使邮箱不存在也返回成功消息，不泄露用户信息
            return response_success({'email': email}, 'Code sent', 200)

    # 发送验证码
    try:
        code = _issue_code(email)
        _send_verification_email(email, code)
    except Exception as exc:
        return response_error(f'Failed to send email: {exc}', 500)

    return response_success({'email': email}, 'Code sent', 200)


@auth_bp.route('/change-email/send-code', methods=['POST'])
def send_change_email_code():
    """
    发送更换邮箱验证码接口
    
    请求方法: POST
    路径: /api/auth/change-email/send-code
    认证: 需要登录
    
    请求数据:
        {
            "new_email": "new@example.com"
        }
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "Code sent",
            "data": {"new_email": "new@example.com"}
        }
        
        失败 (400/500):
        {
            "code": 400,
            "message": "错误信息",
            "data": null
        }
    """
    user_id = _get_current_user_id()
    if not user_id:
        return response_error('Please log in', 401)

    data = request.json or {}
    new_email = (data.get('new_email') or '').strip().lower()

    if not _is_valid_email(new_email):
        return response_error('无效的邮箱', 400)

    with get_db() as db:
        # 检查新邮箱是否已被其他用户使用
        existing = db.query(User).filter(User.email == new_email, User.id != user_id).first()
        if existing:
            return response_error('邮箱已被注册', 400)

    # 发送验证码
    try:
        code = _issue_code(new_email)
        _send_verification_email(new_email, code)
    except Exception as exc:
        return response_error(f'Failed to send email: {exc}', 500)

    return response_success({'new_email': new_email}, 'Code sent', 200)


@auth_bp.route('/check-email', methods=['POST'])
def check_email():
    """
    检查邮箱是否已被使用的接口
    
    请求方法: POST
    路径: /api/auth/check-email
    认证: 需要登录
    
    请求数据:
        {
            "email": "new_email@example.com"
        }
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "Email checked",
            "data": {"exists": true/false}
        }
        
        失败 (400):
        {
            "code": 400,
            "message": "无效的邮箱",
            "data": null
        }
    """
    data = request.json or {}
    email = (data.get('email') or '').strip().lower()
    
    if not _is_valid_email(email):
        return response_error('无效的邮箱', 400)
    
    with get_db() as db:
        # 获取当前用户ID，排除当前用户自己
        user_id = _get_current_user_id() or 0
        
        # 检查邮箱是否存在（排除当前用户）
        existing = db.query(User).filter(
            User.email == email,
            User.id != user_id
        ).first()
        
        return response_success({'exists': existing is not None}, 'Email checked')


@auth_bp.route('/check-username', methods=['POST'])
def check_username():
    """
    检查用户名是否已被使用的接口
    
    请求方法: POST
    路径: /api/auth/check-username
    认证: 需要登录
    
    请求数据:
        {
            "username": "new_username"
        }
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "Username checked",
            "data": {"exists": true/false}
        }
        
        失败 (400):
        {
            "code": 400,
            "message": "Invalid username",
            "data": null
        }
    """
    data = request.json or {}
    username = (data.get('username') or '').strip()
    
    if not username:
        return response_error('Invalid username', 400)
    
    with get_db() as db:
        # 获取当前用户ID，排除当前用户自己
        user_id = _get_current_user_id() or 0
        
        # 检查用户名是否存在（排除当前用户）
        existing = db.query(User).filter(
            User.username == username,
            User.id != user_id
        ).first()
        
        return response_success({'exists': existing is not None}, 'Username checked')


@auth_bp.route('/update-profile', methods=['PUT'])
def update_profile_only():
    """
    只更新用户名接口
    
    请求方法: PUT
    路径: /api/auth/update-profile
    认证: 需要登录
    
    请求数据:
        {
            "username": "new_username"
        }
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "Profile updated",
            "data": {
                "username": "new_username"
            }
        }
        
        失败 (400/404):
        {
            "code": 400,
            "message": "错误信息",
            "data": null
        }
    """
    user_id = _get_current_user_id()
    if not user_id:
        return response_error('Please log in', 401)

    data = request.json or {}
    username = (data.get('username') or '').strip()

    if not username:
        return response_error('用户名不能为空', 400)
    
    # 验证用户名长度
    if len(username) < 2 or len(username) > 16:
        return response_error('用户名长度必须在2-16个字符之间', 400)
    
    # 验证用户名格式（只能包含中英文和数字）
    import re
    if not re.match(r'^[\u4e00-\u9fa5a-zA-Z0-9]+$', username):
        return response_error('用户名只能包含中英文和数字', 400)

    with get_db() as db:
        # 检查用户名是否已被其他用户使用
        existing_username = db.query(User).filter(User.username == username, User.id != user_id).first()
        if existing_username:
            return response_error('Username already registered', 400)

        # 更新用户信息
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return response_error('User not found', 404)

        user.username = username
        db.commit()

    return response_success({'username': username}, 'Profile updated', 200)


@auth_bp.route('/change-email/send-old-code', methods=['POST'])
def send_old_email_code():
    """
    发送原邮箱验证码的接口
    
    请求方法: POST
    路径: /api/auth/change-email/send-old-code
    认证: 需要登录
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "Code sent to old email",
            "data": {"email": "old@example.com"}
        }
        
        失败 (400/500):
        {
            "code": 400,
            "message": "Error sending code",
            "data": null
        }
    """
    user_id = _get_current_user_id()
    if not user_id:
        return response_error('Please log in', 401)

    with get_db() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return response_error('User not found', 404)

        user_email = user.email  # 在会话内部保存邮箱地址

        # 发送验证码到原邮箱
        try:
            code = _issue_code(user_email)
            _send_verification_email(user_email, code)
        except Exception as exc:
            return response_error(f'Failed to send email: {exc}', 500)

    return response_success({'email': user_email}, 'Code sent to old email', 200)


@auth_bp.route('/change-email/verify-old-code', methods=['POST'])
def verify_old_email_code():
    """
    验证原邮箱验证码的接口
    
    请求方法: POST
    路径: /api/auth/change-email/verify-old-code
    认证: 需要登录
    
    请求数据:
        {
            "code": "123456"
        }
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "Old email code verified",
            "data": {"verified": true}
        }
        
        失败 (400):
        {
            "code": 400,
            "message": "Invalid or expired verification code",
            "data": null
        }
    """
    user_id = _get_current_user_id()
    if not user_id:
        return response_error('Please log in', 401)

    data = request.json or {}
    code = data.get('code')

    if not code:
        return response_error('验证码无效', 400)

    with get_db() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return response_error('User not found', 404)

        # 验证原邮箱验证码
        verification = db.query(EmailVerification).filter(
            EmailVerification.email == user.email,
            EmailVerification.code == code,
            EmailVerification.used_at.is_(None),
            EmailVerification.expires_at > datetime.utcnow()
        ).first()

        if not verification:
            return response_error('Invalid or expired verification code', 400)

    return response_success({'verified': True}, 'Old email code verified', 200)


@auth_bp.route('/change-email/send-new-code', methods=['POST'])
def send_new_email_code():
    """
    发送新邮箱验证码的接口
    
    请求方法: POST
    路径: /api/auth/change-email/send-new-code
    认证: 需要登录
    
    请求数据:
        {
            "new_email": "new@example.com"
        }
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "Code sent to new email",
            "data": {"email": "new@example.com"}
        }
        
        失败 (400/500):
        {
            "code": 400,
            "message": "Error sending code",
            "data": null
        }
    """
    user_id = _get_current_user_id()
    if not user_id:
        return response_error('Please log in', 401)

    data = request.json or {}
    new_email = (data.get('new_email') or '').strip().lower()

    if not _is_valid_email(new_email):
        return response_error('无效的邮箱', 400)

    with get_db() as db:
        # 检查新邮箱是否已被其他用户使用
        existing = db.query(User).filter(User.email == new_email, User.id != user_id).first()
        if existing:
            return response_error('Email already registered', 400)

    # 发送验证码到新邮箱
    try:
        code = _issue_code(new_email)
        _send_verification_email(new_email, code)
    except Exception as exc:
        return response_error(f'Failed to send email: {exc}', 500)

    return response_success({'email': new_email}, 'Code sent to new email', 200)


@auth_bp.route('/change-email/verify', methods=['POST'])
def verify_change_email():
    """
    验证更换邮箱的验证码并更新邮箱和/或用户名接口
    
    请求方法: POST
    路径: /api/auth/change-email/verify
    认证: 需要登录
    
    请求数据:
        {
            "new_email": "new@example.com",
            "new_code": "789012",  # 新邮箱验证码
            "username": "new_username"
        }
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "Profile updated",
            "data": {
                "username": "new_username",
                "email": "new@example.com"
            }
        }
        
        失败 (400/404):
        {
            "code": 400,
            "message": "错误信息",
            "data": null
        }
    """
    user_id = _get_current_user_id()
    if not user_id:
        return response_error('Please log in', 401)

    data = request.json or {}
    new_email = (data.get('new_email') or '').strip().lower()
    new_code = data.get('new_code')
    username = (data.get('username') or '').strip()

    if not _is_valid_email(new_email) or not new_code or not username:
        return response_error('无效的邮箱、验证码或用户名', 400)

    with get_db() as db:
        # 获取当前用户信息
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return response_error('User not found', 404)
        
        # 检查邮箱是否发生变化
        email_changed = new_email != user.email
        
        if email_changed:
            # 验证新邮箱验证码
            new_verification = db.query(EmailVerification).filter(
                EmailVerification.email == new_email,
                EmailVerification.code == new_code,
                EmailVerification.used_at.is_(None),
                EmailVerification.expires_at > datetime.utcnow()
            ).first()

            if not new_verification:
                return response_error('Invalid or expired new email verification code', 400)

            # 检查新邮箱是否已被其他用户使用
            existing_email = db.query(User).filter(User.email == new_email, User.id != user_id).first()
            if existing_email:
                return response_error('Email already registered', 400)

        # 检查用户名是否已被其他用户使用
        existing_username = db.query(User).filter(User.username == username, User.id != user_id).first()
        if existing_username:
            return response_error('Username already registered', 400)

        # 更新用户信息
        user.username = username
        if email_changed:
            user.email = new_email
            user.is_verified = True  # 用户已验证新邮箱，直接标记为已验证
            new_verification.used_at = datetime.utcnow()

        # 保存最终的email值用于返回
        final_email = new_email if email_changed else user.email
        db.commit()

    return response_success({'username': username, 'email': final_email}, 'Profile updated', 200)


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """
    重置密码接口
    
    请求方法: POST
    路径: /api/auth/reset-password
    认证: 不需要登录
    
    请求数据:
        {
            "email": "user@example.com",
            "code": "123456",
            "password": "new_password"
        }
    
    返回数据:
        成功 (200):
        {
            "code": 200,
            "message": "Password reset",
            "data": {"email": "user@example.com"}
        }
        
        失败 (400):
        {
            "code": 400,
            "message": "错误信息",
            "data": null
        }
    """
    data = request.json or {}
    email = (data.get('email') or '').strip().lower()
    code = (data.get('code') or '').strip()
    password = data.get('password') or ''

    if not _is_valid_email(email):
        return response_error('无效的邮箱', 400)
    if not code:
        return response_error('Verification code is required', 400)
    if not password:
        return response_error('Password is required', 400)
    if not PASSWORD_REGEX.match(password):
        return response_error('Password must contain at least 8 characters, including uppercase and lowercase letters, numbers, and special characters', 400)

    with get_db() as db:
        # 验证验证码
        verif = db.query(EmailVerification).filter(
            EmailVerification.email == email,
            EmailVerification.code == code,
            EmailVerification.used_at.is_(None)
        ).order_by(EmailVerification.created_at.desc()).first()

        if not verif:
            return response_error('验证码无效', 400)
        if verif.expires_at < datetime.utcnow():
            return response_error('Verification code expired', 400)

        # 查找用户
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return response_error('User not found', 404)

        # 更新密码
        user.set_password(password)
        verif.used_at = datetime.utcnow()
        db.commit()

    return response_success({'email': email}, 'Password reset', 200)
