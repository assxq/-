#!/usr/bin/env python3
"""E01 sound design v2 (synthesized; use as a reference track and as layers under real foley).

What changed from v1
  * layered hits (plastic tock + body + spring ring), stick-slip friction for slides/scrapes
  * small metal-room reverb on every hit
  * detuned, filter-moving pad with tape wow/flutter and saturation
  * a real "tape stop" (pitch falls while the beds fade) and a 0.1 s dropout glitch at 11.0 s
  * power-on thump (0.0 s), a very soft breath (14.2 s)
  * stereo placement, TPDF dither, loudness normalised to -16 LUFS with a soft ceiling

Outputs (production/E01/audio/)
  E01_audio_temp_mix.wav   final mix, stereo 44.1 kHz 16-bit, ~-16 LUFS
  stem_room.wav            room tone                       \\
  stem_tape.wav            hiss + motor hum + reels         |  the four stems sum to the mix
  stem_pad.wav             soft pad                         |  (before the soft ceiling)
  stem_sfx.wav             all hits (dry + reverb)         /
  sfx_*.wav                single hits (dry, mono)

Tuning: edit MIX below (all values in dB) and re-run.   Needs numpy; ffmpeg (optional, for loudness).
"""
import os, re, subprocess, tempfile, wave
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = f"{ROOT}/production/E01/audio"
SR, DUR = 44100, 20.0
N = int(SR * DUR)
db = lambda x: 10 ** (x / 20)

# ---------------------------------------------------------------------------
# MIX — change these numbers to rebalance (dB, relative; everything is normalised to TARGET_LUFS at the end)
# ---------------------------------------------------------------------------
TARGET_LUFS = -16.0
CEILING_DB = -1.5
MIX = dict(
    room=-38, hiss=-37, hum=-41, reels=-49,          # beds
    pad=-23,                                         # soft pad (12 s -> 19 s)
    poweron=-17, key=-14, relay=-30, type=-31,       # 0.0 s, play/stop keys, REC relay ticks, typed-caption ticks
    scrape=-21, slide=-19, thunk=-13, latch=-24,     # headset, cassette in, door
    hand=-17, breath=-24, spindown=-29, glitch=-30,  # hand on deck, exhale, reels slowing, dropout
    reverb_wet=0.22, reverb_rt60=0.5,
)
BREATH = True    # set False to remove the exhale at 14.2 s

rng = np.random.default_rng(27)

# ---------------------------------------------------------------------------
# small DSP toolbox
# ---------------------------------------------------------------------------
def band_noise(n, lo, hi, r=None):
    r = r or rng
    spec = np.fft.rfft(r.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR); f[0] = 1e-9
    spec *= (1 / (1 + (f / hi) ** 4)) * (1 / (1 + (lo / f) ** 4))
    x = np.fft.irfft(spec, n)
    return x / (np.sqrt(np.mean(x ** 2)) + 1e-12)                      # RMS = 1

def tilt_noise(n, lo, hi, slope, r=None):
    """noise whose power falls as 1/f^slope inside lo..hi (slope=1 is pink)"""
    r = r or rng
    spec = np.fft.rfft(r.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR); f[0] = 1e-9
    spec *= (f / 1000.0) ** (-slope / 2) * (1 / (1 + (f / hi) ** 4)) * (1 / (1 + (lo / f) ** 4))
    x = np.fft.irfft(spec, n)
    return x / (np.sqrt(np.mean(x ** 2)) + 1e-12)

def lowpass(x, fc):
    ax = 0
    spec = np.fft.rfft(x, axis=ax)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    g = 1 / (1 + (f / fc) ** 4)
    if x.ndim == 2: g = g[:, None]
    return np.fft.irfft(spec * g, len(x), axis=ax)

def ex(n, tau):
    return np.exp(-np.arange(n) / SR / tau)

def peak1(x):
    return x / (np.max(np.abs(x)) + 1e-12)

def ramp(pts, n=N):
    t = np.arange(n) / SR
    return np.interp(t, [p[0] for p in pts], [p[1] for p in pts])

def fftconv(x, ir):
    n = len(x) + len(ir) - 1
    nfft = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, nfft) * np.fft.rfft(ir, nfft), nfft)[: len(x)]

def make_ir(rt60, seed):
    r = np.random.default_rng(seed)
    n = int(SR * rt60 * 1.3); t = np.arange(n) / SR
    ir = band_noise(n, 180, 6000, r) * np.exp(-t * 6.9 / rt60) * np.clip(t / .012, 0, 1) * .35
    for ms, g in zip([6.3, 9.1, 13.7, 19.4, 27.2, 36.8], [.7, -.55, .45, -.4, .32, -.25]):
        ir[int(ms / 1000 * SR)] += g
    return ir / np.sqrt(np.sum(ir ** 2))

def pan(x, p):
    a = (p + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)], axis=1)

def stick_slip(n, lo=30, hi=90, depth=.85):
    g = np.maximum(band_noise(n, lo, hi), 0) ** 1.2
    g /= g.max() + 1e-9
    return (1 - depth) + depth * g

# ---------------------------------------------------------------------------
# single hits (each returns a peak-normalised mono array)
# ---------------------------------------------------------------------------
def sfx_key():                      # chunky plastic key: tock + body + tiny spring ring
    n = int(.14 * SR); t = np.arange(n) / SR
    tock = band_noise(n, 1500, 4500) * ex(n, .004)
    body = np.sin(2 * np.pi * (80 + 130 * np.exp(-t * 40)) * t) * ex(n, .022) * .9
    ring = np.sin(2 * np.pi * 3100 * t) * ex(n, .012) * .12
    return peak1(tock + body + ring)

def sfx_relay():                    # REC lamp relay tick
    n = int(.04 * SR); t = np.arange(n) / SR
    x = band_noise(n, 2000, 6500) * ex(n, .0015) + .5 * np.sin(2 * np.pi * 2800 * t) * ex(n, .002)
    i = int(.012 * SR)
    x[i:] += .35 * (band_noise(n - i, 1500, 5000) * ex(n - i, .002))
    return peak1(x)

def sfx_type(k):                    # typed-caption tick, three slightly different variants
    n = int(.03 * SR); t = np.arange(n) / SR
    f = [900, 1150, 1400][k % 3]
    x = band_noise(n, 2500, 6500) * ex(n, .0012) * (.65 + .1 * (k % 3)) + .3 * np.sin(2 * np.pi * f * t) * ex(n, .003)
    return peak1(x)

def sfx_slide():                    # cassette sliding into the deck, with a seat bump at the end
    n = int(.78 * SR); t = np.arange(n) / SR; L = .78
    a = band_noise(n, 500, 1200) * (1 - t / L); b = band_noise(n, 1100, 2600) * (t / L)
    x = (a + b) * np.sin(np.pi * np.clip(t / L, 0, 1)) ** 1.2 * stick_slip(n, 30, 90)
    m = t >= .68
    x[m] += 1.4 * np.sin(2 * np.pi * 100 * (t[m] - .68)) * np.exp(-(t[m] - .68) / .03)
    return peak1(x)

def sfx_scrape():                   # headset plastic adjusting
    n = int(.42 * SR); t = np.arange(n) / SR
    x = band_noise(n, 1000, 4500) * np.sin(np.pi * np.clip(t / .42, 0, 1)) * stick_slip(n, 40, 120, .9)
    x += .25 * band_noise(n, 200, 700) * np.sin(np.pi * np.clip(t / .42, 0, 1))
    return peak1(x)

def sfx_thunk():                    # smoked door closing: thud + clack + latch + rattle
    n = int(.5 * SR); t = np.arange(n) / SR
    thud = np.sin(2 * np.pi * (55 + 40 * np.exp(-t * 18)) * t) * ex(n, .11)
    clack = np.zeros(n); i = int(.004 * SR)
    clack[i:] = band_noise(n - i, 900, 3000) * ex(n - i, .006) * .8
    latch = np.zeros(n); j = int(.09 * SR)
    latch[j:] = band_noise(n - j, 2000, 5200) * ex(n - j, .003) * .45
    rattle = np.zeros(n)
    for k, dly in enumerate([.13, .16, .19]):
        q = int(dly * SR); rattle[q:] += band_noise(n - q, 700, 2400) * ex(n - q, .005) * (.22 / (k + 1))
    return peak1(thud + clack + latch + rattle)

def sfx_hand():                     # a hand settling on plastic
    n = int(.35 * SR); t = np.arange(n) / SR
    x = np.sin(2 * np.pi * (50 + 35 * np.exp(-t * 14)) * t) * ex(n, .07)
    x += .55 * band_noise(n, 120, 700) * ex(n, .04) + .18 * band_noise(n, 1000, 3000) * ex(n, .05)
    return peak1(x)

def sfx_poweron():                  # CRT degauss-ish thump + short warm-up whine
    n = int(.6 * SR); t = np.arange(n) / SR
    thump = np.sin(2 * np.pi * 60 * t) * ex(n, .12) * (1 + .5 * np.sin(2 * np.pi * 14 * t))
    zap = band_noise(n, 300, 2500) * ex(n, .02) * .8
    whine = np.sin(2 * np.pi * np.cumsum(2400 * np.exp(-t * 6) + 700) / SR) * ex(n, .18) * .12
    return peak1(thump + zap + whine)

def sfx_spindown():                 # reels slowing (the pitch drop of the beds is done by the tape-stop below)
    n = int(.9 * SR); t = np.arange(n) / SR
    f = 150 * np.exp(-t * 3.4) + 26
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = (np.sin(ph) + .3 * np.sin(2 * ph)) * ex(n, .32) + .22 * band_noise(n, 300, 1100) * ex(n, .28)
    return peak1(x)

def sfx_breath():                   # a very soft exhale (not speech)
    n = int(1.1 * SR); t = np.arange(n) / SR
    env = np.minimum(t / .22, 1) ** 1.5 * np.exp(-np.maximum(t - .22, 0) / .35)
    x = band_noise(n, 350, 2600) * env + .35 * band_noise(n, 1500, 3800) * env
    return peak1(lowpass(x, 3600))

def sfx_glitch():                   # tiny dropout burst
    n = int(.12 * SR); t = np.arange(n) / SR
    x = band_noise(n, 3500, 9000) * np.sin(np.pi * t / .12) ** 2 * stick_slip(n, 80, 250, .9)
    return peak1(x)

HITS = {"key": sfx_key(), "relay": sfx_relay(), "type": sfx_type(0), "slide": sfx_slide(), "scrape": sfx_scrape(),
        "thunk": sfx_thunk(), "hand": sfx_hand(), "poweron": sfx_poweron(), "spindown": sfx_spindown(),
        "breath": sfx_breath(), "glitch": sfx_glitch()}

# ---------------------------------------------------------------------------
# beds
# ---------------------------------------------------------------------------
def bed_room():
    out = np.zeros((N, 2)); t = np.arange(N) / SR
    drift = 1 + .15 * np.sin(2 * np.pi * .07 * t + 1.3)                    # slow ventilation breathing
    for ch in range(2):
        r = np.random.default_rng(100 + ch)
        out[:, ch] = band_noise(N, 40, 700, r) * drift * db(MIX["room"])
    return out

def bed_tape():
    """hiss + motor hum + reels, before the tape transport (wow/flutter, dropout, stop)"""
    out = np.zeros((N, 2)); t = np.arange(N) / SR
    breath = 1 + .16 * np.sin(2 * np.pi * .21 * t) + .08 * np.sin(2 * np.pi * .53 * t + 2)
    hiss_env = ramp([(0, 0), (.3, .25), (2, .25), (4, 1), (18.3, 1), (20, 1)]) * breath
    hum_env = ramp([(0, 0), (.3, 1), (20, 1)]) * (1 + .12 * np.sin(2 * np.pi * .9 * t))
    dip = ramp([(0, 1), (15.9, 1), (16.1, db(-3)), (17.0, db(-3)), (17.3, 1), (20, 1)])
    f0 = 58 + 0.5 * np.sin(2 * np.pi * .3 * t)
    ph = 2 * np.pi * np.cumsum(f0) / SR
    motor = sum(a * np.sin(k * ph + k) for k, a in [(1, 1), (2, .45), (3, .22), (4, .12), (5, .06)])
    brush = band_noise(N, 1200, 3800, np.random.default_rng(7)) * (.5 + .5 * np.sin(ph)) ** 2   # commutator brush texture
    reel_am = .55 + .45 * np.sin(2 * np.pi * 5.5 * t)
    reel_env = ramp([(10.7, 0), (11.0, 1), (20, 1)])
    for ch in range(2):
        r = np.random.default_rng(200 + ch)
        hiss = tilt_noise(N, 1800, 11000, .6, r) * db(MIX["hiss"]) * hiss_env
        hum = (motor + .08 * brush) * db(MIX["hum"]) * hum_env * dip
        reels = band_noise(N, 250, 900, r) * reel_am * db(MIX["reels"]) * reel_env
        out[:, ch] = hiss + hum + reels
    return out

def bed_pad():
    """A2 E3 A3 C4 (same chord as the web page), detuned saws whose brightness opens slowly"""
    out = np.zeros((N, 2)); t = np.arange(N) / SR
    env = ramp([(0, 0), (12.0, 0), (15.0, 1), (16.8, 1), (19.0, 0), (20, 0)]) ** 1.2
    bright = ramp([(12, .15), (16, .75), (19, .3)])
    vib = 1 + (3 / 1200 * np.log(2)) * np.sin(2 * np.pi * 4.6 * t) * ramp([(12, 0), (14, 1), (20, 1)])
    for k, f in enumerate([110.0, 164.81, 220.0, 261.63]):
        for ch, sgn in enumerate((-1, 1)):
            for det in (-7, 7):
                fc = f * 2 ** ((det + 2 * sgn) / 1200)
                ph = 2 * np.pi * np.cumsum(fc * vib) / SR
                voice = np.zeros(N)
                for h in range(1, 13):
                    voice += np.sin(h * ph + .6 * h) * (1 / h ** 1.4) * np.exp(-h * (1 - bright) * 1.1)
                out[:, ch] += voice / (4 * 2 * 1.6)
    out += .06 * np.stack([np.sin(2 * np.pi * 440 * t + .3), np.sin(2 * np.pi * 440.4 * t)], axis=1) * (env ** 2)[:, None]
    out = np.tanh(out * 1.6) / 1.6                                           # gentle tape saturation
    out = lowpass(out, 5500)
    return out * env[:, None] * db(MIX["pad"])

# ---------------------------------------------------------------------------
# tape transport: slow wow + fast flutter, a 0.1 s dropout at 11.0 s and the tape stop at 18.3 s
# ---------------------------------------------------------------------------
def transport(x):
    t = np.arange(N) / SR
    drift = lowpass(np.random.default_rng(31).standard_normal(N), 3.0); drift /= np.max(np.abs(drift))
    wow = 1 + .0030 * np.sin(2 * np.pi * .55 * t + .7) + .0010 * np.sin(2 * np.pi * 6.8 * t + 2.1) + .0006 * drift
    stop = np.where(t < 18.3, 1.0, np.clip(1 - (t - 18.3) / .8, 0, 1) ** 1.6)
    b = np.exp(-((t - 11.03) / .045) ** 2)
    speed = wow * stop * (1 - .08 * b)
    gain = stop ** .6 * (1 - .85 * b)
    pos = np.clip(np.cumsum(speed), 0, N - 1)
    idx = np.arange(N)
    y = np.stack([np.interp(pos, idx, x[:, c]) for c in range(2)], axis=1) if x.ndim == 2 else np.interp(pos, idx, x)
    return y * (gain[:, None] if y.ndim == 2 else gain)

# ---------------------------------------------------------------------------
# events (time, hit, level key, pan, reverb send)
# ---------------------------------------------------------------------------
def events():
    ev = [(0.00, "poweron", "poweron", 0, .10), (0.02, "key", "key", 0, .15)]
    ev += [(float(t), "relay", "relay", 0.0, .04) for t in np.arange(0.0, 17.7, 1.6)]            # REC lamp blinks
    for start, text in [(0.6, "STATION 7"), (4.5, "OPERATOR 027"), (12.5, "SIGNAL OK."), (18.3, "End of tape.")]:
        for i, ch in enumerate(text):
            if ch != " ":
                ev.append((start + i * 0.04, "type", "type", 0.0, .05))
    ev += [(6.50, "scrape", "scrape", -.35, .22),   # headset sits on the left of the frame
           (9.20, "slide", "slide", -.05, .22),
           (10.60, "thunk", "thunk", 0, .25), (10.64, "key", "latch", 0, .20),
           (11.00, "glitch", "glitch", 0, .10),
           (16.00, "hand", "hand", .1, .25),
           (18.30, "key", "key", 0, .15), (18.30, "spindown", "spindown", 0, .20)]
    if BREATH:
        ev.append((14.20, "breath", "breath", .05, .30))
    return ev

def place_sfx():
    dry = np.zeros((N, 2)); send = np.zeros(N)
    rr = np.random.default_rng(5)
    for (t0, name, lvl, p, wet) in events():
        sig = HITS[name]
        if name == "type":                                     # pick one of three variants, slight level variation
            sig = sfx_type(int(rr.integers(0, 3))) * (.7 + .3 * rr.random())
        g = db(MIX[lvl]); i = int(t0 * SR); j = min(N, i + len(sig))
        stereo = pan(sig, p) * g
        dry[i:j] += stereo[: j - i]
        send[i:j] += sig[: j - i] * g * wet
    ir_l, ir_r = make_ir(MIX["reverb_rt60"], 11), make_ir(MIX["reverb_rt60"], 12)
    wetm = np.stack([fftconv(send, ir_l), fftconv(send, ir_r)], axis=1) * (MIX["reverb_wet"] / .22)
    return dry + wetm

# ---------------------------------------------------------------------------
# output helpers
# ---------------------------------------------------------------------------
def to_pcm16(x, dither=True):
    x = np.clip(x, -1, 1) * 32767
    if dither:
        r = np.random.default_rng(9)
        x = x + (r.random(x.shape) - r.random(x.shape))
    return np.round(x).astype("<i2")

def write_wav(path, x, dither=True):
    pcm = to_pcm16(x, dither)
    with wave.open(path, "wb") as w:
        w.setnchannels(1 if x.ndim == 1 else x.shape[1]); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())

def measure(path):
    try:
        p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"],
                           capture_output=True, text=True)
        lufs = float(re.findall(r"I:\s+(-?\d+\.\d+)\s+LUFS", p.stderr)[-1])
        tp = float(re.findall(r"Peak:\s+(-?\d+\.\d+)\s+dBFS", p.stderr)[-1])
        return lufs, tp
    except Exception:
        return None, None

def soft_limit(x, ceil_lin):
    th = .6 * ceil_lin; a = np.abs(x); y = x.copy(); o = a > th
    y[o] = np.sign(x[o]) * (th + (ceil_lin - th) * np.tanh((a[o] - th) / (ceil_lin - th)))
    return y

def main():
    os.makedirs(OUT, exist_ok=True)
    for old in ("bed_room_hiss_hum.wav", "bed_pad.wav", "sfx_bip.wav", "sfx_tick.wav", "sfx_click.wav"):
        p = f"{OUT}/{old}"
        if os.path.exists(p): os.remove(p)

    room = bed_room()
    tape = transport(bed_tape())
    pad = transport(bed_pad())
    sfx = place_sfx()
    raw = room + tape + pad + sfx

    # loudness: measure a temp copy, then scale to the target
    gain = 1.0
    with tempfile.TemporaryDirectory() as td:
        tmp = f"{td}/m.wav"; write_wav(tmp, raw / max(1e-9, np.max(np.abs(raw))) * .5, dither=False)
        lufs, _ = measure(tmp)
    if lufs is not None:
        lufs_raw = lufs - 20 * np.log10(.5 / max(1e-9, np.max(np.abs(raw))))
        gain = db(TARGET_LUFS - lufs_raw)
    else:
        gain = db(TARGET_LUFS + 24) / max(1e-9, np.sqrt(np.mean(raw ** 2)))
    ceil = db(CEILING_DB)
    final = soft_limit(raw * gain, ceil)

    write_wav(f"{OUT}/E01_audio_temp_mix.wav", final)
    for name, stem in (("room", room), ("tape", tape), ("pad", pad), ("sfx", sfx)):
        write_wav(f"{OUT}/stem_{name}.wav", np.clip(stem * gain, -1, 1))
    peaks = {"key": -3, "relay": -6, "type": -6, "slide": -6, "scrape": -6, "thunk": -3, "hand": -3, "poweron": -3,
             "spindown": -3, "breath": -6, "glitch": -6}
    for k, v in HITS.items():
        write_wav(f"{OUT}/sfx_{k}.wav", v * db(peaks[k]))

    l2, tp = measure(f"{OUT}/E01_audio_temp_mix.wav")
    print(f"mix: {l2} LUFS integrated, sample peak {20 * np.log10(np.max(np.abs(final))):.1f} dBFS, ebur128 peak {tp} dBFS")
    print("files:", sorted(os.listdir(OUT)))

if __name__ == "__main__":
    main()
