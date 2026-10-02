"""python -m shorts_pipeline.cli <command>

Automated: topics -> script -> policy lint -> TTS(optional) -> captions -> render -> upload -> stats
Human gates (by design): demo recording, voice (default), final approval before upload."""
from __future__ import annotations
import argparse, sys, yaml
from pathlib import Path
from . import store, topics, scriptgen, policy, tts, render, youtube

GUIDE = {
    "awaiting_demo": "HUMAN: record the real tool run -> save as {d}/demo.mp4 (steps in script.json: demo_steps)",
    "needs_voice": "HUMAN: record voice-over from script.json -> {d}/voice.wav|mp3|m4a  (or set voice.provider)",
    "awaiting_approval": "HUMAN: watch {d}/final.mp4, then run: approve {id}",
}


def load_cfg() -> dict:
    p = store.ROOT / "config.yaml"
    return yaml.safe_load((p if p.exists() else store.ROOT / "config.example.yaml").read_text())


def advance(d: Path, cfg: dict, mock: bool = False, publish_at: str | None = None, log=print) -> str:
    """Move one episode as far as automation allows. Returns the final stage."""
    for _ in range(8):
        st = store.stage(d)
        if st == "needs_script":
            state = store.read_json(d / "state.json")
            past = store.known_scripts()
            script = scriptgen.generate(state["topic"], cfg, [p["title"] for p in past], mock)
            errs = policy.lint(script, past)
            store.write_json(d / "script.json", script)
            if errs:
                store.write_json(d / "lint_errors.json", errs)
                (d / "script.json").rename(d / "script.rejected.json")
                log(f"[{d.name}] script rejected by policy lint: {errs}")
                return "rejected"
            store.remember_script(script, d.name)
            log(f"[{d.name}] script ok: {script['title']}")
        elif st == "needs_voice":
            v = tts.make_voice(d, store.read_json(d / "script.json"), cfg)
            if v is None:
                break
        elif st == "needs_render":
            log(f"[{d.name}] rendering"); render.render(d, cfg)
        elif st == "needs_upload":
            if cfg["upload"]["require_approval"] and not store.read_json(d / "state.json")["approved"]:
                break
            if youtube.uploaded_today() >= cfg["upload"].get("daily_limit", 2):
                log("daily upload limit reached"); break
            log(f"[{d.name}] uploaded video_id={youtube.upload(d, cfg, publish_at)}")
        else:
            break
    st = store.stage(d)
    if st in GUIDE:
        log("  -> " + GUIDE[st].format(d=d, id=d.name))
    return st


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="shorts_pipeline")
    ap.add_argument("cmd", choices=["topics", "new", "run", "status", "approve", "stats", "auth"])
    ap.add_argument("arg", nargs="?")
    ap.add_argument("--mock", action="store_true", help="offline placeholder scripts (no API key)")
    ap.add_argument("--publish-at", help="RFC3339 time, e.g. 2026-10-05T13:00:00Z")
    a = ap.parse_args(argv)
    cfg = load_cfg()
    if a.cmd == "topics":
        for t, s in topics.collect(cfg):
            print(f"{t}  [{s}]")
    elif a.cmd == "new":
        print(store.new_episode(a.arg, "manual"))
    elif a.cmd == "run":
        for t, s in topics.collect(cfg) if a.arg == "collect" else []:
            store.new_episode(t, s)
        for d in store.episodes():
            if store.stage(d) != "uploaded":
                advance(d, cfg, a.mock, a.publish_at)
    elif a.cmd == "status":
        for d in store.episodes():
            print(f"{store.stage(d):18} {d.name}")
    elif a.cmd == "approve":
        d = store.WORK / a.arg
        s = store.read_json(d / "state.json"); s["approved"] = True; store.write_json(d / "state.json", s)
        print("approved", a.arg)
    elif a.cmd == "stats":
        for r in youtube.fetch_stats():
            print(r)
    elif a.cmd == "auth":
        youtube.service(); print("token.json saved")
    return 0


if __name__ == "__main__":
    sys.exit(main())
