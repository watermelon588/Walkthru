"""Original score for the 15 s Walkthru film, synthesised from scratch (no samples, no licence).

128 BPM, so 32 beats = 15.0 s exactly; index.html cuts on the same beat grid.
Run: python score.py  ->  assets/score.wav (44.1 kHz, 16-bit stereo)
"""
import os
import wave

import numpy as np
from scipy.signal import butter, sosfilt

SR = 44100
B = 60 / 128  # one beat in seconds
N = int(SR * 15.0)
rng = np.random.default_rng(7)

main = np.zeros((2, N))
bass_bus = np.zeros((2, N))
send = np.zeros((2, N))  # reverb send
kicks = []  # kick times in beats, for the sidechain


def t_(dur):
    return np.arange(int(dur * SR)) / SR


def filt(x, kind, f):
    return sosfilt(butter(2, f, kind, fs=SR, output="sos"), x)


def lp(x, f): return filt(x, "lowpass", f)
def hp(x, f): return filt(x, "highpass", f)
def bp(x, lo, hi): return filt(x, "bandpass", [lo, min(hi, SR / 2 - 100)])


def noise(dur): return rng.standard_normal(len(t_(dur)))


def osc(freq, t, shape="sin"):
    f = np.broadcast_to(freq, t.shape)
    ph = np.cumsum(f) / SR
    if shape == "saw":
        return 2 * (ph % 1) - 1
    if shape == "sq":
        return np.sign(np.sin(2 * np.pi * ph))
    return np.sin(2 * np.pi * ph)


def place(sig, beat, gain=1.0, pan=0.0, verb=0.0, bus=None):
    i = int(round(beat * B * SR))
    if i >= N:
        return
    sig = sig[: N - i] * gain
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    target = main if bus is None else bus
    target[0, i:i + len(sig)] += sig * l * 1.414
    target[1, i:i + len(sig)] += sig * r * 1.414
    if verb:
        send[0, i:i + len(sig)] += sig * l * verb
        send[1, i:i + len(sig)] += sig * r * verb


# ---------------------------------------------------------------- instruments
def kick(punch=1.0):
    t = t_(0.45)
    f = 44 + 150 * np.exp(-t / 0.032)
    body = osc(f, t) * np.exp(-t / 0.17)
    click = hp(noise(0.45), 2500) * np.exp(-t / 0.004) * 0.35
    return np.tanh((body + click) * 1.7 * punch)


def clap():
    t = t_(0.4)
    e = sum((t >= d) * np.exp(-np.clip(t - d, 0, None) / 0.006) for d in (0, 0.011, 0.023))
    e = e + (t >= 0.03) * np.exp(-np.clip(t - 0.03, 0, None) / 0.11) * 0.7
    return bp(noise(0.4), 900, 6000) * e


def hat(open_=False):
    t = t_(0.3 if open_ else 0.06)
    return hp(noise(len(t) / SR), 7500) * np.exp(-t / (0.08 if open_ else 0.011))


def tick(f=3200, decay=0.006):
    t = t_(0.04)
    return osc(f, t) * np.exp(-t / decay)


def shutter():
    t = t_(0.05)
    e = np.exp(-t / 0.004) + (t >= 0.018) * np.exp(-np.clip(t - 0.018, 0, None) / 0.006)
    return bp(noise(0.05), 1800, 7000) * e


def thwack(f=170):
    t = t_(0.32)
    body = osc(f * (1 + 1.6 * np.exp(-t / 0.018)), t) * np.exp(-t / 0.09)
    snap = bp(noise(0.32), 1400, 9000) * np.exp(-t / 0.022)
    return np.tanh(body * 1.2 + snap * 0.8)


def impact(dur=1.8, weight=1.0):
    t = t_(dur)
    sub = osc(28 + 70 * np.exp(-t / 0.07), t) * np.exp(-t / (0.45 * weight))
    crash = lp(noise(dur), 5500) * np.exp(-t / 0.3) * 0.55
    return np.tanh(sub * 2.0 + crash)


def sweep(dur, f0, f1, env):
    """Noise through a bandpass that slides from f0 to f1 (crossfaded bands)."""
    t = t_(dur)
    n = noise(dur)
    bands = np.geomspace(f0, f1, 10)
    pos = t / dur * (len(bands) - 1)
    out = np.zeros(len(t))
    for i, fc in enumerate(bands):
        out += bp(n, fc * 0.7, fc * 1.45) * np.clip(1 - abs(pos - i), 0, 1)
    return out * env(t / dur)


def whoosh(dur=0.45, up=True):
    f0, f1 = (300, 7000) if up else (7000, 300)
    return sweep(dur, f0, f1, lambda p: np.sin(np.pi * p) ** 2) * 2.2


def riser(dur):
    t = t_(dur)
    tone = osc(180 * (12 ** (t / dur)), t, "saw")
    tone = lp(tone, 3000) * 0.25
    return (sweep(dur, 400, 11000, lambda p: p ** 2.2) * 2.4 + tone * (t / dur) ** 2)


def glitch(dur, base=110):
    """Stuttered buzz + bit-crushed noise + a tape-stop tail."""
    t = t_(dur)
    grain = int(SR * B / 8)  # 32nd notes
    buzz = osc(base * 2, t, "sq") * 0.5 + noise(dur) * 0.5
    gate = ((np.arange(len(t)) // grain) % 2 == 0).astype(float)
    crushed = np.round(buzz * 4) / 4
    crushed = np.repeat(crushed[::12], 12)[: len(t)]
    stop = osc(base * np.clip(1 - t / dur, 0.02, 1), t, "saw") * (t / dur)
    return np.tanh((crushed * gate + stop * 0.6) * 1.5) * np.exp(-t / (dur * 0.9))


def pluck(f):
    t = t_(0.35)
    return (osc(f, t) + 0.35 * osc(2 * f, t) + 0.12 * osc(3 * f, t)) * np.exp(-t / 0.09)


def bell(f, dur=2.4):
    t = t_(dur)
    parts = [(1, 1, 1.6), (2.0, 0.45, 1.0), (2.76, 0.35, 0.7), (5.4, 0.2, 0.35), (8.93, 0.12, 0.2)]
    return sum(a * osc(f * r, t) * np.exp(-t / d) for r, a, d in parts) * 0.5


def bass_note(f, dur):
    t = t_(dur)
    s = osc(f, t, "saw") * 0.6 + osc(f / 2, t) * 0.8
    cut = 250 + 1600 * np.exp(-t / 0.05)
    # piecewise filter sweep: three passes with falling cutoff
    s = lp(s, float(cut[0])) * np.exp(-t / 0.06) + lp(s, 320) * (1 - np.exp(-t / 0.06))
    return np.tanh(s * 1.4) * np.minimum(1, (dur - t) / 0.01)


def pad(freqs, dur):
    t = t_(dur)
    s = sum(osc(f * d, t, "saw") for f in freqs for d in (0.996, 1.0, 1.004))
    s = lp(s / (len(freqs) * 3), 1800)
    att = np.minimum(1, t / 0.35)
    rel = np.clip((dur - t) / 1.2, 0, 1)
    return s * att * rel


# notes
A1, C2, F1, G1, E2 = 55.0, 65.41, 43.65, 49.0, 82.41
PENTA = [440.0, 523.25, 587.33, 659.25, 783.99, 880.0, 1046.5, 1174.66]

# ---------------------------------------------------------------- arrangement
groove = [b for b in range(0, 14)] + [b for b in range(18, 27)]

# drums
for b in groove:
    place(kick(), b, 0.95)
    kicks.append(b)
    place(hat(open_=b >= 18), b + 0.5, 0.16 if b < 18 else 0.11, pan=0.25)
    if b >= 10:
        place(hat(), b + 0.25, 0.07, pan=-0.3)
        place(hat(), b + 0.75, 0.07, pan=-0.3)
    if b >= 4 and b % 2 == 1:
        place(clap(), b, 0.5, verb=0.35)
place(kick(1.4), 15, 1.0)
kicks.append(15)
for b, g in ((16, 0.55), (16.3, 0.4), (17, 0.55), (17.3, 0.4)):  # heartbeat under the thought
    place(lp(kick(0.8), 900), b, g)

# bass: eighth notes, octave pump, one root per bar
roots = {0: A1, 1: F1, 2: C2, 3: G1, 4: A1, 5: F1, 6: G1}
for b in groove:
    root = roots[b // 4]
    for k, mult in ((0, 1), (0.5, 2)):
        place(bass_note(root * mult, B * 0.45), b + k, 0.3, bus=bass_bus)
place(bass_note(A1, B * 1.9), 15, 0.4, bus=bass_bus)

# hook: word slams and the url being typed
for b, f in ((0, 150), (1, 190), (2, 140)):
    place(thwack(f), b, 0.6, verb=0.2)
place(impact(1.2, 0.8), 0, 0.7, verb=0.3)
for i in range(11):
    place(tick(2600 + 90 * i), 3 + i * 0.07, 0.22, pan=0.2)

# strangers: one shutter per photo cut, words slam, glitch on STUCK?
for k in range(6):
    place(shutter(), 4 + k * 0.5, 0.5, pan=(-0.4 if k % 2 else 0.4))
for b, f in ((4, 160), (5, 120), (6, 180)):
    place(thwack(f), b, 0.5, verb=0.2)
place(riser(B * 1.5), 5.5, 0.35)
place(glitch(B * 0.95, 98), 7, 0.55)

# test users flood in
place(impact(1.6, 1.1), 8, 0.9, verb=0.4)
for i in range(8):
    place(pluck(PENTA[i]), 8 + i * 0.25, 0.22, pan=-0.5 + i / 7, verb=0.3)
for i in range(16):
    place(tick(900 + rng.uniform(-150, 150), 0.004), 8 + i * 0.125, 0.12, pan=rng.uniform(-0.7, 0.7))
place(whoosh(0.4), 9.55, 0.45)

# the run: page draws, clicks, masked typing, nothing happens, stuck
place(whoosh(0.3, up=False), 10, 0.3)
for b in (10.6, 13.25):
    place(tick(2400), b, 0.35, pan=0.15)
    place(tick(1700), b + 0.12, 0.3, pan=0.15)
for b in (11.4, 12.3):
    place(tick(2200), b, 0.3, pan=0.1)
for start, count in ((11.5, 7), (12.4, 6)):
    for i in range(count):
        place(tick(3400 + rng.uniform(-200, 200), 0.004), start + i * 0.06, 0.18, pan=-0.1)
for i, b in enumerate((14, 14.25, 14.5)):  # confused clicking in the silence
    place(tick(2400 - i * 200), b, 0.4)
place(tick(1200, 0.01), 14.75, 0.25)
place(riser(B * 1.0), 14.0, 0.4)
place(glitch(B * 0.8, 70), 15, 0.65)
place(impact(1.4, 1.2), 15, 0.8, verb=0.3)
for i in range(16):  # the thought being typed
    place(tick(3000 + rng.uniform(-300, 300), 0.003), 15.7 + i * 0.056, 0.12)
place(whoosh(0.35), 17.6, 0.4)

# report: four words, four rising notes
for i, b in enumerate((18, 19, 20, 21)):
    place(thwack(150 + 20 * i), b, 0.5, verb=0.2)
    place(pluck(PENTA[[0, 2, 3, 4][i]] * 2), b, 0.18, verb=0.4)

# score: fix, rerun, counter, ding
place(riser(B * 2.2), 22, 0.35)
for b in (23, 24):
    place(thwack(200), b, 0.55, verb=0.25)
for i in range(29):
    place(tick(1800 + i * 45, 0.003), 24 + i * 0.033, 0.12)
place(bell(1318.5), 25, 0.35, verb=0.5)
place(clap(), 25, 0.4, verb=0.4)

# logo: whip, a few footsteps, the landing chord
place(whoosh(0.4), 25.7, 0.5)
for i in range(6):
    place(tick(1000 + 120 * (i % 2), 0.004), 26.25 + i * 0.33, 0.15, pan=-0.6 + i * 0.2)
place(whoosh(B * 0.9)[::-1] * np.linspace(0, 1, int(B * 0.9 * SR)) ** 2, 27.1, 0.5)
place(impact(2.0, 1.4), 28, 0.6, verb=0.5)
place(pad([130.81, 164.81, 196.0, 246.94, 293.66], 15.0 - 27 * B), 27, 0.3, verb=0.3)
place(bell(1046.5, 3.0), 28, 0.28, verb=0.6)
place(bell(783.99, 3.0), 28.5, 0.2, verb=0.6, pan=-0.3)
place(bell(1318.5, 2.6), 29, 0.18, verb=0.6, pan=0.3)
place(bass_note(C2 / 2, B * 4), 28, 0.35, bus=bass_bus)

# ---------------------------------------------------------------- mix
# sidechain the bass to the kick
duck = np.ones(N)
tt = np.arange(N) / SR
for b in kicks:
    k0 = b * B
    m = tt >= k0
    duck[m] = np.minimum(duck[m], 1 - 0.75 * np.exp(-(tt[m] - k0) / 0.09))
main += bass_bus * duck


def comb(x, d, g):
    y = x.copy()
    for k in range(d, len(x), d):
        seg = y[k:k + d]
        seg += g * y[k - d:k - d + len(seg)]
    return y


def allpass(x, d, g):
    y = np.zeros_like(x)
    y[:d] = -g * x[:d]
    for k in range(d, len(x), d):
        e = min(k + d, len(x))
        y[k:e] = -g * x[k:e] + x[k - d:e - d] + g * y[k - d:e - d]
    return y


def reverb(x, spread):
    wet = sum(comb(x, d + spread, 0.78) for d in (1557, 1617, 1491, 1422))
    for d in (225, 556):
        wet = allpass(wet, d, 0.5)
    return lp(wet, 6000) * 0.12


main[0] += reverb(send[0], 0)
main[1] += reverb(send[1], 23)

main = hp(main, 25)
main /= np.max(np.abs(main))
main = np.tanh(main * 1.4) / np.tanh(1.4)  # gentle soft clip, keeps the transients
main *= 10 ** (-14.1 / 20) / np.sqrt(np.mean(main ** 2))  # about -14 LUFS for this mix
main = np.clip(main, -0.89, 0.89)
fade = np.clip((15.0 - tt) / 0.25, 0, 1)
main *= fade

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "score.wav")
pcm = (main.T * 32767).astype("<i2")
with wave.open(out, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print("wrote", out, f"{N / SR:.2f}s")
