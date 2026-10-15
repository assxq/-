"""Shared loader + validator for production/<EP>/episode.json.

Every tool calls  load(ep, need=[...])  so a missing or mistyped key fails at the START with a clear message,
not after minutes of rendering.  Keys are documented in production/EPISODE_JSON.md.
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def _fail(ep, msg):
    sys.exit(f"episode.json ({ep}): {msg}\n  see production/EPISODE_JSON.md for the key list")

def _need(ep, d, keys, where):
    for k in keys:
        if k not in d: _fail(ep, f"missing key '{where}{k}'")

def load(ep, need=("overlay", "audio", "video", "review")):
    path = f"{ROOT}/production/{ep}/episode.json"
    if not os.path.exists(path):
        sys.exit(f"{path} not found. Create it (copy production/_template/episode.json) before using --ep {ep}.")
    with open(path, encoding="utf-8") as f:
        try: cfg = json.load(f)
        except json.JSONDecodeError as e: sys.exit(f"{path} is not valid JSON: {e}")
    _need(ep, cfg, ["duration", "fps"], "")
    if "overlay" in need or "audio" in need or "video" in need:
        pass
    if "overlay" in need:
        _need(ep, cfg, ["tape_id", "side", "overlay"], "")
        ov = cfg["overlay"]; _need(ep, ov, ["captions", "rec"], "overlay.")
        _need(ep, ov["rec"], ["period", "on"], "overlay.rec.")
        for i, c in enumerate(ov["captions"]): _need(ep, c, ["start", "until", "text", "icon"], f"overlay.captions[{i}].")
    if "audio" in need:
        _need(ep, cfg, ["audio"], ""); a = cfg["audio"]; _need(ep, a, ["timing"], "audio.")
        _need(ep, a["timing"], ["hiss_ramp", "hum_ramp", "hum_dip_db", "reel_ramp", "pad_env", "pad_bright", "pad_vib"], "audio.timing.")
    if "video" in need:
        _need(ep, cfg, ["video"], ""); v = cfg["video"]; _need(ep, v, ["base_image", "lamp", "shots", "effects"], "video.")
        _need(ep, v["lamp"], ["src", "out", "period", "on"], "video.lamp.")
        ids = set()
        for i, s in enumerate(v["shots"]):
            _need(ep, s, ["id", "t0", "t1"], f"video.shots[{i}].")
            if s["id"] in ids: _fail(ep, f"duplicate shot id '{s['id']}'")
            ids.add(s["id"])
            kind = s.get("kind")
            if kind is None: _need(ep, s, ["file", "standin"], f"video.shots[{i}] ({s['id']}).")
            if kind == "crt_off": _need(ep, s, ["from", "len"], f"video.shots[{i}] ({s['id']}).")
        for e in v["effects"]:
            if e.get("type") not in ("dissolve", "impact", "glitch"): _fail(ep, f"unknown effect type {e.get('type')!r}")
    if "review" in need:
        _need(ep, cfg, ["review"], ""); r = cfg["review"]; _need(ep, r, ["ref", "boxes"], "review.")
        _need(ep, r["boxes"], ["face", "eyes", "mouth", "lamp"], "review.boxes.")
    return cfg
