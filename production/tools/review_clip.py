#!/usr/bin/env python3
"""Review an AI-generated clip against the approved still, so the best of 6-8 candidates can be chosen with numbers.

It assumes a LOCKED camera and the same framing as the reference still (E01: clips C1 and C4).
Reference still, analysis boxes and the REC-lamp cycle come from production/<EP>/episode.json ("review" and "video.lamp").

Usage:
  python3 production/tools/review_clip.py candidate.mp4 --ep E01 [--ref image.png] [--offset 1.5] [--out review_dir]
    --offset  seconds to add to clip time to get timeline time (C1: 1.5, C4: 11.5) -- used for the REC lamp schedule

Outputs (in --out, default: <clip name>_review/):
  sheet.png    frames every 0.5 s (clip time / timeline time)
  metrics.png  4 plots: face drift, mouth motion, eye motion, REC lamp (observed vs expected)
  and a text report on stdout.

How to read it (heuristics, not laws):
  face drift   how far the face region is from the reference still (grey-level difference, %). Lower = the person stays the same.
  mouth motion frame-to-frame change in the mouth box. Should stay low and flat: the character does not speak.
  eye motion   frame-to-frame change in the eye box. The peaks show WHEN the gaze moves; compare them with the beat sheet.
  REC lamp     redness of the lamp box. Compare the observed blink with the expected on/off cycle (E01: 0.8 s on / 0.8 s off).
"""
import argparse, json, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
W, H, FPS = 864, 1536, 24
BOX = {"face": (270, 430, 620, 820), "eyes": (290, 545, 575, 620), "mouth": (420, 685, 520, 750), "lamp": (281, 480, 321, 520)}

def crop(a, name):
    x0, y0, x1, y1 = BOX[name]
    return a[y0:y1, x0:x1]

def grey(a):
    return a.astype(np.float32) @ np.array([.299, .587, .114], dtype=np.float32)

def redness(a):
    return float((a[..., 0].astype(np.int16) - (a[..., 1].astype(np.int16) + a[..., 2].astype(np.int16)) // 2).max())

def frames(path):
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", path, "-vf", f"fps={FPS},scale={W}:{H}:flags=lanczos",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    n = W * H * 3
    while True:
        b = p.stdout.read(n)
        if len(b) < n: break
        yield np.frombuffer(b, dtype=np.uint8).reshape(H, W, 3)
    p.wait()

def plot(series, width=1200, h=130, title="", ylab="", shade=None, thr=None, fmt="{:.1f}"):
    img = Image.new("RGB", (width, h), (14, 16, 14)); d = ImageDraw.Draw(img)
    try: f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 12)
    except Exception: f = ImageFont.load_default()
    n = len(series); lo, hi = 0, max(max(series), 1e-6) * 1.15
    if shade:
        for i, on in enumerate(shade):
            if on: d.rectangle([60 + i * (width - 70) / n, 18, 60 + (i + 1) * (width - 70) / n, h - 8], fill=(40, 30, 10))
    pts = [(60 + i * (width - 70) / max(n - 1, 1), h - 10 - (v - lo) / (hi - lo) * (h - 30)) for i, v in enumerate(series)]
    d.line(pts, fill=(77, 255, 136), width=2)
    if thr is not None:
        y = h - 10 - (thr - lo) / (hi - lo) * (h - 30); d.line([(60, y), (width - 10, y)], fill=(255, 59, 47))
    d.text((6, 2), title, font=f, fill=(255, 176, 0)); d.text((6, h - 24), f"max {fmt.format(max(series))}", font=f, fill=(143, 129, 96))
    return img

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clip"); ap.add_argument("--ep", default="E01"); ap.add_argument("--ref")
    ap.add_argument("--offset", type=float, default=0.0); ap.add_argument("--out"); ap.add_argument("--lamp-thr", type=float, default=60)
    a = ap.parse_args()
    global BOX
    cfg_path = f"{ROOT}/production/{a.ep}/episode.json"
    period, on = 1.6, .8
    if os.path.exists(cfg_path):
        with open(cfg_path, encoding="utf-8") as f: cfg = json.load(f)
        BOX = {k: tuple(v) for k, v in cfg["review"]["boxes"].items()}
        a.ref = a.ref or f"{ROOT}/production/{a.ep}/{cfg['review']['ref']}"
        period, on = cfg["video"]["lamp"]["period"], cfg["video"]["lamp"]["on"]
    a.ref = a.ref or f"{ROOT}/production/{a.ep}/source/mia_base_A.png"
    out = a.out or os.path.splitext(a.clip)[0] + "_review"; os.makedirs(out, exist_ok=True)

    ref = np.asarray(Image.open(a.ref).convert("RGB").resize((W, H)))
    ref_face = grey(crop(ref, "face")); ref_mean = ref.reshape(-1, 3).mean(axis=0)
    prev = None; face, mouth, eyes, lamp, color = [], [], [], [], []; thumbs = []
    for i, fr in enumerate(frames(a.clip)):
        face.append(float(np.abs(grey(crop(fr, "face")) - ref_face).mean() / 255 * 100))
        gm, ge = grey(crop(fr, "mouth")), grey(crop(fr, "eyes"))
        if prev is None: mouth.append(0.0); eyes.append(0.0)
        else:
            mouth.append(float(np.abs(gm - prev[0]).mean())); eyes.append(float(np.abs(ge - prev[1]).mean()))
        prev = (gm, ge)
        lamp.append(redness(crop(fr, "lamp"))); color.append(float(np.abs(fr.reshape(-1, 3).mean(axis=0) - ref_mean).mean()))
        if i % (FPS // 2) == 0: thumbs.append((i / FPS, Image.fromarray(fr).resize((216, 384))))
    n = len(face)
    if n == 0: sys.exit("no frames decoded")

    # contact sheet
    cols = min(len(thumbs), 8); rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 222, rows * 410), (20, 20, 20)); d = ImageDraw.Draw(sheet)
    for k, (t, im) in enumerate(thumbs):
        x, y = (k % cols) * 222, (k // cols) * 410
        sheet.paste(im, (x + 3, y + 24)); d.text((x + 6, y + 4), f"c{t:.1f}s  t{t + a.offset:.1f}s", fill=(255, 176, 0))
    sheet.save(f"{out}/sheet.png")

    # lamp: observed vs expected blink (on during the first 0.8 s of each 1.6 s on the timeline)
    obs = [v > a.lamp_thr for v in lamp]
    exp = [((i / FPS + a.offset) % period) < on for i in range(n)]
    tol = 3                                                         # frames around a transition are not scored
    scored = [i for i in range(n) if all(exp[max(0, min(n - 1, i + k))] == exp[i] for k in range(-tol, tol + 1))]
    match = sum(obs[i] == exp[i] for i in scored) / max(len(scored), 1) * 100

    plots = [plot(face, title="face drift vs reference (%, lower = same person)", fmt="{:.1f}%"),
             plot(mouth, title="mouth motion (frame diff, should be low and flat)", fmt="{:.2f}"),
             plot(eyes, title="eye-area motion (peaks = the gaze moves)", fmt="{:.2f}"),
             plot(lamp, title=f"REC lamp redness (shaded = expected ON, threshold {a.lamp_thr:g})", shade=exp, thr=a.lamp_thr, fmt="{:.0f}")]
    sheet2 = Image.new("RGB", (1200, 130 * len(plots)))
    for k, p in enumerate(plots): sheet2.paste(p, (0, 130 * k))
    sheet2.save(f"{out}/metrics.png")

    def peaks(series, k=3):
        idx = np.argsort(series)[::-1]; got = []
        for i in idx:
            if all(abs(i - j) > FPS // 3 for j in got): got.append(int(i))
            if len(got) == k: break
        return sorted(got)

    print(f"frames {n} ({n / FPS:.2f}s)   offset {a.offset}s   output: {out}")
    print(f"face drift     mean {np.mean(face):5.1f}%   max {np.max(face):5.1f}%")
    print(f"mouth motion   mean {np.mean(mouth):5.2f}    max {np.max(mouth):5.2f}   (lower is better; compare candidates)")
    print(f"colour drift   mean {np.mean(color):5.1f}/255 (lighting continuity vs the still)")
    print("eye-motion peaks at clip time:", ", ".join(f"{i / FPS:.2f}s (t={i / FPS + a.offset:.2f}s)" for i in peaks(eyes)))
    trans = [(i / FPS, "ON" if obs[i] else "OFF") for i in range(1, n) if obs[i] != obs[i - 1]]
    print("REC lamp observed switches:", ", ".join(f"{t:.2f}s->{s}" for t, s in trans) or "none detected")
    print(f"REC lamp matches the expected 0.8s/0.8s cycle on {match:.0f}% of scored frames")

if __name__ == "__main__":
    main()
