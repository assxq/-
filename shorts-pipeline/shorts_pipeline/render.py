"""Compose final 1080x1920 video: demo recording (fit over blurred fill) + burned captions + voice-over."""
from __future__ import annotations
from pathlib import Path
from . import store, media, captions


def render(d: Path, cfg: dict) -> Path:
    script = store.read_json(d / "script.json")
    voice = store.find_voice(d)
    dur = media.duration(voice)
    cap = cfg["render"].get("max_seconds", 59)
    if dur > cap:
        raise RuntimeError(f"voice-over is {dur:.1f}s, over the {cap}s Shorts cap - shorten the script")
    (d / "captions.ass").write_text(captions.to_ass(script, dur, cfg["render"].get("font", "DejaVu Sans")), encoding="utf-8")
    vf = ("[0:v]split[a][b];"
          "[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:5[bg];"
          "[b]scale=1080:1920:force_original_aspect_ratio=decrease[fg];"
          "[bg][fg]overlay=(W-w)/2:(H-h)/2,format=yuv420p,subtitles=captions.ass[v]")
    media.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
               "-stream_loop", "-1", "-i", "demo.mp4", "-i", voice.name,
               "-filter_complex", vf, "-map", "[v]", "-map", "1:a",
               "-t", f"{dur + 0.3:.2f}", "-r", "30", "-c:v", "libx264", "-crf", "20", "-preset", "veryfast",
               "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "final.mp4"], cwd=d)
    return d / "final.mp4"
