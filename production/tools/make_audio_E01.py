#!/usr/bin/env python3
"""E01 temporary sound design (synthesized placeholder).

All sounds are generated from noise and sine waves, in the same spirit as the web page's synth.
They are meant as a TEMP / reference track and as layers to mix with real foley.

Outputs (production/E01/audio/):
  E01_audio_temp_mix.wav     full 20 s mix, stereo 44.1 kHz, synced to the shot list
  bed_room_hiss_hum.wav      room tone + tape hiss + motor hum + reels (20 s, stereo)
  bed_pad.wav                soft pad (A2 E3 A3 C4), 20 s, stereo
  sfx_*.wav                  single hits (mono)

Usage: python3 production/tools/make_audio_E01.py     (needs numpy only)
"""
import os, wave
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = f"{ROOT}/production/E01/audio"
SR, DUR = 44100, 20.0
N = int(SR * DUR)
rng = np.random.default_rng(27)

db = lambda x: 10 ** (x / 20)

def band_noise(n, lo, hi, seed_rng=None):
    r = seed_rng or rng
    spec = np.fft.rfft(r.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR); f[0] = 1e-9
    mask = (1 / (1 + (f / hi) ** 4)) * (1 / (1 + (lo / f) ** 4))
    x = np.fft.irfft(spec * mask, n)
    return x / (np.sqrt(np.mean(x ** 2)) + 1e-12)          # RMS = 1

def env_exp(n, tau):
    return np.exp(-np.arange(n) / SR / tau)

def at(buf, sig, t0, gain_db):
    i = int(t0 * SR)
    if i >= len(buf): return
    s = sig * db(gain_db)
    j = min(len(buf), i + len(s))
    if buf.ndim == 2:
        buf[i:j, :] += s[: j - i, None]
    else:
        buf[i:j] += s[: j - i]

def ramp(n_total, pts):
    """piecewise-linear envelope from [(t, v), ...] in seconds"""
    t = np.arange(n_total) / SR
    return np.interp(t, [p[0] for p in pts], [p[1] for p in pts])

# ---------------- single hits (peak-normalised to 1.0, level set when placed) ----
def sfx_click():
    n = int(.08 * SR)
    x = band_noise(n, 1200, 3500) * env_exp(n, .008)
    tt = np.arange(n) / SR
    x += .8 * np.sin(2 * np.pi * 150 * tt * np.exp(-tt * 20)) * env_exp(n, .02)
    return x / np.max(np.abs(x))

def sfx_thunk():
    n = int(.35 * SR); tt = np.arange(n) / SR
    x = band_noise(n, 50, 420) * env_exp(n, .05)
    x += 1.2 * np.sin(2 * np.pi * (70 - 20 * tt / .35) * tt) * env_exp(n, .09)
    return x / np.max(np.abs(x))

def sfx_slide():
    n = int(.55 * SR); tt = np.arange(n) / SR
    env = np.sin(np.pi * np.clip(tt / .55, 0, 1)) ** 1.5
    x = band_noise(n, 600, 1500) * env * (.7 + .3 * band_noise(n, 5, 30))
    return x / np.max(np.abs(x))

def sfx_scrape():
    n = int(.4 * SR); tt = np.arange(n) / SR
    env = np.sin(np.pi * np.clip(tt / .4, 0, 1)) * np.clip(.6 + .4 * band_noise(n, 4, 40), 0, None)
    x = band_noise(n, 900, 4200) * env
    return x / np.max(np.abs(x))

def sfx_tick():
    n = int(.03 * SR); tt = np.arange(n) / SR
    x = np.sin(2 * np.pi * 1100 * tt) * env_exp(n, .004) + .5 * band_noise(n, 2000, 6000) * env_exp(n, .003)
    return x / np.max(np.abs(x))

def sfx_bip(f=720):
    n = int(.03 * SR); tt = np.arange(n) / SR
    x = np.sin(2 * np.pi * f * tt) * np.sin(np.pi * tt / .03)
    return x / np.max(np.abs(x))

def sfx_spindown():
    n = int(.9 * SR); tt = np.arange(n) / SR
    f = 190 * np.exp(-tt * 3.2) + 28
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = (np.sin(ph) + .35 * np.sin(2 * ph)) * env_exp(n, .35)
    x += .25 * band_noise(n, 300, 1100) * env_exp(n, .3)
    return x / np.max(np.abs(x))

def sfx_hand():
    n = int(.3 * SR); tt = np.arange(n) / SR
    x = np.sin(2 * np.pi * 92 * tt * np.exp(-tt * 6)) * env_exp(n, .08)
    x += .5 * band_noise(n, 200, 900) * env_exp(n, .02)
    return x / np.max(np.abs(x))

HITS = {"click": sfx_click(), "thunk": sfx_thunk(), "slide": sfx_slide(), "scrape": sfx_scrape(),
        "tick": sfx_tick(), "bip": sfx_bip(), "spindown": sfx_spindown(), "hand": sfx_hand()}

# ---------------- beds -------------------------------------------------------
def bed_room_hiss_hum():
    out = np.zeros((N, 2))
    t = np.arange(N) / SR
    for ch in range(2):
        r = np.random.default_rng(100 + ch)
        room = band_noise(N, 40, 700, r) * db(-38)
        hiss = band_noise(N, 2400, 9000, r) * db(-37) * ramp(N, [(0, 0), (.3, .25), (2, .25), (4, 1), (18.3, 1), (18.65, 0), (20, 0)])
        # motor hum with slow wow, dipping a little when the hand lands (16.0-17.0)
        ph = 2 * np.pi * np.cumsum(58 + 1.2 * np.sin(2 * np.pi * .6 * t)) / SR
        dip = ramp(N, [(0, 1), (15.9, 1), (16.1, db(-3)), (17.0, db(-3)), (17.3, 1), (20, 1)])
        hum_env = ramp(N, [(0, 0), (.3, 1), (18.3, 1), (18.35, 0), (20, 0)]) * dip
        hum = (np.sin(ph) + .4 * np.sin(2 * ph) + .15 * np.sin(3 * ph)) * db(-40) * hum_env
        # reels start turning when the cassette is in (10.8 s)
        reel_am = .55 + .45 * np.sin(2 * np.pi * 5.5 * t)
        reels = band_noise(N, 250, 900, r) * reel_am * db(-46) * ramp(N, [(10.7, 0), (11.0, 1), (18.3, 1), (18.6, 0)])
        out[:, ch] = room + hiss + hum + reels
    return out

def bed_pad():
    out = np.zeros((N, 2))
    t = np.arange(N) / SR
    env = ramp(N, [(0, 0), (12.0, 0), (16.0, 1), (16.5, 1), (19.0, 0), (20, 0)]) ** 1.5
    trem = .75 + .25 * np.sin(2 * np.pi * .13 * t)
    for k, (f, det) in enumerate([(110.0, -6), (164.81, -2), (220.0, 3), (261.63, 7)]):
        for ch, sgn in enumerate((-1, 1)):
            fc = f * 2 ** ((det * sgn) / 1200)
            out[:, ch] += (np.sin(2 * np.pi * fc * t) if k % 2 == 0 else
                           (2 / np.pi) * np.arcsin(np.sin(2 * np.pi * fc * t))) / 4
    return out * env[:, None] * trem[:, None] * db(-30)

def write_wav(path, x, normalise_to=None):
    x = np.asarray(x, dtype=np.float64)
    if normalise_to is not None:
        x = x / (np.max(np.abs(x)) + 1e-12) * db(normalise_to)
    x = np.clip(x, -1, 1)
    pcm = (x * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1 if x.ndim == 1 else x.shape[1]); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())

def main():
    os.makedirs(OUT, exist_ok=True)
    bed = bed_room_hiss_hum(); pad = bed_pad()
    mix = bed + pad

    # ---- events synced to the shot list (see E01_제작패키지.md) ----
    at(mix, HITS["click"], 0.00, -16)                       # PLAY key
    for t in np.arange(0.0, 17.7, 1.6):                     # REC lamp relay tick on every blink
        at(mix, HITS["tick"], float(t), -34)
    for start, text in [(0.6, "STATION 7"), (4.5, "OPERATOR 027"), (12.5, "SIGNAL OK."), (18.3, "End of tape.")]:
        for i in range(len(text)):                          # one soft bip per typed character
            at(mix, HITS["bip"], start + i * 0.04, -34)
    at(mix, HITS["scrape"], 6.5, -26)                       # headset adjust
    at(mix, HITS["slide"], 9.2, -27)                        # cassette slides in
    at(mix, HITS["thunk"], 10.6, -14)                       # door closes
    at(mix, HITS["click"], 10.65, -24)                      # latch
    at(mix, HITS["hand"], 16.0, -22)                        # hand rests on the deck
    at(mix, HITS["click"], 18.3, -16)                       # STOP key
    at(mix, HITS["spindown"], 18.3, -24)                    # reels spin down

    # stage-friendly fade at the very end, then write
    mix *= ramp(N, [(0, 1), (19.6, 1), (20, 0)])[:, None]
    write_wav(f"{OUT}/E01_audio_temp_mix.wav", mix, normalise_to=-3)
    write_wav(f"{OUT}/bed_room_hiss_hum.wav", bed, normalise_to=-6)
    write_wav(f"{OUT}/bed_pad.wav", pad, normalise_to=-6)
    levels = {"click": -3, "thunk": -3, "slide": -6, "scrape": -6, "tick": -6, "bip": -6, "spindown": -3, "hand": -3}
    for k, v in HITS.items():
        write_wav(f"{OUT}/sfx_{k}.wav", v, normalise_to=levels[k])
    print("done:", sorted(os.listdir(OUT)))

if __name__ == "__main__":
    main()
