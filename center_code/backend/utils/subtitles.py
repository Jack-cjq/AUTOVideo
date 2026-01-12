"""
字幕生成工具
"""
import re
import uuid
from dataclasses import dataclass


_SPLIT_RE = re.compile(r"[\r\n]+|[。！？!?；;]+")


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def split_into_sentences(text: str) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    parts = [p.strip() for p in _SPLIT_RE.split(text)]
    return [p for p in parts if p]


def _weight(s: str) -> int:
    # Count non-space characters as rough speaking weight
    s = re.sub(r"\s+", "", s)
    return max(1, len(s))


def format_srt_time(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    ms = int(round(seconds * 1000))
    hh = ms // 3_600_000
    ms %= 3_600_000
    mm = ms // 60_000
    ms %= 60_000
    ss = ms // 1000
    ms %= 1000
    return f"{hh:02d}:{mm:02d}:{ss:02d},{ms:03d}"


@dataclass(frozen=True)
class SrtItem:
    index: int
    start: float
    end: float
    text: str


def generate_srt_items(
    *,
    text: str,
    total_duration_sec: float,
    min_item_sec: float = 0.9,
    max_item_sec: float = 6.0,
) -> list[SrtItem]:
    total_duration_sec = float(total_duration_sec)
    if total_duration_sec <= 0:
        raise ValueError("total_duration_sec must be positive")

    sentences = split_into_sentences(text)
    if not sentences:
        raise ValueError("text is empty")

    weights = [_weight(s) for s in sentences]
    total_w = float(sum(weights)) or 1.0

    # Initial allocation
    durs = [(w / total_w) * total_duration_sec for w in weights]

    # Clamp durations
    durs = [max(min_item_sec, min(max_item_sec, d)) for d in durs]

    # Re-scale to match total duration
    sum_d = float(sum(durs)) or 1.0
    scale = total_duration_sec / sum_d
    durs = [d * scale for d in durs]

    # Build items
    items: list[SrtItem] = []
    t = 0.0
    for i, (s, d) in enumerate(zip(sentences, durs), start=1):
        start = t
        end = t + float(d)
        t = end
        items.append(SrtItem(index=i, start=start, end=end, text=_clean_text(s)))

    # Ensure last end aligns to total duration
    if items:
        last = items[-1]
        if last.end != total_duration_sec:
            items[-1] = SrtItem(index=last.index, start=last.start, end=total_duration_sec, text=last.text)
    return items


def render_srt(items: list[SrtItem]) -> str:
    lines: list[str] = []
    for it in items:
        lines.append(str(it.index))
        lines.append(f"{format_srt_time(it.start)} --> {format_srt_time(it.end)}")
        lines.append(it.text)
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def new_srt_filename(prefix: str = "sub") -> str:
    return f"{prefix}_{uuid.uuid4().hex}.srt"

