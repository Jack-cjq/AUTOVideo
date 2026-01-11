from pathlib import Path
from typing import List

from conf import BASE_DIR

SOCIAL_MEDIA_DOUYIN = "douyin"
SOCIAL_MEDIA_TENCENT = "tencent"
SOCIAL_MEDIA_TIKTOK = "tiktok"
SOCIAL_MEDIA_BILIBILI = "bilibili"
SOCIAL_MEDIA_KUAISHOU = "kuaishou"


def get_supported_social_media() -> List[str]:
    return [SOCIAL_MEDIA_DOUYIN, SOCIAL_MEDIA_TENCENT, SOCIAL_MEDIA_TIKTOK, SOCIAL_MEDIA_KUAISHOU]


def get_cli_action() -> List[str]:
    return ["upload", "login", "watch"]


async def set_init_script(context):
    """
    设置反检测脚本到浏览器上下文
    包括通用的 stealth.min.js 和针对抖音的增强脚本
    """
    # 1. 加载通用的反检测脚本
    stealth_js_path = Path(BASE_DIR / "utils/stealth.min.js")
    if stealth_js_path.exists():
        await context.add_init_script(path=stealth_js_path)
    
    # 2. 加载针对抖音的增强反检测脚本
    douyin_stealth_js_path = Path(BASE_DIR / "utils/douyin_stealth.js")
    if douyin_stealth_js_path.exists():
        await context.add_init_script(path=douyin_stealth_js_path)
    
    return context
