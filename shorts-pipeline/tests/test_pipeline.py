import subprocess, json
from pathlib import Path
import pytest
from shorts_pipeline import store, policy, captions, scriptgen, render, media, cli

CFG = {"render": {"max_seconds": 59, "font": "DejaVu Sans"}, "voice": {"provider": "human"},
       "upload": {"require_approval": True, "daily_limit": 2, "privacy": "private", "category_id": "28"},
       "channel": {"name": "t", "language": "en"}, "llm": {"model": "x"}, "topics": {}}


def ff(args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error"] + args, check=True)


@pytest.fixture
def ep(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "HISTORY", tmp_path / "history.jsonl")
    monkeypatch.setattr(store, "WORK", tmp_path / "work")
    return store.new_episode("Test tool", work=tmp_path / "work")


def test_policy_accepts_mock_and_rejects_bad():
    s = scriptgen.mock_script("PDF summarizer")
    assert policy.lint(s) == []
    bad = dict(s, limitation="", title="x" * 80)
    assert "missing field: limitation" in policy.lint(bad)
    hype = dict(s, beats=[{"narration": "Guaranteed to make $500 passive income with this tool every day of the week for you", "on_screen": ""}] * 3)
    assert any("hype" in e for e in policy.lint(hype))
    legal = dict(s, title="AI reads your contract")
    assert any("disclaimer" in e for e in policy.lint(legal))


def test_policy_blocks_near_duplicates():
    s = scriptgen.mock_script("PDF summarizer")
    past = [{"id": "a", "text": store.script_text(s)}]
    assert any("too similar" in e for e in policy.lint(s, past))


def test_caption_timing_covers_audio():
    s = scriptgen.mock_script("x")
    ev = captions.build_events(s, 30.0)
    caps = [e for e in ev if e[2] == "Cap"]
    assert caps[0][0] == 0 and abs(caps[-1][1] - 30.0) < 1e-6
    assert all(b[0] >= a[1] - 1e-6 for a, b in zip(caps, caps[1:]))
    assert "[Events]" in captions.to_ass(s, 30.0)


def test_stage_gates_and_full_render(ep):
    st = cli.advance(ep, CFG, mock=True, log=lambda *_: None)
    assert st == "awaiting_demo"
    ff(["-f", "lavfi", "-i", "testsrc=size=1280x720:rate=30:duration=4", "-pix_fmt", "yuv420p", str(ep / "demo.mp4")])
    assert cli.advance(ep, CFG, mock=True, log=lambda *_: None) == "needs_voice"
    ff(["-f", "lavfi", "-i", "sine=frequency=300:duration=12", str(ep / "voice.wav")])
    assert cli.advance(ep, CFG, mock=True, log=lambda *_: None) == "awaiting_approval"   # demo (4s) loops to cover 12s voice
    out = ep / "final.mp4"
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                            "-of", "csv=p=0", str(out)], capture_output=True, text=True).stdout.strip()
    assert probe == "1080,1920"
    assert 12 <= media.duration(out) <= 13
    s = store.read_json(ep / "state.json"); s["approved"] = True; store.write_json(ep / "state.json", s)
    assert store.stage(ep) == "needs_upload"


def test_over_cap_voice_rejected(ep):
    cli.advance(ep, CFG, mock=True, log=lambda *_: None)
    ff(["-f", "lavfi", "-i", "testsrc=size=640x360:rate=30:duration=2", "-pix_fmt", "yuv420p", str(ep / "demo.mp4")])
    ff(["-f", "lavfi", "-i", "sine=frequency=300:duration=70", str(ep / "voice.wav")])
    with pytest.raises(RuntimeError, match="over the 59s"):
        render.render(ep, CFG)
