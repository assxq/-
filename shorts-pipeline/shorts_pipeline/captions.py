"""Caption timing: audio length is split across beats by word count, then across 3-word chunks by character count."""
from __future__ import annotations


def _ts(t: float) -> str:
    cs = int(round(t * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def chunks(words: list[str], n: int = 3) -> list[str]:
    return [" ".join(words[i:i + n]) for i in range(0, len(words), n)]


def build_events(script: dict, total: float) -> list[tuple[float, float, str, str]]:
    """Return (start, end, style, text). Hook is its own segment, cta is last."""
    segs = [(script["hook"], "")] + [(b["narration"], b.get("on_screen", "")) for b in script["beats"]] + [(script["cta"], "")]
    total_words = sum(len(s[0].split()) for s in segs) or 1
    t, events = 0.0, []
    for text, label in segs:
        w = text.split()
        seg_dur = total * len(w) / total_words
        cs = chunks(w)
        weights = [len(c) for c in cs]
        wsum = sum(weights) or 1
        ct = t
        for c, wt in zip(cs, weights):
            d = seg_dur * wt / wsum
            events.append((ct, ct + d, "Cap", c.upper()))
            ct += d
        if label:
            events.append((t, t + seg_dur, "Label", label))
        t += seg_dur
    return events


def to_ass(script: dict, total: float, font: str = "DejaVu Sans") -> str:
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Cap,{font},84,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,7,2,2,60,60,520,1
Style: Label,{font},56,&H0000E5FF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,5,0,8,60,60,170,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    lines = [f"Dialogue: 0,{_ts(s)},{_ts(e)},{st},,0,0,0,,{txt.replace(chr(10), ' ')}"
             for s, e, st, txt in build_events(script, total)]
    return head + "\n".join(lines) + "\n"
