"""Voice-over. Default provider 'human' waits for you to drop voice.wav/mp3/m4a into the episode folder
(recommended: your own voice is an original-value signal). 'elevenlabs' / 'espeak' are automation options."""
from __future__ import annotations
import os, shutil, subprocess
from pathlib import Path
from . import store, media


def make_voice(d: Path, script: dict, cfg: dict) -> Path | None:
    prov = cfg["voice"]["provider"]
    text = " ".join([script["hook"]] + [b["narration"] for b in script["beats"]] + [script["cta"]])
    if prov == "human":
        return store.find_voice(d)       # None -> pipeline stays at needs_voice
    if prov == "elevenlabs":
        import requests
        vid = cfg["voice"]["elevenlabs_voice_id"]
        r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}",
                          headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]},
                          json={"text": text, "model_id": "eleven_multilingual_v2"}, timeout=120)
        r.raise_for_status()
        out = d / "voice.mp3"
        out.write_bytes(r.content)
        return out
    if prov == "espeak":
        exe = shutil.which("espeak-ng") or shutil.which("espeak")
        if not exe:
            raise RuntimeError("espeak not installed")
        out = d / "voice.wav"
        subprocess.run([exe, "-w", str(out), text], check=True)
        return out
    raise ValueError(f"unknown voice provider {prov}")
