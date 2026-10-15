#!/usr/bin/env python3
"""E01 assembly: builds the cut from the SELECTED clips, with the locked timing (see E01_클립프롬프트_초단위.md, section 6).

Put the chosen files in  production/E01/generated/selected/  :
    C1.mp4   S2  (t 2.0-6.0)   REC lamp check          -> uses clip time 0.5-4.5
    C2.mp4   S3  (t 6.0-9.0)   headset                 -> uses clip time 0.5-3.5
    C3.mp4   S4  (t 9.0-12.0)  cassette in, door       -> uses clip time 0.5-3.5
    C4.mp4   S5  (t 12.0-16.0) gaze to the window      -> uses clip time 0.5-4.5
    S6_C.png S6  (t 16.0-18.5) hand on the deck (still image C)
Any file that is missing is replaced by the animatic stand-in, so you can swap shots in one at a time.

What it does (all from the locked EDL):  push-ins, S1 black + REC dot, 0.4 s dissolve S1->S2, impact shake at 16.0,
glitches at 11.0 and 18.3, CRT power-off, tape look (video layers only), overlay, sound.

Usage:
  python3 production/tools/assemble_E01.py [--out NAME] [--audio FILE] [--no-look] [--labeled] [--clips DIR]
Output: production/E01/build/<NAME>.mp4   (default name: E01_cut)
Needs: Pillow, numpy, ffmpeg; overlay + audio from the other E01 tools.
"""
import argparse, importlib.util, os, shutil, subprocess, tempfile
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("animatic", f"{HERE}/make_animatic_E01.py")
A = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(A)          # reuse constants + effects
W, H, FPS, NF = A.W, A.H, A.FPS, A.NF
E01 = A.E01

# shot -> (clip file, timeline start/end, clip head used, push-in zoom from/to, push-in centre as fraction of the frame)
SHOTS = {
    "S2": dict(file="C1.mp4",   t0=2.0,  t1=6.0,  head=.5, z=(1.00, 1.04), c=(.50, .46)),
    "S3": dict(file="C2.mp4",   t0=6.0,  t1=9.0,  head=.5, z=(1.00, 1.04), c=(.50, .50)),
    "S4": dict(file="C3.mp4",   t0=9.0,  t1=12.0, head=.5, z=(1.00, 1.03), c=(.50, .50)),
    "S5": dict(file="C4.mp4",   t0=12.0, t1=16.0, head=.5, z=(1.00, 1.03), c=(.50, .47)),
    "S6": dict(file="S6_C.png", t0=16.0, t1=18.5, head=0,  z=(1.00, 1.03), c=(.50, .50)),
}

def push(img, shot, t):
    s = SHOTS[shot]; k = A.smooth((t - s["t0"]) / (s["t1"] - s["t0"]))
    z = s["z"][0] + (s["z"][1] - s["z"][0]) * k
    if z <= 1.0001: return img
    cx, cy = s["c"][0] * W, s["c"][1] * H
    return img.transform((W, H), Image.AFFINE, (1 / z, 0, cx - W / (2 * z), 0, 1 / z, cy - H / (2 * z)), resample=Image.BICUBIC)

class ClipReader:
    """sequential 24 fps reader that fills 1080x1920 (centre-crop if the aspect differs); holds the last frame at the end"""
    def __init__(self, path, head, dur):
        cmd = ["ffmpeg", "-v", "error", "-ss", str(head), "-i", path, "-t", str(dur + .3), "-vf",
               f"fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H}",
               "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
        self.p = subprocess.Popen(cmd, stdout=subprocess.PIPE); self.last = None; self.n = W * H * 3
    def next(self):
        b = self.p.stdout.read(self.n)
        if len(b) == self.n: self.last = Image.frombytes("RGB", (W, H), b)
        return self.last
    def close(self):
        try: self.p.stdout.close(); self.p.kill()
        except Exception: pass

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clips", default=f"{E01}/generated/selected"); ap.add_argument("--out", default="E01_cut")
    ap.add_argument("--audio", default=A.AUDIO); ap.add_argument("--no-look", action="store_true"); ap.add_argument("--labeled", action="store_true")
    a = ap.parse_args()
    os.makedirs(f"{E01}/build", exist_ok=True)

    src_on = Image.open(A.SRC_PATH).convert("RGB"); src_off = A.make_lamp_off(src_on)
    pick = lambda t: src_on if A.lamp_on(t) else src_off
    standin = lambda shot, t: A.view(pick(t), *A.cam_at(shot, t))

    # which shots use real files
    real, readers, stills = {}, {}, {}
    for shot, s in SHOTS.items():
        p = f"{a.clips}/{s['file']}"; real[shot] = os.path.exists(p)
        print(f"  {shot}: {'REAL  ' + s['file'] if real[shot] else 'stand-in (missing ' + s['file'] + ')'}")
        if real[shot] and s["file"].lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            im = Image.open(p).convert("RGB"); r = max(W / im.width, H / im.height)
            im = im.resize((int(im.width * r + .5), int(im.height * r + .5)), Image.LANCZOS)
            stills[shot] = im.crop(((im.width - W) // 2, (im.height - H) // 2, (im.width - W) // 2 + W, (im.height - H) // 2 + H))

    def shot_frame(shot, t):
        s = SHOTS[shot]
        if not real[shot]: return standin(shot, t)
        if shot in stills: return push(stills[shot], shot, t)
        if shot not in readers:
            readers[shot] = ClipReader(f"{a.clips}/{s['file']}", s["head"], s["t1"] - s["t0"]); readers[shot].first = readers[shot].next()
            readers[shot].idx = 0
        r = readers[shot]
        if t < s["t0"]: return push(r.first, shot, s["t0"])                    # dissolve pre-roll uses the first used frame
        k = int(round((t - s["t0"]) * FPS))
        while r.idx < k: r.next(); r.idx += 1
        return push(r.last or r.first, shot, t)

    tmp = tempfile.mkdtemp(prefix="e01_asm_"); raw = f"{tmp}/base_raw.mp4"
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                            "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", raw], stdin=subprocess.PIPE)
    for f in range(NF):
        t = f / FPS
        if t < 1.8:   img = A.rec_dot_frame(t)
        elif t < 2.2: img = Image.blend(A.rec_dot_frame(t), shot_frame("S2", max(t, 2.0)), A.smooth((t - 1.8) / .4))
        elif t < 6.0: img = shot_frame("S2", t)
        elif t < 9.0: img = shot_frame("S3", t)
        elif t < 12.0: img = shot_frame("S4", t)
        elif t < 16.0: img = shot_frame("S5", t)
        elif t < 18.5: img = shot_frame("S6", t)
        else:         img = A.crt_off(shot_frame("S6", min(t, 18.499)), min(1.0, (t - 18.5) / 1.1))
        if 16.0 <= t < 16.0 + 4 / FPS:                                          # impact when the hand lands
            dy = [10, -6, 3, -1][int(round((t - 16.0) * FPS))]; img = img.transform((W, H), Image.AFFINE, (1, 0, 0, 0, 1, -dy))
        for g_t, seed in ((11.0, 3), (18.3, 5)):                                # glitches: door closed / STOP
            if g_t <= t < g_t + 3 / FPS: img = A.glitch(img, seed + int(round((t - g_t) * FPS)))
        enc.stdin.write(img.tobytes())
    enc.stdin.close(); enc.wait()
    for r in readers.values(): r.close()

    base = raw
    if not a.no_look:
        base = f"{tmp}/base_look.mp4"
        subprocess.run(["bash", A.LOOK, raw, base], check=True, env={**os.environ, "GRAIN": os.environ.get("GRAIN", "11")})
    vf = "[0:v][1:v]overlay=format=auto"
    if a.labeled:
        fnt = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
        for name, a0, b0 in A.SHOT_RANGES:
            tag = "editor" if name in ("S1", "S7") else (("REAL " + SHOTS[name]["file"]) if real.get(name) else "stand-in")
            txt = f"{name} {tag}  {a0:.1f}-{b0:.1f}s".replace(":", "\\:")
            vf += (f",drawtext=fontfile={fnt}:text='{txt}':x=40:y=1700:fontsize=30:fontcolor=white:box=1:boxcolor=black@0.55:"
                   f"boxborderw=10:enable='gte(t,{a0})*lt(t,{b0})'")
    dst = f"{E01}/build/{a.out}.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", base, "-c:v", "libvpx-vp9", "-i", A.OVERLAY]
    if os.path.exists(a.audio): cmd += ["-i", a.audio]
    cmd += ["-filter_complex", vf + "[v]", "-map", "[v]"]
    if os.path.exists(a.audio): cmd += ["-map", "2:a", "-c:a", "aac", "-b:a", "192k"]
    cmd += ["-c:v", "libx264", "-crf", "20", "-maxrate", "12M", "-bufsize", "24M", "-pix_fmt", "yuv420p", "-shortest", dst]
    subprocess.run(cmd, check=True); shutil.rmtree(tmp, ignore_errors=True)
    print("built:", dst)

if __name__ == "__main__":
    main()
