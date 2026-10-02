"""File-based episode store. Stage is derived from which files exist, so every step is idempotent."""
from __future__ import annotations
import json, re, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work"
HISTORY = ROOT / "history.jsonl"


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "episode"


def new_episode(topic: str, source: str = "manual", work: Path = WORK) -> Path:
    eid = f"{time.strftime('%Y%m%d-%H%M%S')}-{slug(topic)}"
    d = work / eid
    d.mkdir(parents=True)
    write_json(d / "state.json", {"id": eid, "topic": topic, "source": source,
                                   "created": time.time(), "approved": False})
    return d


def read_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def write_json(p: Path, data) -> None:
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def episodes(work: Path = WORK) -> list[Path]:
    return sorted(p for p in work.glob("*") if (p / "state.json").exists()) if work.exists() else []


def find_voice(d: Path) -> Path | None:
    for ext in ("wav", "mp3", "m4a"):
        p = d / f"voice.{ext}"
        if p.exists():
            return p
    return None


def stage(d: Path) -> str:
    """Return the next action an episode is waiting for."""
    st = read_json(d / "state.json")
    if (d / "upload.json").exists():
        return "uploaded"
    if not (d / "script.json").exists():
        return "needs_script"
    if not (d / "demo.mp4").exists():
        return "awaiting_demo"          # HUMAN: record the real tool demo
    if find_voice(d) is None:
        return "needs_voice"            # TTS or HUMAN voice-over
    if not (d / "final.mp4").exists():
        return "needs_render"
    if not st.get("approved"):
        return "awaiting_approval"      # HUMAN: watch final.mp4
    return "needs_upload"


def known_scripts() -> list[dict]:
    if not HISTORY.exists():
        return []
    return [json.loads(l) for l in HISTORY.read_text(encoding="utf-8").splitlines() if l.strip()]


def remember_script(script: dict, eid: str) -> None:
    with HISTORY.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"id": eid, "title": script["title"], "text": script_text(script)}, ensure_ascii=False) + "\n")


def script_text(script: dict) -> str:
    return " ".join([script["hook"]] + [b["narration"] for b in script["beats"]])
