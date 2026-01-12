"""
AI 文案生成工具（DeepSeek）
"""
import json
import os
from typing import Any

# 导入配置
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL


def _get_openai_client():
    try:
        from openai import OpenAI
    except Exception as e:
        raise RuntimeError("未安装 openai 依赖，请先 pip install openai") from e

    api_key = (DEEPSEEK_API_KEY or os.environ.get("DEEPSEEK_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("缺少 DEEPSEEK_API_KEY 环境变量")

    base_url = (DEEPSEEK_BASE_URL or os.environ.get("DEEPSEEK_BASE_URL") or "https://api.deepseek.com").strip()
    return OpenAI(api_key=api_key, base_url=base_url)


def deepseek_generate_copies(
    *,
    theme: str,
    keywords: str = "",
    reference: str = "",
    count: int = 3,
    model: str | None = None,
) -> dict[str, Any]:
    """
    返回结构：
    {
      "copies": [
        {"title": "...", "lines": ["...", "..."], "tags": ["..."]}
      ]
    }
    """
    count = int(count)
    count = max(1, min(count, 10))

    client = _get_openai_client()
    model_name = (model or DEEPSEEK_MODEL or "deepseek-chat").strip()

    schema_hint = {
        "copies": [
            {
                "title": "一句话标题/钩子",
                "lines": ["口播文案分句（4~10句，适合直接配音）"],
                "tags": ["可选：风格/情绪标签"],
            }
        ]
    }

    system = (
        "你是短视频口播文案策划助手。"
        "请根据用户给定主题与关键词，生成多条适配 9:16 短视频的口播文案（仅文案，不要分镜/镜头建议/标题卡）。"
        "输出必须是严格 JSON（不要包含任何额外文字），并符合给定 schema。"
    )

    user = """主题：{theme}
关键词：{keywords}
参考文案：{reference}

请生成 {count} 条口播文案（仅文案），默认按 15 秒以内设计。
要求：
- 开头 1~2 秒强钩子（反差/问题/结果先给）
- 中段给出具体信息点/卖点/步骤（避免空话，必须结合关键词写细节）
- 结尾有收束与 CTA（关注/点赞/评论/收藏等），不要过度夸张
- 每条文案必须显式包含关键词（至少出现 1 次）
- lines 写成 4~10 句短句，适合直接配音；不要写"镜头建议/分镜/标题卡"等方案内容
- 语言为中文；尽量贴合参考文案的语气但不要照抄
输出 JSON schema 示例：{schema}""".format(
        theme=theme,
        keywords=keywords,
        reference=reference,
        count=count,
        schema=json.dumps(schema_hint, ensure_ascii=False)
    )

    kwargs: dict[str, Any] = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.7,
        "stream": False,
    }

    # DeepSeek 文档支持 Json Output，这里尽量启用；若不支持则自动回退
    try:
        kwargs["response_format"] = {"type": "json_object"}
    except Exception:
        pass

    resp = client.chat.completions.create(**kwargs)
    content = (resp.choices[0].message.content or "").strip()
    if not content:
        raise RuntimeError("模型未返回内容")

    try:
        data = json.loads(content)
    except Exception:
        # 兜底：把原始文本包起来，避免前端直接崩
        data = {"copies": [], "raw": content}

    copies = data.get("copies")
    if not isinstance(copies, list):
        data["copies"] = []
    return data

