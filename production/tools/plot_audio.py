#!/usr/bin/env python3
"""Draws production/<EP>/audio/<EP>_audio_timeline.png: waveform + spectrogram with the event markers
(markers come from episode.json -> audio.marks).  Usage: python3 production/tools/plot_audio.py --ep E01
Needs numpy and Pillow (no matplotlib)."""
import argparse, json, os, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load(p):
    w = wave.open(p); n = w.getnframes(); sr = w.getframerate(); ch = w.getnchannels()
    x = np.frombuffer(w.readframes(n), dtype="<i2").reshape(-1, ch) / 32768.0
    return x.mean(axis=1), sr

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--ep", default="E01"); a = ap.parse_args()
    with open(f"{ROOT}/production/{a.ep}/episode.json", encoding="utf-8") as f:
        MARKS = [tuple(m) for m in json.load(f)["audio"]["marks"]]
    SRC = f"{ROOT}/production/{a.ep}/audio/{a.ep}_audio_temp_mix.wav"
    OUT = f"{ROOT}/production/{a.ep}/audio/{a.ep}_audio_timeline.png"
    x, sr = load(SRC)
    dur = len(x) / sr
    W, H_WAVE, H_SPEC, PAD_L, PAD_T = 1800, 150, 520, 70, 70
    img = Image.new("RGB", (W + PAD_L + 20, PAD_T + H_WAVE + H_SPEC + 70), (11, 13, 12))
    d = ImageDraw.Draw(img)
    try: f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 13)
    except Exception: f = ImageFont.load_default()

    # waveform envelope
    cols = np.array_split(np.abs(x), W)
    env = np.array([c.max() for c in cols])
    y0 = PAD_T + H_WAVE // 2
    for i, e in enumerate(env):
        h = int(e * (H_WAVE / 2 - 4) * 1.6)
        d.line([(PAD_L + i, y0 - h), (PAD_L + i, y0 + h)], fill=(77, 255, 136))
    d.text((6, PAD_T + 4), "wave", font=f, fill=(143, 129, 96))

    # spectrogram (log frequency 40 Hz .. 12 kHz)
    nfft, hop = 2048, int(len(x) / W)
    win = np.hanning(nfft)
    fr = np.fft.rfftfreq(nfft, 1 / sr)
    fmin, fmax = 40, 12000
    rows = np.geomspace(fmin, fmax, H_SPEC)
    idx = np.clip(np.searchsorted(fr, rows), 0, len(fr) - 1)
    S = np.zeros((H_SPEC, W))
    for c in range(W):
        s = c * hop
        seg = x[s:s + nfft]
        if len(seg) < nfft: seg = np.pad(seg, (0, nfft - len(seg)))
        S[:, c] = 20 * np.log10(np.abs(np.fft.rfft(seg * win))[idx] / (win.sum() / 2) + 1e-9)   # dBFS
    S = np.clip((S - (-112)) / 90, 0, 1)
    rgb = np.zeros((H_SPEC, W, 3), dtype=np.uint8)
    rgb[..., 0] = (np.clip(S * 2 - .9, 0, 1) * 255)           # amber/green phosphor ramp
    rgb[..., 1] = (np.clip(S * 1.6, 0, 1) * 255)
    rgb[..., 2] = (np.clip(S * .7 - .1, 0, 1) * 120)
    spec = Image.fromarray(rgb[::-1])
    img.paste(spec, (PAD_L, PAD_T + H_WAVE + 6))
    ys = PAD_T + H_WAVE + 6
    for hz in (100, 1000, 10000):
        yy = ys + H_SPEC - int(np.log(hz / fmin) / np.log(fmax / fmin) * H_SPEC)
        d.line([(PAD_L, yy), (PAD_L + W, yy)], fill=(60, 66, 56))
        d.text((8, yy - 7), f"{hz}Hz" if hz < 1000 else f"{hz // 1000}k", font=f, fill=(143, 129, 96))

    # event markers + time axis
    for t, label in MARKS:
        xx = PAD_L + int(t / dur * W)
        d.line([(xx, PAD_T - 4), (xx, ys + H_SPEC)], fill=(255, 176, 0))
        d.text((xx + 3, PAD_T - 22 - (12 if MARKS.index((t, label)) % 2 else 0)), label, font=f, fill=(255, 176, 0))
    for s in range(0, 21, 2):
        xx = PAD_L + int(s / dur * W)
        d.text((xx - 6, ys + H_SPEC + 6), f"{s}s", font=f, fill=(143, 129, 96))
    img.save(OUT)
    print("saved", OUT, img.size)

if __name__ == "__main__":
    main()
