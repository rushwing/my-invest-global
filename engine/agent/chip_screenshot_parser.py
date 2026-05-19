"""Phase 11 — 同花顺截图 OCR 解析 (REQ-038).

Fallback path: Claude Vision API parses chip distribution screenshots
when akshare data is unavailable.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.agent.chip_analysis import ChipAnalysis

_SYSTEM_PROMPT = """\
你是A股筹码分析助手。从同花顺筹码分布截图提取数字字段，返回JSON（无法识别填null）：
{
  "code": "股票代码(6位)",
  "current_price": 当前价(float),
  "avg_cost": 平均成本(float),
  "profitable_pct": 获利比例(0-1小数),
  "concentration": 集中度(0-100 float),
  "range_70_lower": 70%区间下限(float或null),
  "range_70_upper": 70%区间上限(float或null),
  "range_90_lower": 90%区间下限(float),
  "range_90_upper": 90%区间上限(float)
}
只返回JSON，不含其他文字。"""

_CRITICAL_FIELDS = ("avg_cost", "profitable_pct", "range_90_lower", "range_90_upper")


class ScreenshotParseError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _call_claude_vision(image_path: str) -> dict:
    """Call Claude Vision API and return parsed JSON payload as dict.

    Raises ScreenshotParseError on API failure or non-JSON response.
    """
    import anthropic

    suffix = Path(image_path).suffix.lower()
    media_type = "image/jpeg" if suffix in {".jpg", ".jpeg"} else "image/png"

    with open(image_path, "rb") as fh:
        image_data = base64.standard_b64encode(fh.read()).decode("utf-8")

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=256,
            system=_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                        {"type": "text", "text": "请提取截图中的筹码分布数据，返回JSON格式。"},
                    ],
                }
            ],
        )
    except Exception as exc:
        raise ScreenshotParseError(reason=f"API call failed: {exc}") from exc

    raw = response.content[0].text
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ScreenshotParseError(reason=f"JSON parse failed: {exc}") from exc


def parse_chip_screenshot(
    image_path: str,
    code: str | None = None,
) -> ChipAnalysis:
    """Parse a 同花顺 chip distribution screenshot via Claude Vision.

    Returns ChipAnalysis. Raises ScreenshotParseError on failure.
    """
    from engine.agent.chip_analysis import analyze_chip
    from engine.agent.chip_fetcher import ChipSummary

    payload = _call_claude_vision(image_path)

    if not isinstance(payload, dict):
        raise ScreenshotParseError(
            reason=f"JSON parse failed: expected dict, got {type(payload).__name__}"
        )

    missing = [f for f in _CRITICAL_FIELDS if payload.get(f) is None]
    if missing:
        raise ScreenshotParseError(
            reason=f"Missing critical fields: {missing}"
        )

    r90lo = float(payload["range_90_lower"])
    r90hi = float(payload["range_90_upper"])
    r70lo = float(payload["range_70_lower"]) if payload.get("range_70_lower") is not None else r90lo
    r70hi = float(payload["range_70_upper"]) if payload.get("range_70_upper") is not None else r90hi

    current_price = float(payload.get("current_price") or 0.0)
    resolved_code = code if code is not None else (payload.get("code") or "")

    summary = ChipSummary(
        code=resolved_code,
        date=payload.get("date") or "",
        avg_cost=float(payload["avg_cost"]),
        profitable_pct=float(payload["profitable_pct"]),
        concentration=float(payload.get("concentration") or 0.0),
        range_70_lower=r70lo,
        range_70_upper=r70hi,
        range_90_lower=r90lo,
        range_90_upper=r90hi,
        bars=[],
    )

    return analyze_chip(resolved_code, current_price, summary)
