"""Builds what the panic film needs from one cut list, so picture and sound share the same timing.

Run: python build.py
  -> assets/shots.js   cut list, heartbeat times, end-scene timing (read by index.html)
  -> assets/score.wav  original score, synthesised here (no samples, no licence)
  -> assets/d-*.png    1-bit dithered photos, assets/scout-strip-paper.png
"""
import json
import os
import wave

import numpy as np
from PIL import Image, ImageOps, ImageEnhance
from scipy.signal import butter, sosfilt

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, "assets")
SRC = "C:/Users/Rohit Maity/Desktop/coding/Webdev/project/portfolio/apps/web/src/assets/Walktru/"
FPS = 60
CH = 9.6  # the panic ends here: hard cut to black and silence
TOTAL = 14.4
END = dict(fadeA=10.0, fadeB=10.8, untA=10.5, untB=11.9, walkA=11.4, walkB=12.9, x0=-760, stride=150,
           wordA=12.8, tagA=13.5, lineA=12.9, lineB=13.5)
rng = np.random.default_rng(2026)


# ---------------------------------------------------------------- images
def crop169(im, fy):
    w, h = im.size
    th = round(w * 9 / 16)
    if th <= h:
        top = round((h - th) * fy)
        return im.crop((0, top, w, top + th))
    tw = round(h * 16 / 9)
    left = (w - tw) // 2
    return im.crop((left, 0, left + tw, h))


def dither(src, name, fy):
    im = crop169(ImageOps.grayscale(Image.open(src)), fy)
    im = ImageEnhance.Contrast(im).enhance(1.5).resize((640, 360), Image.LANCZOS).convert("1")
    im = im.resize((1920, 1080), Image.NEAREST).convert("L")
    ImageOps.colorize(im, black=(15, 15, 18), white=(244, 244, 245)).save(os.path.join(A, f"d-{name}.png"), optimize=True)


dither(os.path.join(A, "eye-src.jpg"), "eye", 0.5)
for name, fy in (("phone", 0.4), ("owner", 0.3), ("buyer", 0.3), ("signup", 0.3), ("returning", 0.35)):
    dither(SRC + f"persona-{name}.jpg", name, fy)

ink = Image.open(os.path.join(A, "scout-strip-ink.png")).convert("RGBA")
r, g, b, a = ink.split()
inv = ImageOps.invert(Image.merge("RGB", (r, g, b)))
Image.merge("RGBA", (*inv.split(), a)).save(os.path.join(A, "scout-strip-paper.png"), optimize=True)

# ---------------------------------------------------------------- the cut list
WORDS = ["SEO", "LLMS.TXT", "HSTS", "CORS", "MOBILE?", "404", "500", "PRICING?", "ONBOARDING", "DMARC", "SITEMAP",
         "OG TAGS", "ALT TEXT", "CSP", "AUTH", "RATE LIMITS", "EMPTY STATE", "LCP 4.8s", "BROKEN LINKS", "PRIVACY",
         "API KEYS", "DOES IT WORK?", "WHO IS IT FOR?", "TESTED?", "NOT YET", "LAUNCH?", "HELP", "RETRY", "WHY?",
         "UNDEFINED", "NULL", "TODO", "DEPLOY", "ROLLBACK", "HOTFIX", "STRANGERS?", "STUCK?", "CLICK HERE?", "CHURN",
         "0 USERS", "ARE WE LIVE?", "TOO MUCH", "WAIT", "CACHE", "DNS", "SSL", "TIMEOUT", "OOPS"]
KINDS = {"word": 7, "rings": 1, "grid": 1, "spiral": 1, "morph": 1, "bars": 1, "burst": 1, "dots": 1, "errors": 2,
         "browsers": 1, "cursors": 1, "spinners": 1, "notifs": 1, "code": 1, "chart": 1, "photo": 2, "eye": 1,
         "scout": 2, "checklist": 1, "maze": 2, "foot": 1, "question": 1}
names, weights = list(KINDS), np.array(list(KINDS.values()), float)
weights /= weights.sum()

times = []
t = 0
while t < CH * FPS:
    x = t / (CH * FPS)
    n = max(3, round((0.05 + 0.40 * (1 - x) ** 1.6) * FPS))
    times.append((t, min(n, CH * FPS - t)))
    t += n

forced = {0: ("word", 1, "SHIP IT", 0), 1: ("word", 0, "WAIT.", 4), 2: ("checklist", 0, "", 0), 3: ("word", 6, "SIGNUP?", 5),
          4: ("maze", 1, "", 0), 5: ("errors", 0, "", 0), 6: ("eye", 2, "", 0)}
cuts, last_pal, word_i = [], -1, 0
for i, (f0, n) in enumerate(times):
    tc = f0 / FPS
    lay = "f"
    roll = rng.random()
    if tc >= 7.6:
        lay = "q" if roll < 0.4 else "s" if roll < 0.6 else "f"
    elif tc >= 5.0:
        lay = "q" if roll < 0.25 else "s" if roll < 0.5 else "f"
    elif tc >= 2.4:
        lay = "s" if roll < 0.2 else "f"
    items = []
    for j in range({"f": 1, "s": 2, "q": 4}[lay]):
        if i in forced and j == 0:
            k, pal, w, st = forced[i]
        else:
            k = str(rng.choice(names, p=weights))
            pal = int(rng.integers(0, 7))
            if j == 0 and pal == last_pal:
                pal = (pal + 3) % 7
            w = WORDS[word_i % len(WORDS)] if k == "word" else ""
            word_i += k == "word"
            st = int(rng.integers(0, 6))
        items.append({"k": k, "p": pal, "s": int(rng.integers(1, 1 << 30)), "w": w, "st": st})
    last_pal = items[0]["p"]
    cuts.append({"t": round(tc, 5), "d": round(n / FPS, 5), "lay": lay + ("v" if rng.random() < 0.5 else "h"), "items": items})

# heartbeat: 86 to 190 bpm across the panic
hb, ph = [], 0.0
for tt in np.arange(0, CH, 0.001):
    ph += (86 + 104 * (tt / CH) ** 1.4) / 60 * 0.001
    if ph >= 1:
        ph -= 1
        hb.append(round(float(tt), 4))

with open(os.path.join(A, "shots.js"), "w", encoding="utf-8") as fh:
    data = dict(fps=FPS, ch=CH, total=TOTAL, end=END, cuts=cuts, hb=hb, eye=[0.688, 0.47])
    fh.write("window.WT = " + json.dumps(data, separators=(",", ":")) + ";\n")
print(f"{len(cuts)} cuts, {len(hb)} heartbeats")

# ---------------------------------------------------------------- sound
SR = 44100
N = int(SR * TOTAL)
panic = np.zeros((2, N))
calm = np.zeros((2, N))
send = np.zeros((2, N))


def t_(dur): return np.arange(int(dur * SR)) / SR
def filt(x, kind, f): return sosfilt(butter(2, f, kind, fs=SR, output="sos"), x)
def lp(x, f): return filt(x, "lowpass", f)
def hp(x, f): return filt(x, "highpass", f)
def bp(x, lo, hi): return filt(x, "bandpass", [lo, min(hi, SR / 2 - 200)])
def noise(dur): return rng.standard_normal(len(t_(dur)))


def osc(freq, t, shape="sin"):
    ph_ = np.cumsum(np.broadcast_to(freq, t.shape)) / SR
    if shape == "saw":
        return 2 * (ph_ % 1) - 1
    if shape == "sq":
        return np.sign(np.sin(2 * np.pi * ph_))
    return np.sin(2 * np.pi * ph_)


def place(bus, sig, at, gain=1.0, pan=0.0, verb=0.0):
    i = int(round(at * SR))
    if i >= N or i < 0:
        return
    sig = sig[: N - i] * gain
    l, r_ = np.cos((pan + 1) * np.pi / 4) * 1.414, np.sin((pan + 1) * np.pi / 4) * 1.414
    bus[0, i:i + len(sig)] += sig * l
    bus[1, i:i + len(sig)] += sig * r_
    if verb:
        send[0, i:i + len(sig)] += sig * l * verb
        send[1, i:i + len(sig)] += sig * r_ * verb


def env(t, tau): return np.exp(-t / tau)


def kick(p=1.0):
    t = t_(0.35)
    return np.tanh((osc(44 + 160 * env(t, 0.03), t) * env(t, 0.13) + hp(noise(0.35), 2500) * env(t, 0.004) * 0.4) * 1.8 * p)


def thwack(f):
    t = t_(0.25)
    return np.tanh(osc(f * (1 + 1.6 * env(t, 0.016)), t) * env(t, 0.07) * 1.2 + bp(noise(0.25), 1400, 9000) * env(t, 0.02) * 0.9)


def zap(f):
    t = t_(0.14)
    return osc(f * (1 + 3 * env(t, 0.02)), t, "sq") * env(t, 0.035) * 0.5 + bp(noise(0.14), f * 0.8, f * 2.5) * env(t, 0.02)


def zap_up(f):
    t = t_(0.16)
    return osc(f * (1 + 4 * (t / 0.16)), t, "saw") * env(t, 0.05) * 0.45


def bonk():
    t = t_(0.18)
    return osc(np.where(t < 0.08, 440, 330), t, "sq") * env(t, 0.07) * 0.35


def ding():
    t = t_(0.35)
    return (osc(1320, t) + 0.6 * osc(1980, t)) * env(t, 0.09) * 0.5


def chirp():
    t = t_(0.09)
    return osc(2100 + 1800 * (t / 0.09), t) * np.sin(np.pi * t / 0.09) * 0.55


def shutter():
    t = t_(0.05)
    return bp(noise(0.05), 1800, 7000) * (env(t, 0.004) + (t >= 0.018) * env(np.clip(t - 0.018, 0, None), 0.006))


def tick(f=3000, d=0.005):
    t = t_(0.03)
    return osc(f, t) * env(t, d)


def whirr():
    t = t_(0.2)
    return osc(600 + 300 * np.sin(2 * np.pi * 40 * t), t) * env(t, 0.06) * 0.35


def glass():
    t = t_(0.2)
    return (osc(3150, t) + osc(4720, t) * 0.5) * env(t, 0.04) * 0.35


def hat():
    t = t_(0.05)
    return hp(noise(0.05), 7500) * env(t, 0.01)


def bell(f, dur=2.5):
    t = t_(dur)
    return sum(a_ * osc(f * r_, t) * env(t, d_) for r_, a_, d_ in ((1, 1, 1.8), (2.0, 0.4, 1.0), (2.76, 0.3, 0.7), (5.4, 0.15, 0.35))) * 0.5


def pluck_ks(f, dur):
    n, p_ = int(SR * dur), int(SR / f)
    buf = rng.uniform(-1, 1, p_)
    out = np.zeros(n)
    for i in range(n):
        j = i % p_
        out[i] = buf[j]
        buf[j] = 0.997 * 0.5 * (buf[j] + buf[(j + 1) % p_])
    return lp(out, 5000)


HIT = {"word": lambda: thwack(rng.uniform(110, 240)), "errors": bonk, "notifs": ding, "scout": chirp, "photo": shutter,
       "eye": shutter, "spinners": whirr, "browsers": glass, "maze": lambda: zap_up(rng.uniform(300, 900)),
       "foot": lambda: zap_up(rng.uniform(500, 1200))}

for i, c in enumerate(cuts):
    k, d = c["items"][0]["k"], c["d"]
    g = 0.6 * (d / 0.45) ** 0.4
    pan = float(rng.uniform(-0.6, 0.6))
    if k in HIT:
        place(panic, HIT[k](), c["t"], g, pan)
    elif k in ("code", "checklist", "cursors", "chart"):
        for m in range(6):
            place(panic, tick(rng.uniform(2500, 4200)), c["t"] + m * min(d, 0.3) / 6, g * 0.6, pan)
    else:
        place(panic, zap(rng.uniform(300, 3800)), c["t"], g, pan)
    place(panic, hat(), c["t"], 0.22, -pan)
    if d >= 0.1 and i % 2 == 0 or d < 0.1 and i % 4 == 0:
        place(panic, kick(), c["t"], 0.8)

for b_ in hb:  # the heart, low and felt
    place(panic, lp(kick(0.7), 500), b_, 0.55)
    place(panic, lp(kick(0.5), 400), b_ + 0.11, 0.35)
for k_ in range(1, 10):  # countdown beeps, then four fast ones in the last second
    place(panic, osc(1050, t_(0.07)) * env(t_(0.07), 0.03), CH - k_, 0.22)
for b_ in (8.85, 9.1, 9.35):
    place(panic, osc(1600, t_(0.07)) * env(t_(0.07), 0.03), b_, 0.25)

tt = t_(CH)
drone = osc(38 * 2 ** (tt / CH), tt, "saw") * 0.5 + osc(19 * 2 ** (tt / CH), tt) * 0.8
panic[:, : len(tt)] += np.tanh(lp(drone, 320) * 2) * (0.12 + 0.2 * (tt / CH) ** 2)
tin = osc(3200 * (2.1 ** np.clip((tt - 3) / (CH - 3), 0, 1)), tt) * 0.025 * np.clip((tt - 3) / (CH - 3), 0, 1) ** 2
panic[:, : len(tt)] += tin
rs = t_(CH - 6.2)
rise = sum(bp(noise(CH - 6.2), fc, fc * 1.6) * np.clip(1 - abs(rs / (CH - 6.2) * 7 - j), 0, 1) for j, fc in enumerate(np.geomspace(300, 9000, 8)))
place(panic, (rise * 2.2 + lp(osc(120 * 8 ** (rs / (CH - 6.2)), rs, "saw"), 3000) * 0.2) * (rs / (CH - 6.2)) ** 2, 6.2, 0.5)
ov = t_(0.6)
on = noise(0.6)
oe = (ov / 0.6) ** 2  # brightens as it swells
place(panic, np.tanh((lp(on, 700) * (1 - oe) + lp(on, 12000) * oe) * 3) * (ov / 0.6) ** 1.5, CH - 0.6, 0.45)

# the hard cut: the panic bus ends dead at CH (3 ms ramp, no click)
cut = np.clip((CH - np.arange(N) / SR) / 0.003, 0, 1)
panic = np.tanh(panic * 0.9) * cut

# calm: pad, the string pulled straight, footsteps, two bells
pt = t_(TOTAL - 10.25)
pad = sum(osc(f * d_, pt, "saw") for f in (130.81, 196.0, 246.94, 293.66, 329.63) for d_ in (0.997, 1.003))
pad = lp(pad / 10, 1100) * np.minimum(1, pt / 1.5) * np.clip((TOTAL - 10.25 - pt) / 1.2, 0, 1)
place(calm, pad, 10.25, 0.16, verb=0.3)
gt = t_(END["untB"] - END["untA"])
glide = osc(196 * 2 ** (gt / gt[-1]) * (1 + 0.006 * np.sin(2 * np.pi * 5 * gt)), gt) * np.sin(np.pi * gt / gt[-1]) ** 2
place(calm, glide, END["untA"], 0.05, verb=0.4)
place(calm, pluck_ks(392.0, 2.4), END["untB"], 0.5, verb=0.5)
prev = 0
for tw in np.arange(END["walkA"], END["walkB"], 0.001):
    p = min(1, (tw - END["walkA"]) / (END["walkB"] - END["walkA"]))
    dist = -END["x0"] * (1 - (1 - p) ** 3)
    step = int(dist // (END["stride"] / 2))
    if step > prev:
        prev = step
        place(calm, lp(tick(1300, 0.008), 2500), tw, 0.22, pan=-0.3 + 0.5 * p)
place(calm, bell(1046.5), END["wordA"], 0.22, verb=0.6)
place(calm, bell(1567.98), END["wordA"] + 0.12, 0.14, verb=0.6, pan=0.3)
place(calm, bell(2093.0, 2.0), END["tagA"], 0.07, verb=0.6, pan=-0.3)


def comb(x, d, g_):
    y = x.copy()
    for k in range(d, len(x), d):
        seg = y[k:k + d]
        seg += g_ * y[k - d:k - d + len(seg)]
    return y


def allpass(x, d, g_):
    y = np.zeros_like(x)
    y[:d] = -g_ * x[:d]
    for k in range(d, len(x), d):
        e = min(k + d, len(x))
        y[k:e] = -g_ * x[k:e] + x[k - d:e - d] + g_ * y[k - d:e - d]
    return y


def reverb(x, spread):
    wet = sum(comb(x, d + spread, 0.82) for d in (1557, 1617, 1491, 1422))
    for d in (225, 556):
        wet = allpass(wet, d, 0.5)
    return lp(wet, 5000) * 0.1


calm[0] += reverb(send[0], 0)
calm[1] += reverb(send[1], 23)

pm = hp(panic, 25)
pm *= 10 ** (-13.5 / 20) / np.sqrt(np.mean(pm[:, : int(CH * SR)] ** 2))  # loud panic
mix = np.clip(pm + calm * 1.8, -0.92, 0.92)
mix *= np.clip((TOTAL - np.arange(N) / SR) / 0.4, 0, 1)
with wave.open(os.path.join(A, "score.wav"), "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((mix.T * 32767).astype("<i2").tobytes())
print("wrote score.wav", f"{TOTAL:.1f}s")
