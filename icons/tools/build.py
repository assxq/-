#!/usr/bin/env python3
"""Station 7 icon set generator.

Outputs (relative to icons/):
  svg/<id>.svg          monochrome (currentColor)
  svg-color/<id>.svg    function color baked in
  sprite.svg            <symbol> sprite (currentColor)
  index.html            specimen sheet (sprite inlined)

Grid: 48x48, stroke 3, miter joins, butt caps, no rounded corners.
Frame shape = category:  circle = CONTROL, square = STATUS, triangle = WARNING / ABSENCE
Filled = present.  Hollow = absent / empty.
Color = function:        green = normal, amber = caution, red = alert / recording
"""
import os, html

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GREEN, AMBER, RED = "#4dff88", "#ffb000", "#ff3b2f"
F = 'fill="currentColor" stroke="none"'

FRAMES = {
    "circle":   '<circle cx="24" cy="24" r="21" fill="none" stroke="currentColor" stroke-width="3"/>',
    "square":   '<rect x="3" y="3" width="42" height="42" fill="none" stroke="currentColor" stroke-width="3"/>',
    "triangle": '<path d="M24 5 L44 41 H4 Z" fill="none" stroke="currentColor" stroke-width="3" stroke-linejoin="miter"/>',
}
CAT = {"circle": "CONTROL", "square": "STATUS", "triangle": "WARNING"}
CAT_KO = {"circle": "조작", "square": "상태", "triangle": "경고·부재"}
# id, frame, color, log label, Korean meaning, glyph
ICONS = [
    # ---- CONTROL (circle) ----
    ("play", "circle", GREEN, "PLAY", "재생", f'<path d="M19 15 L34 24 L19 33 Z" {F}/>'),
    ("stop", "circle", GREEN, "STOP", "정지", f'<rect x="16" y="16" width="16" height="16" {F}/>'),
    ("rewind", "circle", GREEN, "REW", "되감기", f'<path d="M24 16 V32 L14 24 Z M34 16 V32 L24 24 Z" {F}/>'),
    ("fast-forward", "circle", GREEN, "FF", "빨리 감기", f'<path d="M14 16 V32 L24 24 Z M24 16 V32 L34 24 Z" {F}/>'),
    ("eject", "circle", GREEN, "EJECT", "꺼내기", f'<path d="M24 14 L35 26 H13 Z" {F}/><rect x="13" y="29" width="22" height="5" {F}/>'),
    ("record", "circle", RED, "REC", "기록 중", f'<circle cx="24" cy="24" r="8" {F}/>'),
    ("transmit", "circle", GREEN, "TX", "송신",
     f'<path d="M24 26 V36" fill="none" stroke="currentColor" stroke-width="3"/><circle cx="24" cy="22" r="2.8" {F}/>'
     '<path d="M28.24 17.76 A6 6 0 0 1 28.24 26.24 M19.76 17.76 A6 6 0 0 0 19.76 26.24 '
     'M31.78 14.22 A11 11 0 0 1 31.78 29.78 M16.22 14.22 A11 11 0 0 0 16.22 29.78" fill="none" stroke="currentColor" stroke-width="3"/>'),
    ("receive", "circle", GREEN, "RX", "수신",
     '<path d="M24 26 V36 M13 17 L19 22 L13 27 M35 17 L29 22 L35 27" fill="none" stroke="currentColor" stroke-width="3"/>'
     f'<circle cx="24" cy="22" r="2.8" {F}/>'),
    ("battery", "square", GREEN, "BATTERY", "배터리",
     '<rect x="11" y="17" width="22" height="14" fill="none" stroke="currentColor" stroke-width="3"/>'
     f'<rect x="34" y="21" width="3" height="6" {F}/><rect x="15" y="20.5" width="4" height="7" {F}/>'
     f'<rect x="21" y="20.5" width="4" height="7" {F}/><rect x="27" y="20.5" width="3" height="7" {F}/>'),
    ("signal", "square", GREEN, "SIGNAL", "신호 세기",
     f'<rect x="12" y="30" width="5" height="5" {F}/><rect x="19" y="25" width="5" height="10" {F}/>'
     f'<rect x="26" y="20" width="5" height="15" {F}/><rect x="33" y="15" width="5" height="20" {F}/>'),
    ("tape", "square", GREEN, "TAPE", "테이프",
     '<rect x="10" y="16" width="28" height="18" fill="none" stroke="currentColor" stroke-width="3"/>'
     '<circle cx="18" cy="25" r="3.2" fill="none" stroke="currentColor" stroke-width="3"/>'
     '<circle cx="30" cy="25" r="3.2" fill="none" stroke="currentColor" stroke-width="3"/>'),
    ("archive", "square", GREEN, "ARCHIVE", "보관고",
     f'<rect x="11" y="14" width="5" height="17" {F}/><rect x="18.5" y="14" width="5" height="17" {F}/>'
     f'<rect x="26" y="14" width="5" height="17" {F}/>'
     '<rect x="34" y="15" width="4.5" height="16" fill="none" stroke="currentColor" stroke-width="2"/>'
     '<path d="M9 34.5 H40" fill="none" stroke="currentColor" stroke-width="3"/>'),
    ("door-locked", "square", AMBER, "DOOR · LOCKED", "잠긴 문",
     '<rect x="14" y="10" width="20" height="28" fill="none" stroke="currentColor" stroke-width="3"/>'
     f'<circle cx="29" cy="24" r="2" {F}/><rect x="9" y="20.5" width="30" height="5" {F}/>'),
    ("operator", "square", GREEN, "OPERATOR", "담당관",
     f'<circle cx="24" cy="18" r="5" {F}/><path d="M13 36 V32 A11 7 0 0 1 35 32 V36 Z" {F}/>'),
    ("station", "square", GREEN, "STATION", "관측소",
     '<path d="M24 18 L15 39 M24 18 L33 39 M18.9 30 H29.1 M16.7 35 H31.3" fill="none" stroke="currentColor" stroke-width="3"/>'
     f'<circle cx="24" cy="15" r="2.5" {F}/>'
     '<path d="M28.95 10.05 A7 7 0 0 1 28.95 19.95 M19.05 10.05 A7 7 0 0 0 19.05 19.95" fill="none" stroke="currentColor" stroke-width="3"/>'),
    ("date-masked", "square", AMBER, "DATE · MASKED", "가려진 날짜",
     '<rect x="11" y="14" width="26" height="23" fill="none" stroke="currentColor" stroke-width="3"/>'
     f'<rect x="11" y="14" width="26" height="7" {F}/>'
     '<path d="M17 10.5 V17 M31 10.5 V17 M16 29 H22 M26 29 H32" fill="none" stroke="currentColor" stroke-width="3"/>'),
    ("city", "square", GREEN, "CITY", "도시",
     f'<rect x="11" y="23" width="7" height="13" {F}/><rect x="20" y="14" width="9" height="22" {F}/>'
     f'<rect x="31" y="26" width="7" height="10" {F}/>'
     '<path d="M9 37.5 H40" fill="none" stroke="currentColor" stroke-width="3"/>'),
    ("time-playing", "square", GREEN, "TIME · PLAYING", "재생 중인 시간",
     '<circle cx="24" cy="24" r="12" fill="none" stroke="currentColor" stroke-width="3"/>'
     f'<path d="M21 18.5 L31 24 L21 29.5 Z" {F}/>'),
    # ---- WARNING / ABSENCE (triangle) ----
    ("low-battery", "triangle", AMBER, "LOW BATTERY", "배터리 부족",
     '<rect x="16" y="26" width="13" height="8" fill="none" stroke="currentColor" stroke-width="3"/>'
     f'<rect x="29" y="28" width="3" height="4" {F}/><rect x="19" y="28.5" width="3" height="3" {F}/>'),
    ("no-signal", "triangle", AMBER, "NO SIGNAL", "신호 없음",
     '<rect x="15" y="31" width="4.5" height="4" fill="none" stroke="currentColor" stroke-width="2"/>'
     '<rect x="21.5" y="27.5" width="4.5" height="7.5" fill="none" stroke="currentColor" stroke-width="2"/>'
     '<rect x="28" y="24" width="4.5" height="11" fill="none" stroke="currentColor" stroke-width="2"/>'),
    ("no-contact", "triangle", RED, "NO CONTACT", "연락 두절",
     '<circle cx="24" cy="23" r="3.6" fill="none" stroke="currentColor" stroke-width="2"/>'
     '<path d="M16.5 37 V34 A7.5 5.5 0 0 1 31.5 34 V37 Z" fill="none" stroke="currentColor" stroke-width="2"/>'),
    ("no-reply", "triangle", AMBER, "NO REPLY", "회신 없음",
     '<path d="M30 25 V31 H22" fill="none" stroke="currentColor" stroke-width="2.5"/>'
     '<path d="M17.5 31 L23 26.5 V35.5 Z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="miter"/>'),
    ("end-of-tape", "triangle", AMBER, "END OF TAPE", "테이프 끝",
     f'<path d="M16 26 L26 31.5 L16 37 Z" {F}/><rect x="28.5" y="26" width="3.5" height="11" {F}/>'),
]


def body(frame, glyph):
    return FRAMES[frame] + glyph


def svg(frame, glyph, color=None):
    c = f' style="color:{color}"' if color else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="48" height="48"'
            f' stroke-linejoin="miter" stroke-linecap="butt"{c}>{body(frame, glyph)}</svg>\n')


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    sprite = ['<svg xmlns="http://www.w3.org/2000/svg" style="display:none" stroke-linejoin="miter" stroke-linecap="butt">']
    for (iid, frame, color, label, ko, glyph) in ICONS:
        write(f"{ROOT}/svg/{iid}.svg", svg(frame, glyph))
        # baked color: replace currentColor so the file works anywhere
        baked = svg(frame, glyph).replace("currentColor", color)
        write(f"{ROOT}/svg-color/{iid}.svg", baked)
        sprite.append(f'<symbol id="s7-{iid}" viewBox="0 0 48 48">{body(frame, glyph)}</symbol>')
    sprite.append("</svg>\n")
    write(f"{ROOT}/sprite.svg", "\n".join(sprite))

    # specimen sheet
    cards = []
    for (iid, frame, color, label, ko, glyph) in ICONS:
        cls = {GREEN: "g", AMBER: "a", RED: "r"}[color]
        cards.append(
            f'<figure class="card {cls}"><svg class="ic" viewBox="0 0 48 48" aria-hidden="true"><use href="#s7-{iid}"/></svg>'
            f'<figcaption><b>{html.escape(label)}</b><span>{html.escape(ko)}</span><code>{iid}</code></figcaption></figure>')
    inline_sprite = "\n".join(sprite).replace('style="display:none"', 'width="0" height="0" style="position:absolute"')
    page = SPECIMEN.replace("%%SPRITE%%", inline_sprite).replace("%%CARDS%%", "\n".join(cards)).replace("%%COUNT%%", str(len(ICONS)))
    write(f"{ROOT}/index.html", page)
    print(f"built {len(ICONS)} icons")


SPECIMEN = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>STATION 7 · ICON SET</title>
<style>
:root{--bg:#0b0d0c;--panel:#14160f;--line:#2b2d25;--fg:#d6c9aa;--dim:#8f8160;--g:#4dff88;--a:#ffb000;--r:#ff3b2f;color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.5 ui-monospace,Menlo,Consolas,monospace}
main{max-width:1080px;margin:0 auto;padding:32px 16px 64px}
h1{font:700 22px/1.2 ui-monospace,monospace;letter-spacing:.2em;margin:0 0 4px}
.sub{color:var(--dim);margin:0 0 28px;letter-spacing:.08em}
h2{font:700 12px/1 ui-monospace,monospace;letter-spacing:.28em;color:var(--dim);margin:36px 0 14px;border-top:1px solid var(--line);padding-top:18px}
.rules{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px}
.rule{background:var(--panel);border:1px solid var(--line);padding:14px 16px}
.rule svg{width:30px;height:30px;vertical-align:middle;margin-right:8px}
.rule b{letter-spacing:.14em}
.rule p{margin:8px 0 0;color:var(--dim)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px}
.card{margin:0;background:var(--panel);border:1px solid var(--line);padding:16px 12px 12px;text-align:center}
.card.g{color:var(--g)}.card.a{color:var(--a)}.card.r{color:var(--r)}
.ic{width:84px;height:84px;display:block;margin:0 auto 12px;stroke-linejoin:miter;stroke-linecap:butt}
figcaption{display:flex;flex-direction:column;gap:2px}
figcaption b{font-size:12px;letter-spacing:.12em;color:inherit}
figcaption span{font-size:12px;color:var(--fg)}
figcaption code{font-size:10px;color:var(--dim)}
.sizes{display:flex;flex-wrap:wrap;align-items:flex-end;gap:20px;color:var(--g)}
.sizes svg{display:block}
.light{background:#d6c9aa;color:#2a241a;padding:18px;display:flex;flex-wrap:wrap;gap:16px}
.light svg{width:48px;height:48px}
pre{background:var(--panel);border:1px solid var(--line);padding:14px;overflow:auto;color:var(--fg);margin:0}
</style></head><body>
%%SPRITE%%
<main>
<h1>STATION 7 · ICON SET</h1>
<p class="sub">%%COUNT%% symbols · 48-unit grid · stroke 3 · no rounded corners</p>

<h2>RULES</h2>
<div class="rules">
<div class="rule"><svg viewBox="0 0 48 48" style="color:var(--g)"><use href="#s7-play"/></svg><b>CIRCLE</b><p>Control. Something the operator does.</p></div>
<div class="rule"><svg viewBox="0 0 48 48" style="color:var(--g)"><use href="#s7-battery"/></svg><b>SQUARE</b><p>Status. Something the station is.</p></div>
<div class="rule"><svg viewBox="0 0 48 48" style="color:var(--a)"><use href="#s7-no-signal"/></svg><b>TRIANGLE</b><p>Warning or absence. Hollow means nothing is there.</p></div>
<div class="rule"><svg viewBox="0 0 48 48" style="color:var(--g)"><use href="#s7-signal"/></svg><b style="color:var(--g)">GREEN</b><p>Normal. <b style="color:var(--a)">AMBER</b> caution. <b style="color:var(--r)">RED</b> alert or recording.</p></div>
</div>

<h2>ALL SYMBOLS</h2>
<div class="grid">
%%CARDS%%
</div>

<h2>SIZES</h2>
<div class="sizes">
<svg viewBox="0 0 48 48" width="96" height="96"><use href="#s7-no-contact"/></svg>
<svg viewBox="0 0 48 48" width="48" height="48"><use href="#s7-no-contact"/></svg>
<svg viewBox="0 0 48 48" width="32" height="32"><use href="#s7-no-contact"/></svg>
<svg viewBox="0 0 48 48" width="24" height="24"><use href="#s7-no-contact"/></svg>
<svg viewBox="0 0 48 48" width="16" height="16"><use href="#s7-no-contact"/></svg>
</div>

<h2>MONOCHROME ON LIGHT</h2>
<div class="light">
<svg viewBox="0 0 48 48"><use href="#s7-record"/></svg><svg viewBox="0 0 48 48"><use href="#s7-tape"/></svg>
<svg viewBox="0 0 48 48"><use href="#s7-archive"/></svg><svg viewBox="0 0 48 48"><use href="#s7-door-locked"/></svg>
<svg viewBox="0 0 48 48"><use href="#s7-no-reply"/></svg><svg viewBox="0 0 48 48"><use href="#s7-end-of-tape"/></svg>
</div>

<h2>USAGE</h2>
<pre>&lt;!-- sprite --&gt;
&lt;svg viewBox="0 0 48 48" style="color:#4dff88"&gt;&lt;use href="sprite.svg#s7-battery"/&gt;&lt;/svg&gt;

&lt;!-- single file, monochrome (inherits color) --&gt;
icons/svg/battery.svg

&lt;!-- single file, function color baked in --&gt;
icons/svg-color/battery.svg

&lt;!-- video editing: transparent PNG, 512px --&gt;
icons/png/battery.png</pre>
</main></body></html>
"""

if __name__ == "__main__":
    main()
