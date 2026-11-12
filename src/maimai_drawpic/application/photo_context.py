"""麦生活只读照片背景；不生成日程，也不触发主动分享或绘图。"""

from typing import Any
import asyncio


PHOTO_CONTEXT_LIMITS = {"activity": 600, "location": 160, "weather": 160, "mood": 40}


def validate_photo_context(value: Any) -> dict[str, str]:
    if not isinstance(value, dict) or value.keys() - {*PHOTO_CONTEXT_LIMITS, "source_role"}:
        raise ValueError("照片场景只能包含 activity、location、weather、mood 和 source_role")
    result = {}
    for key, limit in PHOTO_CONTEXT_LIMITS.items():
        text = value.get(key, "")
        if not isinstance(text, str) or len(text) > limit or "\x00" in text:
            raise ValueError(f"照片场景 {key} 必须为不超过 {limit} 字的文本")
        if text.strip():
            result[key] = " ".join(text.split())
    role = value.get("source_role", "edit")
    if not isinstance(role, str) or role not in {"identity", "edit"}:
        raise ValueError("source_role 只能是 identity 或 edit")
    if "source_role" in value:
        result["source_role"] = role
    return result


async def read_life_photo_context(ctx: Any) -> dict[str, str]:
    """只调用同实例的公开快照 API；缺失时保留原描述，不编造背景。"""
    try:
        async with asyncio.timeout(3):
            value = await ctx.api.call("maibot-community.mai-life.get_photo_context", version="1")
        context = validate_photo_context(value)
        # 快照不能改变当前请求中用户源图的角色，只有调用方显式声明才可作为身份图。
        context.pop("source_role", None)
        return context
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        ctx.logger.warning("麦生活照片场景不可用，本次保留原描述: error_type=%s", type(exc).__name__)
        return {}
