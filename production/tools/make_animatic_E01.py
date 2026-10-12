#!/usr/bin/env python3
"""E01 animatic: the finished timing, built from the approved still (production/E01/source/mia_base_A.png).

It is NOT the final video (the AI clips will replace S2-S6).  It is
  * a timing reference for the AI clips (cuts, push-ins, REC lamp blinks, glitches, CRT power-off), and
  * a fallback "plan B" rough cut made only from the approved still.

Outputs (production/E01/animatic/):
  E01_animatic_clean.mp4     tape look + overlay + temp sound mix
  E01_animatic_labeled.mp4   same, with shot labels burned in (for review)

Needs: Pillow, numpy, ffmpeg.  The overlay and audio must exist (see make_overlay_E01.py / make_audio_E01.py).
Usage: python3 production/tools/make_animatic_E01.py
"""
import os, subprocess, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
E01 = f"{ROOT}/production/E01"
OUT = f"{E01}/animatic"
SRC_PATH = f"{E01}/source/mia_base_A.png"
OVERLAY = f"{E01}/overlay/E01_overlay_alpha.webm"
AUDIO = f"{E01}/audio/E01_audio_temp_mix.wav"
LOOK = f"{ROOT}/production/tools/tape_look.sh"

W, H, FPS, DUR = 1080, 1920, 24, 20
NF = FPS * DUR
SW, SH = 864, 1536                       # source size
LAMP = (301.0, 499.6)                    # REC lamp in source pixels  (= 376, 625 in 1080x1920)
LAMP_OUT = (376, 625)

# ---------------------------------------------------------------- cameras
# keyframes: (t, centre_x, centre_y, zoom) in SOURCE pixels; zoom 1 = the whole 864x1536 frame
CAM = {
    "S2": (2.0, 6.0,  [(2.0, 432, 768, 1.000), (6.0, 432, 735, 1.040)]),
    "S3": (6.0, 9.0,  [(6.0, 195, 623, 2.62), (9.0, 195, 612, 2.72)]),          # headset close-up (stand-in)
    "S4": (9.0, 12.0, [(9.0, 712, 699, 2.84), (12.0, 712, 690, 2.92)]),         # CRT / cassettes (stand-in for the deck)
    "S5": (12.0, 16.0, [(12.0, 432, 735, 1.020), (16.0, 420, 735, 1.050)]),
    "S6": (16.0, 20.0, [(16.0, 440, 1160, 2.54), (20.0, 440, 1150, 2.62)]),     # cassette pendant (stand-in for the hand on the deck)
}
LABELS = {"S1": "S1 · BLACK + REC DOT (editor)", "S2": "S2 · CLIP 1 · STILL STAND-IN", "S3": "S3 · CLIP 2 · STAND-IN",
          "S4": "S4 · CLIP 3 · STAND-IN (deck not generated yet)", "S5": "S5 · CLIP 4 · STILL STAND-IN",
          "S6": "S6 · STILL C · STAND-IN", "S7": "S7 · CRT POWER-OFF (editor)"}
SHOT_RANGES = [("S1", 0, 2.0), ("S2", 2.0, 6.0), ("S3", 6.0, 9.0), ("S4", 9.0, 12.0), ("S5", 12.0, 16.0), ("S6", 16.0, 18.5), ("S7", 18.5, 20.0)]

def smooth(x):
    x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)

def cam_at(shot, t):
    keys = CAM[shot][2]
    for (t0, x0, y0, z0), (t1, x1, y1, z1) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            k = smooth((t - t0) / (t1 - t0))
            return x0 + (x1 - x0) * k, y0 + (y1 - y0) * k, z0 + (z1 - z0) * k
    k = keys[-1]; return k[1], k[2], k[3]

def view(src, cx, cy, zoom):
    vw = SW / zoom; s = vw / W
    return src.transform((W, H), Image.AFFINE, (s, 0, cx - vw / 2, 0, s, cy - (H * s) / 2), resample=Image.BICUBIC)

# ---------------------------------------------------------------- REC lamp: on in the first 0.8 s of every 1.6 s (same cycle as the overlay)
def lamp_on(t):
    return (t % 1.6) < 0.8

def make_lamp_off(src):
    """paint the lamp out of the still so it can 'blink' (animatic only; the AI clip will blink it for real)"""
    a = np.asarray(src).astype(float); cx, cy = int(LAMP[0]), int(LAMP[1])
    yy, xx = np.mgrid[0:SH, 0:SW]; d = np.hypot(xx - LAMP[0], yy - LAMP[1])
    ring = a[(d > 17) & (d < 24)].mean(axis=0)
    mask = Image.fromarray((np.clip(1 - (d - 8) / 7, 0, 1) * 255).astype("uint8")).filter(ImageFilter.GaussianBlur(2))
    patch = Image.new("RGB", src.size, tuple(int(v * .9) for v in ring))
    return Image.composite(patch, src, mask)

# ---------------------------------------------------------------- effects
def glitch(img, seed, strength=1.0):
    rng = np.random.default_rng(seed); a = np.asarray(img).copy()
    for _ in range(int(7 * strength) + 2):
        y = int(rng.integers(0, H - 160)); h = int(rng.integers(18, 150))
        a[y:y + h] = np.roll(a[y:y + h], int(rng.integers(-130, 130) * strength), axis=1)
    a[..., 0] = np.roll(a[..., 0], 7, axis=1); a[..., 2] = np.roll(a[..., 2], -7, axis=1)
    return Image.fromarray(a)

def rec_dot_frame(t):
    base = Image.new("RGB", (W, H), (11, 13, 12))
    if lamp_on(t) or 1.6 <= t < 2.4:
        glow = Image.new("RGB", (W, H), (0, 0, 0)); gd = ImageDraw.Draw(glow)
        gd.ellipse([LAMP_OUT[0] - 34, LAMP_OUT[1] - 34, LAMP_OUT[0] + 34, LAMP_OUT[1] + 34], fill=(150, 25, 18))
        glow = glow.filter(ImageFilter.GaussianBlur(26))
        base = Image.fromarray(np.clip(np.asarray(base).astype(int) + np.asarray(glow), 0, 255).astype("uint8"))
        ImageDraw.Draw(base).ellipse([LAMP_OUT[0] - 12, LAMP_OUT[1] - 12, LAMP_OUT[0] + 12, LAMP_OUT[1] + 12], fill=(255, 70, 52))
    return base

def crt_off(img, u):
    """u 0..1 over 18.5 -> 19.6 s : collapse to a line, line to a dot, dot fades"""
    black = Image.new("RGB", (W, H), (0, 0, 0))
    if u < .45:                                         # vertical collapse
        k = 1 - smooth(u / .45) * .99
        sq = ImageEnhance.Brightness(img).enhance(1 + (1 - k) * .9).resize((W, max(2, int(H * k))), Image.BILINEAR)
        black.paste(sq, (0, (H - sq.height) // 2)); return black
    if u < .75:                                         # line shrinks horizontally
        k = 1 - smooth((u - .45) / .3) * .98; w = max(10, int(W * k))
        ImageDraw.Draw(black).rectangle([(W - w) // 2, H // 2 - 2, (W + w) // 2, H // 2 + 2], fill=(235, 255, 240)); return black.filter(ImageFilter.GaussianBlur(1))
    f = 1 - smooth((u - .75) / .25)                      # dot fades
    d = ImageDraw.Draw(black); r = 6
    d.ellipse([W // 2 - r, H // 2 - r, W // 2 + r, H // 2 + r], fill=(int(235 * f), int(255 * f), int(240 * f)))
    return black.filter(ImageFilter.GaussianBlur(3))

# ---------------------------------------------------------------- frame renderer
def main():
    os.makedirs(OUT, exist_ok=True)
    src_on = Image.open(SRC_PATH).convert("RGB"); src_off = make_lamp_off(src_on)
    pick = lambda t: src_on if lamp_on(t) else src_off

    def shot_frame(shot, t):
        cx, cy, z = cam_at(shot, t)
        return view(pick(t), cx, cy, z)

    tmp = tempfile.mkdtemp(prefix="e01_anim_")
    raw = f"{tmp}/base_raw.mp4"
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                            "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", raw], stdin=subprocess.PIPE)
    for f in range(NF):
        t = f / FPS
        if t < 1.8:
            img = rec_dot_frame(t)
        elif t < 2.2:                                       # S1 -> S2 cross dissolve (0.4 s)
            k = smooth((t - 1.8) / .4)
            img = Image.blend(rec_dot_frame(t), shot_frame("S2", max(t, 2.0)), k)
        elif t < 6.0:  img = shot_frame("S2", t)
        elif t < 9.0:  img = shot_frame("S3", t)
        elif t < 12.0: img = shot_frame("S4", t)
        elif t < 16.0: img = shot_frame("S5", t)
        elif t < 18.5: img = shot_frame("S6", t)
        else:
            img = crt_off(shot_frame("S6", t), min(1.0, (t - 18.5) / 1.1))
        # impact shake when the hand lands (16.0 s)
        if 16.0 <= t < 16.0 + 4 / FPS:
            dy = [10, -6, 3, -1][int(round((t - 16.0) * FPS))]
            img = img.transform((W, H), Image.AFFINE, (1, 0, 0, 0, 1, -dy))
        # glitches: 11.0 (door closed), 18.3 (STOP)
        for g_t, seed in ((11.0, 3), (18.3, 5)):
            if g_t <= t < g_t + 3 / FPS:
                img = glitch(img, seed + int(round((t - g_t) * FPS)))
        enc.stdin.write(img.tobytes())
    enc.stdin.close(); enc.wait()

    look = f"{tmp}/base_look.mp4"
    subprocess.run(["bash", LOOK, raw, look], check=True, env={**os.environ, "GRAIN": "11"})

    def composite(dst, labeled):
        vf = "[0:v][1:v]overlay=format=auto"
        if labeled:
            fnt = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
            for name, a, b in SHOT_RANGES:
                txt = f"{LABELS[name]}  {a:.1f}-{b:.1f}s".replace(":", "\\:")
                vf += (f",drawtext=fontfile={fnt}:text='{txt}':x=40:y=1700:fontsize=30:fontcolor=white:box=1:boxcolor=black@0.55:"
                       f"boxborderw=10:enable='gte(t,{a})*lt(t,{b})'")
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", look, "-c:v", "libvpx-vp9", "-i", OVERLAY]
        if os.path.exists(AUDIO): cmd += ["-i", AUDIO]
        cmd += ["-filter_complex", vf + "[v]", "-map", "[v]"]
        if os.path.exists(AUDIO): cmd += ["-map", "2:a", "-c:a", "aac", "-b:a", "192k"]
        cmd += ["-c:v", "libx264", "-crf", "26", "-maxrate", "7M", "-bufsize", "14M", "-preset", "medium", "-pix_fmt", "yuv420p", "-shortest", dst]
        subprocess.run(cmd, check=True)

    composite(f"{OUT}/E01_animatic_clean.mp4", False)
    composite(f"{OUT}/E01_animatic_labeled.mp4", True)
    import shutil; shutil.rmtree(tmp, ignore_errors=True)
    print("done:", sorted(os.listdir(OUT)))

if __name__ == "__main__":
    main()
