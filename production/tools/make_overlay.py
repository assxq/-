#!/usr/bin/env python3
"""Episode overlay generator: the tape-frame UI + log captions as a 1080x1920 transparent overlay.

Everything (tape id, side, captions, REC cycle, duration) comes from production/<EP>/episode.json ("overlay" section).

Outputs (production/<EP>/overlay/):
  ui_static.png            UI without counter / REC / captions (transparent)
  ui_cover_t<T>.png        full UI at overlay.cover_t, pick a moment with no caption on screen (cover frames / stills)
  caption_<n>_<slug>.png   each log caption, fully typed (transparent, full canvas, already positioned)
  <EP>_overlay_alpha.webm  VP9 with alpha (small).  Add --prores to also write <EP>_overlay_alpha.mov (ProRes 4444, ~160 MB)
  <EP>_overlay_preview.mp4 overlay on black + temp audio mix (timing reference)

Needs: Pillow, ffmpeg, the VT323 font (Google Fonts, OFL).  Usage:
  VT323_PATH=/path/to/VT323.ttf python3 production/tools/make_overlay.py --ep E01 [--prores | --stills]
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ICONS = f"{ROOT}/icons/png"

_ap = argparse.ArgumentParser(); _ap.add_argument("--ep", default="E01"); _ap.add_argument("--prores", action="store_true"); _ap.add_argument("--stills", action="store_true")
ARGS = _ap.parse_args()
EP = ARGS.ep
with open(f"{ROOT}/production/{EP}/episode.json", encoding="utf-8") as _f:
    CFG = json.load(_f)
OV = CFG["overlay"]
OUT = f"{ROOT}/production/{EP}/overlay"
AUDIO = f"{ROOT}/production/{EP}/audio/{EP}_audio_temp_mix.wav"

W, H, FPS, DUR = 1080, 1920, int(CFG["fps"]), float(CFG["duration"])
GREEN, AMBER, RED = (77, 255, 136), (255, 176, 0), (255, 59, 47)
DIM = (77, 255, 136)

def find_font():
    for c in [os.environ.get("VT323_PATH"), os.path.expanduser("~/.fonts/VT323.ttf"),
              os.path.expanduser("~/.fonts/VT323-Regular.ttf"), "/usr/share/fonts/truetype/VT323.ttf"]:
        if c and os.path.exists(c):
            return c
    sys.exit("VT323 font not found. Download it from Google Fonts and set VT323_PATH=/path/to/VT323.ttf")

FONT = find_font()
F = lambda size: ImageFont.truetype(FONT, size)

_icon_cache = {}
def icon(name, size, color=None):
    key = (name, size, color)
    if key not in _icon_cache:
        im = Image.open(f"{ICONS}/{name}.png").convert("RGBA").resize((size, size), Image.LANCZOS)
        if color:  # recolor, keep alpha
            solid = Image.new("RGBA", im.size, color + (255,))
            solid.putalpha(im.getchannel("A"))
            im = solid
        _icon_cache[key] = im
    return _icon_cache[key]

# ---- timeline (seconds) ---------------------------------------------------
TYPE_S = OV.get("type_s", 0.04)        # seconds per typed character
CAPTIONS = [(c["start"], c["until"], c["text"], c["icon"]) for c in OV["captions"]]
_slug = lambda t: re.sub(r"[^a-z0-9]", "", t.lower())
CAP_FILES = [f"caption_{i + 1}_{_slug(c[2])}.png" for i, c in enumerate(CAPTIONS)]
REC_PERIOD, REC_ON = OV["rec"]["period"], OV["rec"]["on"]

SAFE_L, SAFE_R = 70, 1010          # keep clear of platform UI on the right
TOP_Y = 280                        # below the top overlay zone

def glow(layer, radius=9, strength=.65):
    g = layer.filter(ImageFilter.GaussianBlur(radius))
    a = g.getchannel("A").point(lambda v: int(v * strength))
    g.putalpha(a)
    return Image.alpha_composite(g, layer)

def smooth(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)

def legibility_gradient(bars, a_max=165):
    """soft dark band behind the date row so amber text reads on any shot"""
    bd = ImageDraw.Draw(bars)
    for y in range(1380, 1620):
        a = a_max * smooth((y - 1380) / 70) * (1 - smooth((y - 1560) / 60))
        bd.line([(0, y), (W, y)], fill=(4, 9, 6, int(a)))

def draw_ui(d, canvas, t, with_counter=True, with_rec=True):
    # row 1: play icon + tape id
    canvas.alpha_composite(icon("play", 64, GREEN), (SAFE_L, TOP_Y - 6))
    d.text((SAFE_L + 84, TOP_Y + 54), CFG["tape_id"], font=F(64), fill=GREEN + (235,), anchor="ls")
    # row 2: side
    d.text((SAFE_L, TOP_Y + 124), f"SIDE {CFG['side']}", font=F(46), fill=GREEN + (150,), anchor="ls")
    # counter (top right), one tick per second
    if with_counter:
        d.text((SAFE_R, TOP_Y + 54), f"{int(t):06d}", font=F(64), fill=GREEN + (235,), anchor="rs")
    # REC (second row, right): blinks on/off on the lamp cycle (episode.json: overlay.rec)
    if with_rec and (t % REC_PERIOD) < REC_ON:
        tw = d.textlength("REC", font=F(46))
        d.text((SAFE_R, TOP_Y + 124), "REC", font=F(46), fill=RED + (240,), anchor="rs")
        canvas.alpha_composite(icon("record", 46, RED), (int(SAFE_R - tw - 62), TOP_Y + 124 - 40))
    # date row (bottom-left, always masked)
    canvas.alpha_composite(icon("date-masked", 56, AMBER), (SAFE_L, 1450))
    d.text((SAFE_L + 78, 1494), OV.get("date_text", "DATE --/--/----"), font=F(52), fill=AMBER + (225,), anchor="ls")

def draw_caption(d, canvas, bars, t, idx, final=False):
    start, until, text, ic = CAPTIONS[idx]
    if not final and not (start <= t < until):
        return
    n = len(text) if final else min(len(text), int((t - start) / TYPE_S) + 1)
    fade = 1.0 if final else min(1.0, max(0.0, (until - t) / 0.2))
    a = int(255 * fade)
    ImageDraw.Draw(bars).rectangle([40, 1262, 1040, 1384], fill=(4, 9, 6, int(175 * fade)))   # caption strip
    canvas.alpha_composite(icon(ic, 76, GREEN), (SAFE_L, 1290))
    shown = text[:n]
    done = n == len(text)
    cursor = "_" if (not final and (not done or int(t * 2) % 2 == 0)) else ""
    d.text((SAFE_L + 100, 1352), shown + cursor, font=F(84), fill=GREEN + (a,), anchor="ls")

def render(t, ui=True, captions=True, counter=True, rec=True, only=None, final=False):
    base = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bars = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(base)
    visible = not (t < OV.get("flicker_until", 0.4) and int(t * FPS) % 3 == 0)      # power-on flicker
    if visible:
        if ui:
            legibility_gradient(bars)
            draw_ui(d, base, t, counter, rec)
        if captions:
            for i in range(len(CAPTIONS)):
                if only is None or only == i:
                    draw_caption(d, base, bars, t, i, final=final)
    return Image.alpha_composite(bars, glow(base))

def main():
    os.makedirs(OUT, exist_ok=True)
    # stills
    render(OV.get("ui_static_t", 3.5), captions=False, counter=False, rec=False).save(f"{OUT}/ui_static.png")
    cover_t = OV.get("cover_t", 3.9)
    for old in [n for n in os.listdir(OUT) if n.startswith("ui_cover_t")]:
        os.remove(f"{OUT}/{old}")
    render(cover_t).save(f"{OUT}/ui_cover_t{cover_t:g}.png")
    for i, name in enumerate(CAP_FILES):
        c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        b = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw_caption(ImageDraw.Draw(c), c, b, 0, i, final=True)
        Image.alpha_composite(b, glow(c)).save(f"{OUT}/{name}")
    if ARGS.stills:
        print("stills only"); return
    # frame sequence -> video
    tmp = tempfile.mkdtemp(prefix=f"{EP.lower()}_ovl_")
    try:
        n = int(round(FPS * DUR))
        for k in range(n):
            render(k / FPS).save(f"{tmp}/f_{k:04d}.png")
        webm = f"{OUT}/{EP}_overlay_alpha.webm"            # small; VP9 with alpha
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", f"{tmp}/f_%04d.png",
                        "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "28", "-auto-alt-ref", "0", webm], check=True)
        if ARGS.prores:                         # large (~160 MB); for Premiere / DaVinci / Final Cut
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", f"{tmp}/f_%04d.png",
                            "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le",
                            f"{OUT}/{EP}_overlay_alpha.mov"], check=True)
        prev = f"{OUT}/{EP}_overlay_preview.mp4"
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c=0x0b0d0c:s={W}x{H}:r={FPS}:d={DUR}",
               "-framerate", str(FPS), "-i", f"{tmp}/f_%04d.png"]
        if os.path.exists(AUDIO):
            cmd += ["-i", AUDIO]
        cmd += ["-filter_complex", "[0][1]overlay=shortest=1[v]", "-map", "[v]"]
        if os.path.exists(AUDIO):
            cmd += ["-map", "2:a", "-c:a", "aac", "-b:a", "192k"]
        cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-shortest", prev]
        subprocess.run(cmd, check=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("done:", os.listdir(OUT))

if __name__ == "__main__":
    main()
