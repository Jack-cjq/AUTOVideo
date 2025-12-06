import asyncio
from pathlib import Path

from conf import BASE_DIR
from listener.douyin_listener.main import douyin_chat_main


if __name__ == '__main__':
    # 复用上传/获取 cookie 时使用的同一份账号 cookie 文件
    account_file = Path(BASE_DIR / "cookies" / "douyin_uploader" / "account.json")
    account_file.parent.mkdir(exist_ok=True)

    # 默认认为你已经通过 get_douyin_cookie.py 登陆并生成了 cookie
    # 若 cookie 失效，抖音页面可能会自动跳转到登录界面。
    asyncio.run(douyin_chat_main(str(account_file)))


