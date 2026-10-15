#!/usr/bin/env python3
"""Episode assembly: builds the cut from the SELECTED clips with the locked timing, or an all-stand-in animatic.

Everything (shots, timings, push-ins, stand-in cameras, effects, lamp) comes from production/<EP>/episode.json ("video" section).

Put the chosen files in  production/<EP>/generated/selected/  using the file names in the "video.shots[].file" fields
(E01: C1.mp4 C2.mp4 C3.mp4 C4.mp4 S6_C.png).  A shot whose file is missing is replaced by its stand-in (a crop of the approved
still), so shots can be swapped in one at a time.

What it does: push-ins, REC-dot opening, dissolves, impact shake, glitches, CRT power-off, tape look (video layers only),
overlay, sound.

Usage:
  python3 production/tools/assemble.py --ep E01 [--labeled | --both] [--standin-only] [--audio FILE] [--no-look]
                                       [--clips DIR] [--name NAME] [--out-dir DIR] [--quality draft|final]
  python3 production/tools/make_animatic.py --ep E01            (= --standin-only --both --quality draft into production/<EP>/animatic/)
Output: <out-dir>/<name>.mp4   (--both: <name>_clean.mp4 and <name>_labeled.mp4).  Default out-dir: production/<EP>/build, name: <EP>_cut
Needs: Pillow, numpy, ffmpeg; the overlay and audio from make_overlay.py / make_audio.py.
"""
import argparse, os, shutil, subprocess, sys, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import episode as epcfg

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOOK = f"{ROOT}/production/tools/tape_look.sh"
W, H = 1080, 1920
def find_label_font():
    """font for the burned-in shot labels (review videos only); override with LABEL_FONT=/path/to/font.ttf"""
    for c in [os.environ.get("LABEL_FONT"), "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
              "/usr/share/fonts/TTF/DejaVuSansMono.ttf", "/System/Library/Fonts/Menlo.ttc", "/System/Library/Fonts/Supplemental/Courier New.ttf",
              "/Library/Fonts/Courier New.ttf", "C:/Windows/Fonts/consola.ttf"]:
        if c and os.path.exists(c): return c
    return None

def frame_ms(t): return int(round(t * 1000))      # lamp phase in whole milliseconds (float % misjudges exact multiples like 4.0 s)

smooth = lambda x: (lambda v: v * v * (3 - 2 * v))(max(0.0, min(1.0, x)))

# ---------------------------------------------------------------- effects (episode independent)
def glitch(img, seed, strength=1.0):
    rng = np.random.default_rng(seed); a = np.asarray(img).copy()
    for _ in range(int(7 * strength) + 2):
        y = int(rng.integers(0, H - 160)); h = int(rng.integers(18, 150))
        a[y:y + h] = np.roll(a[y:y + h], int(rng.integers(-130, 130) * strength), axis=1)
    a[..., 0] = np.roll(a[..., 0], 7, axis=1); a[..., 2] = np.roll(a[..., 2], -7, axis=1)
    return Image.fromarray(a)

def crt_off(img, u):
    """u 0..1 : collapse to a line, line to a dot, dot fades"""
    black = Image.new("RGB", (W, H), (0, 0, 0))
    if u < .45:
        k = 1 - smooth(u / .45) * .99
        sq = ImageEnhance.Brightness(img).enhance(1 + (1 - k) * .9).resize((W, max(2, int(H * k))), Image.BILINEAR)
        black.paste(sq, (0, (H - sq.height) // 2)); return black
    if u < .75:
        k = 1 - smooth((u - .45) / .3) * .98; w = max(10, int(W * k))
        ImageDraw.Draw(black).rectangle([(W - w) // 2, H // 2 - 2, (W + w) // 2, H // 2 + 2], fill=(235, 255, 240)); return black.filter(ImageFilter.GaussianBlur(1))
    f = 1 - smooth((u - .75) / .25)
    ImageDraw.Draw(black).ellipse([W // 2 - 6, H // 2 - 6, W // 2 + 6, H // 2 + 6], fill=(int(235 * f), int(255 * f), int(240 * f)))
    return black.filter(ImageFilter.GaussianBlur(3))

class ClipReader:
    """sequential reader that fills 1080x1920 (centre-crop if the aspect differs); holds the last frame at the end"""
    def __init__(self, path, head, dur, fps):
        cmd = ["ffmpeg", "-v", "error", "-ss", str(head), "-i", path, "-t", str(dur + .3), "-vf",
               f"fps={fps},scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H}",
               "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
        self.p = subprocess.Popen(cmd, stdout=subprocess.PIPE); self.last = None; self.n = W * H * 3; self.idx = 0
        self.first = self.next()                       # None if the file could not be decoded
    def next(self):
        b = self.p.stdout.read(self.n)
        if len(b) == self.n: self.last = Image.frombytes("RGB", (W, H), b)
        return self.last
    def close(self):
        try: self.p.stdout.close(); self.p.kill()
        except Exception: pass

# ---------------------------------------------------------------- episode
class Episode:
    def __init__(self, ep, clips_dir=None, standin_only=False):
        self.ep = ep; self.dir = f"{ROOT}/production/{ep}"
        self.cfg = epcfg.load(ep, need=("overlay", "video")); v = self.cfg["video"]; self.v = v
        self.fps = int(self.cfg["fps"]); self.dur = float(self.cfg["duration"]); self.nf = int(round(self.fps * self.dur))
        self.shots = {s["id"]: s for s in v["shots"]}; self.order = [s["id"] for s in v["shots"]]
        self.clips_dir = clips_dir or f"{self.dir}/generated/selected"
        self.standin_only = standin_only
        self.src_on = Image.open(f"{self.dir}/{v['base_image']}").convert("RGB")
        self.SW, self.SH = self.src_on.size
        self.lamp = v["lamp"]; self.src_off = self.make_lamp_off()
        self.real = {}; self.stills = {}; self.readers = {}
        for sid, s in self.shots.items():
            if "file" not in s: continue
            p = f"{self.clips_dir}/{s['file']}"; ok = (not standin_only) and os.path.exists(p)
            if ok and not s["file"].lower().endswith((".png", ".jpg", ".jpeg", ".webp")): ok = self.check_clip(sid, p)
            self.real[sid] = ok
            if ok and s["file"].lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                im = Image.open(p).convert("RGB"); r = max(W / im.width, H / im.height)
                im = im.resize((int(im.width * r + .5), int(im.height * r + .5)), Image.LANCZOS)
                x0, y0 = (im.width - W) // 2, (im.height - H) // 2
                self.stills[sid] = im.crop((x0, y0, x0 + W, y0 + H))

    def check_clip(self, sid, path):
        """warn about clips shorter than the timeline needs; refuse files ffprobe cannot read"""
        s = self.shots[sid]
        try:
            d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                                     capture_output=True, text=True).stdout.strip())
        except Exception: d = 0.0
        if d <= 0.1:
            print(f"  WARNING {sid}: {os.path.basename(path)} cannot be read (0 s) -> using the stand-in"); return False
        need = s.get("head", 0) + (s["t1"] - s["t0"])
        if d < need - 0.05:
            print(f"  WARNING {sid}: {os.path.basename(path)} is {d:.2f} s but the cut needs {need:.2f} s (head {s.get('head', 0)} + {s['t1'] - s['t0']:.1f}); "
                  f"the last frame will be held for {need - d:.2f} s")
        return True

    # ---- lamp: on during the first `on` seconds of every `period` (whole milliseconds, so exact multiples are not misjudged)
    def lamp_on(self, t): return (frame_ms(t) % frame_ms(self.lamp["period"])) < frame_ms(self.lamp["on"])
    def make_lamp_off(self):
        """paint the lamp out of the still so the stand-in can 'blink' (the AI clip blinks it for real)"""
        src = self.src_on; lx, ly = self.lamp["src"]
        a = np.asarray(src).astype(float); yy, xx = np.mgrid[0:self.SH, 0:self.SW]; d = np.hypot(xx - lx, yy - ly)
        ring = a[(d > 17) & (d < 24)].mean(axis=0)
        mask = Image.fromarray((np.clip(1 - (d - 8) / 7, 0, 1) * 255).astype("uint8")).filter(ImageFilter.GaussianBlur(2))
        return Image.composite(Image.new("RGB", src.size, tuple(int(c * .9) for c in ring)), src, mask)

    # ---- stand-in camera on the still: keyframes (t, centre_x, centre_y, zoom) in SOURCE pixels
    def cam_at(self, shot, t):
        keys = self.shots[shot]["standin"]
        for (t0, x0, y0, z0), (t1, x1, y1, z1) in zip(keys, keys[1:]):
            if t0 <= t <= t1:
                k = smooth((t - t0) / (t1 - t0)); return x0 + (x1 - x0) * k, y0 + (y1 - y0) * k, z0 + (z1 - z0) * k
        k = keys[-1]; return k[1], k[2], k[3]
    def view(self, src, cx, cy, zoom):
        vw = self.SW / zoom; s = vw / W; vh = H * s
        cx = min(max(cx, vw / 2), self.SW - vw / 2) if vw <= self.SW else self.SW / 2          # keep the window inside the still:
        cy = min(max(cy, vh / 2), self.SH - vh / 2) if vh <= self.SH else self.SH / 2          # no black bands at the edges
        return src.transform((W, H), Image.AFFINE, (s, 0, cx - vw / 2, 0, s, cy - vh / 2), resample=Image.BICUBIC)
    def standin(self, sid, t):
        return self.view(self.src_on if self.lamp_on(t) else self.src_off, *self.cam_at(sid, t))

    def rec_dot_frame(self, t):
        base = Image.new("RGB", (W, H), (11, 13, 12)); ox, oy = self.lamp["out"]
        flick = t < self.cfg["overlay"].get("flicker_until", 0) and int(round(t * self.fps)) % 3 == 0     # same power-on flicker as the overlay
        if self.lamp_on(t) and not flick:
            glow = Image.new("RGB", (W, H), (0, 0, 0))
            ImageDraw.Draw(glow).ellipse([ox - 34, oy - 34, ox + 34, oy + 34], fill=(150, 25, 18))
            glow = glow.filter(ImageFilter.GaussianBlur(26))
            base = Image.fromarray(np.clip(np.asarray(base).astype(int) + np.asarray(glow), 0, 255).astype("uint8"))
            ImageDraw.Draw(base).ellipse([ox - 12, oy - 12, ox + 12, oy + 12], fill=(255, 70, 52))
        return base

    def push(self, img, sid, t):
        s = self.shots[sid]; p = s.get("push")
        if not p: return img
        k = smooth((t - s["t0"]) / (s["t1"] - s["t0"])); z = p["z"][0] + (p["z"][1] - p["z"][0]) * k
        if z <= 1.0001: return img
        cx, cy = p["c"][0] * W, p["c"][1] * H                                   # fixed point of the zoom: c stays where it is, the rest grows away from it
        return img.transform((W, H), Image.AFFINE, (1 / z, 0, cx * (1 - 1 / z), 0, 1 / z, cy * (1 - 1 / z)), resample=Image.BICUBIC)

    def render_shot(self, sid, t):
        s = self.shots[sid]; kind = s.get("kind")
        if kind == "rec_dot": return self.rec_dot_frame(t)
        if kind == "crt_off":
            return crt_off(self.render_shot(s["from"], min(t, self.shots[s["from"]]["t1"] - 1e-3)), min(1.0, (t - s["t0"]) / s["len"]))
        if not self.real.get(sid): return self.standin(sid, t)
        if sid in self.stills: return self.push(self.stills[sid], sid, t)
        if sid not in self.readers:
            self.readers[sid] = ClipReader(f"{self.clips_dir}/{s['file']}", s.get("head", 0), s["t1"] - s["t0"], self.fps)
        r = self.readers[sid]
        if r.first is None:
            print(f"  WARNING {sid}: no frames decoded from {s['file']} -> using the stand-in"); self.real[sid] = False; return self.standin(sid, t)
        if t < s["t0"]: return self.push(r.first, sid, s["t0"])                 # dissolve pre-roll: the first used frame
        k = int(round((t - s["t0"]) * self.fps))
        while r.idx < k: r.next(); r.idx += 1
        return self.push(r.last or r.first, sid, t)

    def frame(self, f):
        t = f / self.fps; img = None
        for e in self.v["effects"]:                                             # dissolves override the plain shot lookup
            if e["type"] == "dissolve" and e["t0"] <= t < e["t1"]:
                img = Image.blend(self.render_shot(e["from"], t), self.render_shot(e["to"], max(t, self.shots[e["to"]]["t0"])),
                                  smooth((t - e["t0"]) / (e["t1"] - e["t0"])))
        if img is None:
            sid = next((i for i in self.order if self.shots[i]["t0"] <= t < self.shots[i]["t1"]), self.order[-1])
            img = self.render_shot(sid, t)
        for e in self.v["effects"]:
            if e["type"] == "impact" and e["t"] <= t < e["t"] + len(e["offsets"]) / self.fps:
                dy = e["offsets"][int(round((t - e["t"]) * self.fps))]; img = img.transform((W, H), Image.AFFINE, (1, 0, 0, 0, 1, -dy))
            if e["type"] == "glitch" and e["t"] <= t < e["t"] + e["frames"] / self.fps:
                img = glitch(img, e["seed"] + int(round((t - e["t"]) * self.fps)))
        return img

    def label(self, sid):
        s = self.shots[sid]
        if self.standin_only or s.get("kind"): return s.get("label", sid) if self.standin_only else "editor"
        return "REAL " + s["file"] if self.real.get(sid) else "stand-in"

    def close(self):
        for r in self.readers.values(): r.close()

# ---------------------------------------------------------------- main
def run(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ep", default="E01"); ap.add_argument("--clips"); ap.add_argument("--out-dir"); ap.add_argument("--name")
    ap.add_argument("--audio"); ap.add_argument("--no-look", action="store_true"); ap.add_argument("--standin-only", action="store_true")
    ap.add_argument("--labeled", action="store_true"); ap.add_argument("--both", action="store_true")
    ap.add_argument("--quality", choices=["draft", "final"], default="final")
    a = ap.parse_args(argv)
    E = Episode(a.ep, a.clips, a.standin_only); ep = a.ep
    out_dir = a.out_dir or f"{E.dir}/build"; os.makedirs(out_dir, exist_ok=True); name = a.name or f"{ep}_cut"
    audio = a.audio or f"{E.dir}/audio/{ep}_audio_temp_mix.wav"; overlay = f"{E.dir}/overlay/{ep}_overlay_alpha.webm"
    for sid in E.order:
        if "file" in E.shots[sid]:
            print(f"  {sid}: {'REAL  ' + E.shots[sid]['file'] if E.real.get(sid) else 'stand-in' + ('' if E.standin_only else ' (missing ' + E.shots[sid]['file'] + ')')}")

    tmp = tempfile.mkdtemp(prefix=f"{ep.lower()}_asm_"); raw = f"{tmp}/base_raw.mp4"
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(E.fps),
                            "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", raw], stdin=subprocess.PIPE)
    for f in range(E.nf): enc.stdin.write(E.frame(f).tobytes())
    enc.stdin.close(); enc.wait(); E.close()

    base = raw
    if not a.no_look:
        base = f"{tmp}/base_look.mp4"
        subprocess.run(["bash", LOOK, raw, base], check=True, env={**os.environ, "GRAIN": os.environ.get("GRAIN", "11")})
    label_font = find_label_font()
    want_labels = a.labeled or a.both
    if want_labels and not label_font:
        print("  NOTE: no label font found (set LABEL_FONT=/path/to/font.ttf); shot labels are skipped")
        if a.both is False and a.labeled: a.labeled = False
    crf, rate, buf = ("26", "7M", "14M") if a.quality == "draft" else ("20", "12M", "24M")

    def composite(dst, labeled):
        vf = "[0:v][1:v]overlay=format=auto"
        if labeled and label_font:
            fnt = label_font
            for sid in E.order:
                s = E.shots[sid]; txt = f"{E.label(sid)}  {s['t0']:.1f}-{s['t1']:.1f}s".replace(":", "\\:")
                if not E.standin_only: txt = f"{sid} {txt}"
                vf += (f",drawtext=fontfile={fnt}:text='{txt}':x=40:y=1700:fontsize=30:fontcolor=white:box=1:boxcolor=black@0.55:"
                       f"boxborderw=10:enable='gte(t,{s['t0']})*lt(t,{s['t1']})'")
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", base, "-c:v", "libvpx-vp9", "-i", overlay]
        if os.path.exists(audio): cmd += ["-i", audio]
        cmd += ["-filter_complex", vf + "[v]", "-map", "[v]"]
        if os.path.exists(audio): cmd += ["-map", "2:a", "-c:a", "aac", "-b:a", "192k"]
        cmd += ["-c:v", "libx264", "-crf", crf, "-maxrate", rate, "-bufsize", buf, "-preset", "medium",
                "-pix_fmt", "yuv420p", "-shortest", dst]
        subprocess.run(cmd, check=True); print("built:", dst)

    if a.both:
        composite(f"{out_dir}/{name}_clean.mp4", False)
        if label_font: composite(f"{out_dir}/{name}_labeled.mp4", True)
    else:
        composite(f"{out_dir}/{name}.mp4", a.labeled)
    shutil.rmtree(tmp, ignore_errors=True)

if __name__ == "__main__":
    run()
