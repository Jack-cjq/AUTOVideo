"""
字幕生成工具
"""
import os
import re
import uuid
from dataclasses import dataclass
from typing import List, Dict, Any


DEFAULT_MAX_LINE_CHARS = 16
DEFAULT_MAX_LINES = 2
DEFAULT_MAX_ITEM_CHARS = DEFAULT_MAX_LINE_CHARS * DEFAULT_MAX_LINES

# Major sentence boundaries (avoid splitting too aggressively on commas).
_MAJOR_SPLIT_RE = re.compile(r"[\r\n]+|[。！？!?]+")
_MINOR_SPLIT_RE = re.compile(r"[，,、；;:：]+")
_COMMA_RE = re.compile(r"[，,、]+")


def _env_int(name: str, default: int) -> int:
    try:
        return int((os.environ.get(name) or "").strip() or default)
    except Exception:
        return int(default)


def _env_float(name: str, default: float) -> float:
    try:
        return float((os.environ.get(name) or "").strip() or default)
    except Exception:
        return float(default)


def _env_bool(name: str, default: bool) -> bool:
    v = (os.environ.get(name) or "").strip().lower()
    if not v:
        return bool(default)
    if v in ("1", "true", "yes", "on"):
        return True
    if v in ("0", "false", "no", "off"):
        return False
    return bool(default)


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _preprocess_text_for_subtitles(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""

    # Optimization path:
    # - Remove comma-like punctuation to avoid "逗号碎片" and reduce jitter.
    # - Keep major punctuation (。！？) for splitting cues.
    if _env_bool("SUBTITLE_REMOVE_COMMAS", True):
        text = _COMMA_RE.sub(" ", text)
    return _clean_text(text)


def _join_text(a: str, b: str) -> str:
    a = (a or "").strip()
    b = (b or "").strip()
    if not a:
        return b
    if not b:
        return a
    if re.search(r"[A-Za-z0-9]$", a) and re.search(r"^[A-Za-z0-9]", b):
        return f"{a} {b}"
    return f"{a}{b}"


def _wrap_subtitle_text(text: str, *, max_line_chars: int = 16, max_lines: int = 2) -> str:
    """
    Wrap subtitle text into 1-2 lines like TV subtitles.
    - Prefer breaking on spaces when present
    - Fallback to fixed-width chunking for CJK/no-space text
    """
    text = _preprocess_text_for_subtitles(text)
    if not text:
        return ""

    max_line_chars = max(8, int(max_line_chars or 16))
    max_lines = max(1, int(max_lines or 2))

    # If text already contains line breaks, normalize and keep at most max_lines
    if "\n" in text:
        lines = [x.strip() for x in text.splitlines() if x.strip()]
        if len(lines) <= max_lines:
            return "\n".join(lines)
        folded = lines[: max_lines - 1] + [" ".join(lines[max_lines - 1 :]).strip()]
        return "\n".join([x for x in folded if x])

    # Prefer splitting by whitespace if present (keep words together)
    tokens = text.split(" ")
    if len(tokens) > 1:
        lines: List[str] = []
        cur: List[str] = []
        cur_len = 0
        for tok in tokens:
            if not tok:
                continue
            add_len = len(tok) + (1 if cur else 0)
            if cur and cur_len + add_len > max_line_chars:
                lines.append(" ".join(cur).strip())
                cur = [tok]
                cur_len = len(tok)
            else:
                cur.append(tok)
                cur_len += add_len
        if cur:
            lines.append(" ".join(cur).strip())
        if len(lines) > max_lines:
            lines = lines[: max_lines - 1] + [" ".join(lines[max_lines - 1 :]).strip()]
        return "\n".join([x for x in lines[:max_lines] if x])

    # No whitespace: chunk by character count
    chunks = [text[i : i + max_line_chars] for i in range(0, len(text), max_line_chars)]
    if len(chunks) > max_lines:
        chunks = chunks[: max_lines - 1] + ["".join(chunks[max_lines - 1 :])]
    return "\n".join([c for c in chunks[:max_lines] if c])


def _split_long_piece(piece: str, *, max_chars: int) -> List[str]:
    piece = _preprocess_text_for_subtitles(piece)
    if not piece:
        return []

    max_chars = max(8, int(max_chars or DEFAULT_MAX_ITEM_CHARS))
    if _weight(piece) <= max_chars:
        return [piece]

    tokens = piece.split(" ")
    if len(tokens) > 1:
        out: List[str] = []
        cur: List[str] = []
        cur_w = 0
        for tok in tokens:
            if not tok:
                continue
            tok_w = _weight(tok)
            add_w = tok_w + (1 if cur else 0)
            if cur and cur_w + add_w > max_chars:
                out.append(" ".join(cur).strip())
                cur = [tok]
                cur_w = tok_w
            else:
                cur.append(tok)
                cur_w += add_w
        if cur:
            out.append(" ".join(cur).strip())
        return [x for x in out if x]

    raw = re.sub(r"\s+", "", piece)
    return [raw[i : i + max_chars] for i in range(0, len(raw), max_chars) if raw[i : i + max_chars]]


def split_into_sentences(text: str, *, max_chars: int = DEFAULT_MAX_ITEM_CHARS) -> List[str]:
    text = (text or "").strip()
    if not text:
        return []
    parts = [p.strip() for p in _MAJOR_SPLIT_RE.split(text)]
    sentences = [p for p in parts if p]
    if len(sentences) >= 2:
        out: List[str] = []
        for s in sentences:
            out.extend(_split_long_piece(s, max_chars=max_chars))
        return [x for x in out if x]

    # Fallback: ASR output often has no punctuation, which would create a single subtitle
    # that spans the whole duration ("字幕铺满画面"). Split long text into chunks.
    raw = sentences[0] if sentences else text
    # Keep commas for weak-boundary splitting; commas are removed at rendering time.
    raw = _clean_text(raw)
    if not raw:
        return []

    minor_parts = [p.strip() for p in _MINOR_SPLIT_RE.split(raw) if p.strip()]
    if len(minor_parts) >= 2:
        out: List[str] = []
        for p in minor_parts:
            out.extend(_split_long_piece(p, max_chars=max_chars))
        return [x for x in out if x]

    return _split_long_piece(raw, max_chars=max_chars)


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
) -> List[SrtItem]:
    total_duration_sec = float(total_duration_sec)
    if total_duration_sec <= 0:
        raise ValueError("total_duration_sec must be positive")

    sentences = split_into_sentences(text)
    if not sentences:
        raise ValueError("text is empty")

    weights = [_weight(s) for s in sentences]
    total_w = float(sum(weights)) or 1.0

    min_item_sec = float(min_item_sec)
    max_item_sec = float(max_item_sec)

    # Reading-speed guard: longer lines need more time to avoid "flashing" subtitles.
    chars_per_sec = 8.0  # conservative default; works reasonably for CJK/short video
    min_durs = [max(min_item_sec, (w / chars_per_sec)) for w in weights]

    # Start from minimum durations, then distribute the remaining time by weights.
    durs = list(min_durs)
    remain = total_duration_sec - float(sum(durs))
    if remain > 1e-6:
        for i, w in enumerate(weights):
            durs[i] += remain * (w / total_w)

    # Cap by max_item_sec and redistribute overflow (a few iterations is enough).
    for _ in range(3):
        overflow = 0.0
        free_w = 0.0
        for i in range(len(durs)):
            if durs[i] > max_item_sec:
                overflow += durs[i] - max_item_sec
                durs[i] = max_item_sec
            else:
                free_w += weights[i]
        if overflow <= 1e-6 or free_w <= 1e-6:
            break
        for i in range(len(durs)):
            if durs[i] < max_item_sec - 1e-9:
                durs[i] += overflow * (weights[i] / free_w)

    # Re-scale to match total duration (last-resort normalization).
    sum_d = float(sum(durs)) or 1.0
    durs = [d * (total_duration_sec / sum_d) for d in durs]

    # Build items
    items: List[SrtItem] = []
    t = 0.0
    for i, (s, d) in enumerate(zip(sentences, durs), start=1):
        start = t
        end = t + float(d)
        t = end
        items.append(SrtItem(index=i, start=start, end=end, text=_wrap_subtitle_text(s)))

    # Ensure last end aligns to total duration
    if items:
        last = items[-1]
        if last.end != total_duration_sec:
            items[-1] = SrtItem(index=last.index, start=last.start, end=total_duration_sec, text=last.text)
    return items


def render_srt(items: List[SrtItem]) -> str:
    lines: List[str] = []
    for it in items:
        lines.append(str(it.index))
        lines.append(f"{format_srt_time(it.start)} --> {format_srt_time(it.end)}")
        lines.append(it.text)
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def new_srt_filename(prefix: str = "sub") -> str:
    return f"{prefix}_{uuid.uuid4().hex}.srt"


def generate_srt_from_timestamps(timestamps: List[dict]) -> List[SrtItem]:
    """
    Generate SRT items from timestamps with basic normalization and merging.

    Expected input format:
        [{"text": str, "start": float, "end": float, "duration": float}, ...]
    """

    def normalize(ts_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for ts in ts_list or []:
            if not isinstance(ts, dict):
                continue
            raw_text = _clean_text(ts.get("text", ""))
            if not _preprocess_text_for_subtitles(raw_text):
                continue
            try:
                start = float(ts.get("start", 0.0) or 0.0)
            except Exception:
                start = 0.0
            try:
                end = float(ts.get("end", start) or start)
            except Exception:
                end = start
            if end <= start:
                end = start + 0.5
            out.append({"text": raw_text, "start": max(0.0, start), "end": max(0.0, end)})

        out.sort(key=lambda x: (x["start"], x["end"]))

        prev_end = 0.0
        for it in out:
            if it["start"] < prev_end:
                it["start"] = prev_end
                if it["end"] <= it["start"]:
                    it["end"] = it["start"] + 0.3
            prev_end = max(prev_end, float(it["end"]))
        return out

    max_line_chars = _env_int("SUBTITLE_MAX_LINE_CHARS", DEFAULT_MAX_LINE_CHARS)
    max_lines = _env_int("SUBTITLE_MAX_LINES", DEFAULT_MAX_LINES)
    max_item_chars = _env_int("SUBTITLE_MAX_ITEM_CHARS", max_line_chars * max_lines)

    # When splitting timestamps into short clauses, allocate duration by text weight.
    split_min_item_sec = _env_float("SUBTITLE_TS_MIN_ITEM_SEC", 0.6)
    split_max_item_sec = _env_float("SUBTITLE_TS_MAX_ITEM_SEC", 6.0)
    split_chars_per_sec = _env_float("SUBTITLE_TS_CHARS_PER_SEC", 8.0)

    merge_min_item_sec = _env_float("SUBTITLE_TS_MERGE_MIN_ITEM_SEC", 0.8)
    merge_max_item_sec = _env_float("SUBTITLE_TS_MERGE_MAX_ITEM_SEC", 6.0)
    merge_gap_sec = _env_float("SUBTITLE_TS_MERGE_GAP_SEC", 0.15)
    max_merge_chars = _env_int("SUBTITLE_TS_MAX_MERGE_CHARS", max_item_chars + 8)

    def merge_short(ts_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        merged: List[Dict[str, Any]] = []
        for ts in ts_list:
            if not merged:
                merged.append(dict(ts))
                continue
            prev = merged[-1]
            gap = float(ts["start"]) - float(prev["end"])
            prev_d = float(prev["end"]) - float(prev["start"])
            cur_d = float(ts["end"]) - float(ts["start"])
            merged_text = _join_text(prev["text"], ts["text"])

            short_by_dur = prev_d < merge_min_item_sec or cur_d < merge_min_item_sec
            short_by_text = _weight(prev["text"]) <= 2 or _weight(ts["text"]) <= 2
            # Avoid over-merging across otherwise good segments: only merge short text
            # if the combined duration is also small.
            short_enough = short_by_dur or (short_by_text and (prev_d + cur_d) <= (merge_min_item_sec * 2.0))

            should_merge = (
                gap <= merge_gap_sec
                and short_enough
                and (float(ts["end"]) - float(prev["start"])) <= merge_max_item_sec
                and _weight(merged_text) <= max_merge_chars
            )
            if should_merge:
                prev["text"] = merged_text
                prev["end"] = max(float(prev["end"]), float(ts["end"]))
            else:
                merged.append(dict(ts))
        return merged

    def allocate_segment(start: float, end: float, parts: List[str]) -> List[Dict[str, Any]]:
        start = float(start)
        end = float(end)
        if end <= start or not parts:
            return []

        seg_dur = end - start
        weights = [float(_weight(p)) for p in parts]
        total_w = float(sum(weights)) or 1.0

        cps = max(1.0, float(split_chars_per_sec or 8.0))
        min_durs = [max(float(split_min_item_sec), w / cps) for w in weights]

        if sum(min_durs) >= seg_dur:
            # Not enough time: scale down but keep a small floor.
            floor = min(0.3, seg_dur / max(1, len(parts)))
            scale = seg_dur / float(sum(min_durs) or 1.0)
            durs = [max(floor, d * scale) for d in min_durs]
        else:
            durs = list(min_durs)
            remain = seg_dur - float(sum(durs))
            for i, w in enumerate(weights):
                durs[i] += remain * (w / total_w)

            # Cap and redistribute overflow a few times.
            for _ in range(3):
                overflow = 0.0
                free_w = 0.0
                for i in range(len(durs)):
                    if durs[i] > split_max_item_sec:
                        overflow += durs[i] - split_max_item_sec
                        durs[i] = split_max_item_sec
                    else:
                        free_w += weights[i]
                if overflow <= 1e-6 or free_w <= 1e-6:
                    break
                for i in range(len(durs)):
                    if durs[i] < split_max_item_sec - 1e-9:
                        durs[i] += overflow * (weights[i] / free_w)

        # Final normalization to exactly match segment duration.
        sum_d = float(sum(durs)) or 1.0
        durs = [d * (seg_dur / sum_d) for d in durs]

        out: List[Dict[str, Any]] = []
        t = start
        for part, d in zip(parts, durs):
            s = t
            e = s + float(d)
            t = e
            out.append({"text": part, "start": s, "end": e})
        if out:
            out[-1]["end"] = end
        return out

    normalized = normalize(timestamps)

    expanded: List[Dict[str, Any]] = []
    for ts in normalized:
        text = ts.get("text", "")
        parts = split_into_sentences(text, max_chars=max_item_chars)
        if not parts:
            continue
        expanded.extend(allocate_segment(ts["start"], ts["end"], parts))

    merged = merge_short(expanded)

    items: List[SrtItem] = []
    for i, ts in enumerate(merged, start=1):
        wrapped = _wrap_subtitle_text(ts.get("text", ""), max_line_chars=max_line_chars, max_lines=max_lines)
        if not wrapped:
            continue
        start = float(ts.get("start", 0.0))
        end = float(ts.get("end", start + 0.5))
        if end <= start:
            end = start + 0.3
        items.append(SrtItem(index=i, start=start, end=end, text=wrapped))
    return items
