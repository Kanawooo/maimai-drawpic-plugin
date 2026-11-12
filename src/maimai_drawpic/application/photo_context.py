"""只读取官方麦生活公开的当前背景，不生成日程或触发分享。"""

import asyncio
import math
from typing import Any


async def read_life_photo_context(ctx: Any) -> dict[str, str]:
    async def read(name: str) -> dict:
        try:
            async with asyncio.timeout(3):
                value = await ctx.api.call("maibot-community.mai-life." + name, version="1")
            if not isinstance(value, dict):
                raise ValueError("Invalid life snapshot")
            return value
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            ctx.logger.warning("麦生活照片背景读取失败: api=%s error_type=%s", name, type(exc).__name__)
            return {}

    state, scene = await asyncio.gather(read("get_life_state"), read("get_current_scene"))
    current = scene.get("current")
    current = current if isinstance(current, dict) else {}
    result = {}
    for key, value, limit in [
        ("activity", state.get("current_activity") or current.get("summary"), 600),
        ("location", state.get("current_location") or current.get("location"), 160),
    ]:
        if isinstance(value, str) and value.strip():
            result[key] = " ".join(value.replace("\x00", "").split())[:limit]
    mood = state.get("mood_valence")
    if type(mood) in (int, float) and math.isfinite(mood) and -1 <= mood <= 1:
        # 与官方麦生活概览相同的效价值档位，仅传画面需要的心情。
        result["mood"] = ("低落" if mood <= -0.5 else "有些闷" if mood <= -0.15 else
                          "平静" if mood < 0.25 else "不错" if mood < 0.6 else "很好")
    # 官方公开接口不返回天气；保留原绘图描述中的天气，不读取私有数据或另查一份。
    return result
