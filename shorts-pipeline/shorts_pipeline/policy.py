"""Pre-flight lint targeting YouTube's 'Generic or Repetitive Content' risk and basic compliance. Returns a list of problems."""
from __future__ import annotations
import difflib, re
from . import store

BANNED = re.compile(r"\b(guaranteed|get rich|make \$?\d+|passive income|100% accurate|cure|no risk)\b", re.I)
SENSITIVE = re.compile(r"\b(legal|lawyer|contract|medical|health|diagnos|invest|stock|crypto|tax|loan)\w*", re.I)
SIMILARITY_LIMIT = 0.6


def lint(script: dict, past: list[dict] | None = None) -> list[str]:
    errs = []
    for k in ("title", "hook", "beats", "demo_steps", "limitation", "cta", "description", "tags"):
        if not script.get(k):
            errs.append(f"missing field: {k}")
    if errs:
        return errs
    if len(script["title"]) > 70:
        errs.append("title > 70 chars")
    if len(script["hook"].split()) > 14:
        errs.append("hook > 14 words")
    text = store.script_text(script)
    words = len(text.split())
    if not 40 <= words <= 150:
        errs.append(f"narration length {words} words (want 40-150)")
    if BANNED.search(text) or BANNED.search(script["title"]):
        errs.append("banned/hype phrase found")
    if (SENSITIVE.search(text) or SENSITIVE.search(script["title"])) and not script.get("disclaimer"):
        errs.append("sensitive topic needs a disclaimer")
    for p in past or []:
        r = difflib.SequenceMatcher(None, text.lower(), p["text"].lower()).ratio()
        if r > SIMILARITY_LIMIT:
            errs.append(f"too similar ({r:.2f}) to past episode {p['id']} -> repetitive-content risk")
            break
    return errs
