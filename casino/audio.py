"""Sintetizador de efectos de sonido (todo generado por código con numpy).

Filosofía: tonos suaves tipo campana/marimba, ataques sin chasquidos, filtros que
quitan agudos estridentes y un poco de reverberación para que todo suene «redondo».
"""
import math
import random
import threading
import time

import numpy as np
import pygame

SR = 44100
PENTA = [0, 2, 4, 7, 9, 12, 14, 16, 19, 21, 24, 26, 28, 31, 33, 36]


def note(semi, base=261.63):
    """Frecuencia a `semi` semitonos de C4 (tono general grave y cálido)."""
    return base * 2 ** (semi / 12)


# ----------------------------------------------------------------------------
# Bloques básicos
# ----------------------------------------------------------------------------
def _t(dur):
    return np.arange(int(SR * dur)) / SR


def _attack(x, ms=4):
    n = min(len(x), int(SR * ms / 1000))
    if n > 1:
        x[:n] *= np.linspace(0, 1, n) ** 1.5
    return x


def _release(x, ms=20):
    n = min(len(x), int(SR * ms / 1000))
    if n > 1:
        x[-n:] *= np.linspace(1, 0, n)
    return x


def partials(freq, dur, parts, attack_ms=3):
    """parts: lista de (multiplicador, amplitud, caída en segundos)."""
    t = _t(dur)
    x = np.zeros_like(t)
    for mult, amp, decay in parts:
        f = freq * mult
        if f > SR / 2.2:
            continue
        x += amp * np.sin(2 * np.pi * f * t) * np.exp(-t / decay)
    return _release(_attack(x, attack_ms))


def bell(freq, dur=1.2, bright=1.0):
    return partials(freq, dur, [(1, 1.0, 0.55), (2.0, 0.28 * bright, 0.22), (3.0, 0.10 * bright, 0.12),
                                (4.16, 0.06 * bright, 0.07), (0.5, 0.12, 0.4)])


def marimba(freq, dur=0.6):
    return partials(freq, dur, [(1, 1.0, 0.22), (3.93, 0.18, 0.04), (9.2, 0.05, 0.012)], attack_ms=2)


def soft_sine(freq, dur, decay=0.3):
    return partials(freq, dur, [(1, 1.0, decay), (2, 0.08, decay * 0.5)], attack_ms=8)


def sweep(f0, f1, dur, decay=None, curve="exp"):
    t = _t(dur)
    if curve == "exp":
        f = f0 * (f1 / f0) ** (t / dur)
    else:
        f = f0 + (f1 - f0) * (t / dur)
    ph = np.cumsum(2 * np.pi * f / SR)
    x = np.sin(ph)
    if decay:
        x *= np.exp(-t / decay)
    return _release(_attack(x, 3))


def noise(dur):
    return np.random.uniform(-1, 1, int(SR * dur))


def bandpass(x, lo=None, hi=None):
    """Filtro por FFT con caídas suaves."""
    n = len(x)
    if n < 8:
        return x
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    g = np.ones_like(f)
    if lo:
        g *= 1 / (1 + (lo / np.maximum(f, 1)) ** 4)
    if hi:
        g *= 1 / (1 + (f / hi) ** 4)
    return np.fft.irfft(X * g, n)


def env(n, attack, decay):
    t = np.arange(n) / SR
    e = np.exp(-t / decay)
    na = int(SR * attack)
    if na > 0:
        e[:na] *= np.linspace(0, 1, na)
    return e


def fftconv(x, h):
    n = len(x) + len(h) - 1
    nfft = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, nfft) * np.fft.rfft(h, nfft), nfft)[:n]


_IR_CACHE = {}


def _impulse(length, seed):
    key = (length, seed)
    if key not in _IR_CACHE:
        rng = np.random.default_rng(seed)
        n = int(SR * length)
        t = np.arange(n) / SR
        ir = rng.uniform(-1, 1, n) * np.exp(-t / (length / 5))
        ir = bandpass(ir, lo=200, hi=5000)
        ir[:int(SR * 0.012)] = 0  # pre-delay
        ir /= np.sqrt(np.sum(ir ** 2)) + 1e-9
        _IR_CACHE[key] = ir
    return _IR_CACHE[key]


def reverb(x, length=1.4, mix=0.25):
    """Reverb estéreo: devuelve (izq, der)."""
    pad = np.concatenate([x, np.zeros(int(SR * length))])
    def fit(a):
        out = np.zeros(len(pad))
        m = min(len(a), len(pad))
        out[:m] = a[:m]
        return out
    wl = fit(fftconv(x, _impulse(length, 1)))
    wr = fit(fftconv(x, _impulse(length, 2)))
    k = mix * 1.6
    return pad + wl * k, pad + wr * k


def mix(*layers):
    """Mezcla capas (array, desfase_segundos, ganancia)."""
    total = max(int(SR * off) + len(a) for a, off, g in layers)
    out = np.zeros(total)
    for a, off, g in layers:
        i = int(SR * off)
        out[i:i + len(a)] += a * g
    return out


def seq(notes_fn, freqs, step, dur, gains=None):
    layers = []
    for i, f in enumerate(freqs):
        g = gains[i] if gains else 1.0
        layers.append((notes_fn(f, dur), i * step, g))
    return mix(*layers)


# ----------------------------------------------------------------------------
# Biblioteca de sonidos
# ----------------------------------------------------------------------------
def build_library():
    L = {}  # nombre -> (mono o (izq, der), volumen)

    def add(name, x, vol=0.5, rev=None):
        if rev:
            x = reverb(x, *rev)
        L[name] = (x, vol)

    # --- moneda: campanita cuyo tono sube con el combo (escala pentatónica)
    for i in range(16):
        # «tap» de madera: golpe grave + tono corto que sube con el combo
        f = note(PENTA[i])
        tone = partials(f, 0.22, [(1, 1.0, 0.05), (2.0, 0.25, 0.02)], attack_ms=1)
        body = sweep(200, 95, 0.07, decay=0.025)
        knock = bandpass(noise(0.02), 500, 2200) * env(882, 0.0005, 0.004)
        add(f"click{i}", mix((body, 0, 1.0), (tone, 0, 0.45), (knock, 0, 0.35)), 0.36, (0.35, 0.05))
    add("crit", mix((bell(note(12), 1.2), 0, 0.8), (bell(note(19), 1.2), 0.03, 0.6), (bell(note(24), 1.0), 0.06, 0.5)),
        0.38, (1.2, 0.3))

    # --- interfaz
    add("hover", partials(700, 0.04, [(1, 1, 0.01)], 1), 0.05)
    tok = mix((sweep(300, 170, 0.06, decay=0.02), 0, 1.0),
              (bandpass(noise(0.02), 400, 1800) * env(882, 0.0005, 0.003), 0, 0.4))
    add("ui", tok, 0.38, (0.3, 0.05))
    wh = bandpass(noise(0.22), 500, 2500) * np.sin(np.linspace(0, np.pi, int(SR * 0.22))) ** 2
    add("tab", wh, 0.10)
    add("buy", seq(marimba, [note(4), note(11)], 0.06, 0.5), 0.36, (0.9, 0.2))
    add("buy_big", seq(marimba, [note(4), note(8), note(11), note(16)], 0.05, 0.6), 0.36, (1.0, 0.22))
    add("error", bandpass(seq(lambda f, d: soft_sine(f, d, 0.12), [330, 262], 0.09, 0.3), hi=1500), 0.26, (0.5, 0.1))
    add("unlock", mix((seq(bell, [note(0), note(4), note(7), note(12)], 0.08, 1.0), 0, 0.7),
                      (seq(lambda f, d: partials(f, d, [(1, 1, 0.15)]), [note(24), note(28), note(31)], 0.05, 0.4), 0.3, 0.2)),
        0.36, (1.6, 0.3))

    # --- resultados
    add("win1", seq(marimba, [note(0), note(4), note(7)], 0.07, 0.6), 0.40, (1.0, 0.25))
    add("win2", mix((seq(marimba, [note(0), note(4), note(7), note(12)], 0.065, 0.7), 0, 1.0),
                    (seq(lambda f, d: bell(f, d, 0.6), [note(19), note(24)], 0.07, 1.0), 0.26, 0.35)), 0.42, (1.3, 0.28))
    shimmer = mix(*[(partials(note(24 + random.choice([0, 4, 7, 12])), 0.5, [(1, 1, 0.12)]), 0.4 + i * 0.06, 0.18)
                    for i in range(12)])
    add("win3", mix((seq(marimba, [note(0), note(4), note(7), note(12), note(16), note(19)], 0.06, 0.8), 0, 1.0),
                    (seq(lambda f, d: bell(f, d), [note(0), note(4), note(7)], 0.0, 2.0), 0.36, 0.35),
                    (shimmer, 0, 1.0)), 0.44, (2.0, 0.32))
    add("lose", bandpass(seq(lambda f, d: soft_sine(f, d, 0.18), [392, 330], 0.11, 0.45), hi=1400), 0.22, (0.8, 0.15))
    add("push", bandpass(soft_sine(440, 0.4, 0.15), hi=1800), 0.22, (0.6, 0.15))

    # --- cartas y fichas
    for i in range(3):
        n = int(SR * 0.11)
        sw = bandpass(noise(0.11), 1200 + i * 300, 6000) * env(n, 0.008, 0.03)
        add(f"card{i}", mix((sw, 0, 1.0), (sweep(220, 120, 0.05, decay=0.02), 0.01, 0.25)), 0.30)
    for i in range(3):
        n = int(SR * 0.03)
        clk = bandpass(noise(0.03), 1200, 3800) * env(n, 0.0005, 0.004)
        res = partials(1300 + i * 150, 0.05, [(1, 1, 0.012), (1.5, 0.4, 0.008)], 0.5)
        c1 = mix((clk, 0, 1), (res, 0, 0.35))
        add(f"chip{i}", mix((c1, 0, 1.0), (c1, 0.035 + i * 0.006, 0.6)), 0.28, (0.3, 0.08))
    for i in range(4):
        n = int(SR * 0.02)
        tk = mix((bandpass(noise(0.02), 700, 2600) * env(n, 0.0005, 0.003), 0, 0.8),
                 (partials(700 + i * 90, 0.04, [(1, 1, 0.008)], 0.5), 0, 0.5))
        add(f"tick{i}", tk, 0.16)
    reel = mix((bandpass(noise(0.02), 400, 1800) * env(int(SR * 0.02), 0.0005, 0.004), 0, 0.7),
               (partials(520, 0.03, [(1, 1, 0.006)], 0.5), 0, 0.4))
    add("reel_tick", reel, 0.07)
    thunk = mix((sweep(190, 80, 0.16, decay=0.05), 0, 1.0), (bandpass(noise(0.03), 200, 1500) * env(1323, 0.001, 0.008), 0, 0.4))
    add("reel_stop", thunk, 0.42, (0.4, 0.1))
    add("spin_start", bandpass(noise(0.4), 300, 2500) * np.linspace(0, 1, int(SR * 0.4)) ** 2 * np.linspace(1, 0, int(SR * 0.4)) ** 0.5, 0.12)
    land = mix((reel * 2, 0, 1.0), (reel * 1.5, 0.09, 0.7), (reel, 0.16, 0.5), (sweep(300, 200, 0.1, decay=0.04), 0.0, 0.3))
    add("ball_land", land, 0.45, (0.5, 0.15))
    rattle = mix(*[(mix((partials(random.uniform(800, 1400), 0.05, [(1, 1, 0.012)], 0.5), 0, 0.6),
                        (bandpass(noise(0.01), 1000, 4000) * env(441, 0.0005, 0.002), 0, 0.5)),
                    random.uniform(0, 0.28), 0.8) for _ in range(7)])
    add("dice", rattle, 0.30, (0.3, 0.1))
    n = int(SR * 0.4)
    swh = bandpass(noise(0.4), 600, 3500) * np.sin(np.linspace(0, np.pi, n)) ** 3
    add("whoosh", swh, 0.16)
    add("ting", bell(note(19), 1.0, 0.7), 0.30, (1.0, 0.25))

    # --- crash
    add("cashout", mix((seq(bell, [note(12), note(16), note(19), note(24)], 0.045, 1.2), 0, 0.8),
                       (marimba(note(0), 0.5), 0, 0.5)), 0.42, (1.6, 0.3))
    n = int(SR * 0.9)
    whump = bandpass(noise(0.9), 30, 420) * env(n, 0.005, 0.18) * 2.2
    add("explode", mix((whump, 0, 1.0), (sweep(120, 38, 0.6, decay=0.22), 0, 0.8)), 0.48, (1.2, 0.18))
    for i in range(12):
        add(f"blip{i}", bell(note(PENTA[min(i, 15)]), 0.6, 0.5), 0.18, (0.7, 0.15))

    # --- minas
    for i in range(16):
        f = note(PENTA[i])
        g = mix((bell(f, 0.9, 0.8), 0, 1.0), (partials(f * 2, 0.3, [(1, 1, 0.05)]), 0.02, 0.25))
        add(f"gem{i}", g, 0.30, (1.0, 0.25))
    add("bomb", mix((whump, 0, 1.0), (sweep(90, 30, 0.8, decay=0.3), 0, 0.9)), 0.50, (1.4, 0.2))

    # --- plinko / keno
    for i in range(8):
        add(f"peg{i}", partials(note(PENTA[i] + 12), 0.12, [(1, 1, 0.03), (2.7, 0.15, 0.01)], 1), 0.07)
    for i in range(6):
        add(f"land{i}", marimba(note([-12, -5, 0, 4, 7, 12][i]), 0.6), 0.32, (0.8, 0.2))
    for i in range(10):
        f0 = 260 + i * 40
        add(f"pop{i}", sweep(f0, f0 * 2.6, 0.06, decay=0.025), 0.20, (0.4, 0.1))
    add("keno_hit", bell(note(16), 0.8), 0.28, (0.9, 0.22))

    # --- caballos
    gal = mix((sweep(110, 60, 0.07, decay=0.025), 0, 1.0), (bandpass(noise(0.03), 100, 800) * env(1323, 0.001, 0.01), 0, 0.3))
    add("gallop", gal, 0.16)
    add("race_start", mix((bell(note(7), 0.8), 0, 1), (bell(note(7), 0.8), 0.28, 1), (bell(note(14), 1.2), 0.56, 1)), 0.32, (1.0, 0.2))
    add("fanfare", mix((seq(marimba, [note(0), note(4), note(7), note(12), note(7), note(12)], 0.09, 0.7), 0, 1.0),
                       (seq(bell, [note(12), note(16), note(19)], 0.0, 1.8), 0.5, 0.3)), 0.40, (1.6, 0.3))

    # --- rasca
    for i in range(4):
        n = int(SR * 0.05)
        add(f"scratch{i}", bandpass(noise(0.05), 1800 + i * 400, 6000) * env(n, 0.006, 0.02), 0.07)

    # --- magia
    sp = mix(*[(partials(random.uniform(900, 1900), 0.3, [(1, 1, 0.06)], 1), random.uniform(0, 0.5), 0.5)
               for _ in range(10)])
    add("sparkle", sp, 0.16, (1.0, 0.3))
    add("golden", mix((seq(lambda f, d: bell(f, d, 0.7), [note(s) for s in (0, 4, 7, 12, 16, 19, 24, 28)], 0.045, 1.0), 0, 0.8),
                      (sp, 0.1, 0.8)), 0.38, (1.8, 0.35))
    add("achievement", mix((seq(bell, [note(0), note(4), note(7), note(12)], 0.0, 2.0), 0, 0.5),
                           (seq(marimba, [note(7), note(12), note(16)], 0.08, 0.6), 0, 0.8)), 0.36, (2.2, 0.35))
    t = _t(2.8)
    pad = np.zeros_like(t)
    for s in (0, 4, 7, 11, 14):
        for det in (-0.12, 0.0, 0.12):
            pad += np.sin(2 * np.pi * note(s - 12) * 2 ** (det / 12) * t) / 15
    pad *= np.minimum(1, t / 0.5) * np.exp(-np.maximum(0, t - 1.2) / 0.6)
    add("prestige", mix((pad, 0, 1.0), (seq(bell, [note(12), note(16), note(19), note(23), note(24)], 0.12, 1.5), 0.2, 0.5)),
        0.45, (2.5, 0.35))
    add("count", partials(900, 0.03, [(1, 1, 0.006)], 0.5), 0.06)
    # extra para los juegos nuevos
    add("cup", mix((sweep(240, 120, 0.09, decay=0.03), 0, 1.0),
                   (bandpass(noise(0.04), 300, 1500) * env(1764, 0.001, 0.01), 0, 0.5)), 0.32, (0.3, 0.06))
    add("slide", bandpass(noise(0.18), 200, 1200) * np.sin(np.linspace(0, np.pi, int(SR * 0.18))) ** 2, 0.14)
    add("dice_hit", mix((sweep(260, 140, 0.05, decay=0.02), 0, 1.0),
                        (bandpass(noise(0.02), 600, 2400) * env(882, 0.0005, 0.003), 0, 0.6)), 0.32)
    add("ball_pop", sweep(180, 420, 0.07, decay=0.03), 0.26, (0.4, 0.1))
    add("tumble", mix((sweep(500, 160, 0.18, decay=0.07), 0, 0.8),
                      (bandpass(noise(0.12), 300, 2000) * env(int(SR * 0.12), 0.002, 0.03), 0, 0.5)), 0.26)
    add("orb", mix((bell(note(12), 0.9, 0.5), 0, 1.0), (bell(note(19), 0.9, 0.4), 0.05, 0.6)), 0.30, (1.0, 0.25))
    add("scatter", mix((bell(note(7), 1.2, 0.6), 0, 1.0), (bell(note(14), 1.2, 0.6), 0.09, 0.8)), 0.34, (1.2, 0.3))

    # --- pico minero: golpes y roturas suaves (lofi: sin agudos, algo de sala)
    def grains(dur, lo, hi, density=60, decay=0.05, seed=0):
        """Ruido granulado (tierra/grava): muchos clics pequeños filtrados."""
        rng = np.random.default_rng(seed)
        n = int(SR * dur)
        x = np.zeros(n)
        for _ in range(int(density * dur)):
            i = rng.integers(0, max(1, n - 400))
            g = rng.uniform(0.3, 1.0) * np.exp(-np.arange(400) / rng.uniform(40, 140))
            x[i:i + 400] += g * rng.uniform(-1, 1, 400)
        x *= env(n, 0.002, decay)
        return bandpass(x, lo, hi)

    for i in range(4):
        add(f"mine_dirt{i}", mix((grains(0.14, 120, 1400, 160, 0.05, i), 0, 1.0),
                                 (sweep(130 + i * 8, 80, 0.08, decay=0.03), 0, 0.5)), 0.20, (0.25, 0.08))
        add(f"mine_stone{i}", mix((bandpass(noise(0.06), 300, 2200) * env(int(SR * 0.06), 0.001, 0.012), 0, 0.8),
                                  (sweep(300 + i * 25, 180, 0.07, decay=0.025), 0, 0.7)), 0.17, (0.3, 0.1))
        add(f"mine_ore{i}", mix((bandpass(noise(0.05), 300, 2000) * env(int(SR * 0.05), 0.001, 0.010), 0, 0.6),
                                (partials(note(PENTA[3 + i]), 0.18, [(1, 0.6, 0.06), (2, 0.15, 0.03)], 2), 0, 0.6)),
            0.16, (0.4, 0.12))
    for i in range(3):
        add(f"break_dirt{i}", grains(0.28, 100, 1200, 260, 0.09, 10 + i), 0.24, (0.35, 0.1))
        add(f"break_stone{i}", mix((grains(0.26, 200, 2000, 220, 0.08, 20 + i), 0, 1.0),
                                   (sweep(220, 110, 0.12, decay=0.05), 0, 0.5)), 0.22, (0.4, 0.12))
        add(f"break_ore{i}", mix((grains(0.24, 200, 2000, 200, 0.08, 30 + i), 0, 0.8),
                                 (bandpass(marimba(note(PENTA[5 + i * 2]), 0.5), None, 2600), 0.02, 0.7)), 0.26,
            (0.7, 0.2))
        add(f"break_gem{i}", mix((grains(0.2, 300, 2400, 160, 0.07, 40 + i), 0, 0.6),
                                 (bandpass(bell(note(PENTA[8 + i]), 0.9, 0.5), None, 3000), 0.02, 0.8),
                                 (bandpass(bell(note(PENTA[10 + i]), 0.9, 0.4), None, 3000), 0.07, 0.5)), 0.28,
            (1.0, 0.25))
    return L


def crash_sweep(duration=50.0, growth=0.12):
    """Tono continuo cuyo pitch sigue al multiplicador de Crash: f = 170·m^0.6 (saturado)."""
    t = _t(duration)
    m = np.exp(growth * t)
    f = 170 * m ** 0.6
    f = 1400 * np.tanh(f / 1400)
    ph = np.cumsum(2 * np.pi * f / SR)
    trem = 1 + 0.10 * np.sin(2 * np.pi * (3 + t * 0.15) * t)
    x = (np.sin(ph) + 0.18 * np.sin(2 * ph) + 0.25 * np.sin(0.5 * ph)) * trem
    x *= np.minimum(1, t / 0.3)
    # un poco más suave en los agudos
    x *= 1 / (1 + (f / 1200) ** 2) ** 0.5
    return x


def lofi_loop():
    """Bucle ambiental suave (opcional): acordes de piano eléctrico, bajo y escobillas."""
    bpm = 78
    beat = 60 / bpm
    bars = 8
    total = beat * 4 * bars
    n = int(SR * total)
    out = np.zeros(n + SR * 3)
    prog = [(-3, [0, 3, 7, 10]), (2, [0, 3, 7, 10]), (-5, [0, 4, 7, 11]), (0, [0, 4, 7, 11])]  # Am7 Dm7 G7 Cmaj7
    for bar in range(bars):
        root, chord = prog[bar % 4]
        t0 = bar * 4 * beat
        for k, s in enumerate(chord):
            f = note(root + s - 12)
            ep = partials(f, beat * 4, [(1, 0.5, 1.6), (2, 0.12, 0.6), (3, 0.04, 0.3)], attack_ms=15)
            i = int(SR * (t0 + k * 0.012))
            out[i:i + len(ep)] += ep * 0.22
        for b in (0, 2.5):
            bass = partials(note(root - 24), beat * 1.4, [(1, 1, 0.5), (2, 0.2, 0.2)], attack_ms=10)
            i = int(SR * (t0 + b * beat))
            out[i:i + len(bass)] += bass * 0.35
        for b in range(8):
            hh = bandpass(noise(0.08), 5000, 12000) * env(int(SR * 0.08), 0.002, 0.02)
            i = int(SR * (t0 + b * beat / 2 + (0.03 if b % 2 else 0)))
            out[i:i + len(hh)] += hh * (0.05 if b % 2 else 0.035)
        for b in (0, 2):
            kick = sweep(110, 45, 0.18, decay=0.08)
            i = int(SR * (t0 + b * beat))
            out[i:i + len(kick)] += kick * 0.35
    out[:SR * 3] += out[n:n + SR * 3]  # cola cíclica
    out = out[:n]
    return bandpass(out, hi=6000)


def to_sound(data, vol):
    if isinstance(data, tuple):
        left, right = data
    else:
        left = right = data
    peak = max(np.max(np.abs(left)), np.max(np.abs(right)), 1e-9)
    k = vol * 0.95 / peak * 32767
    arr = np.empty((len(left), 2), dtype=np.int16)
    arr[:, 0] = np.clip(left * k, -32767, 32767)
    arr[:, 1] = np.clip(right * k, -32767, 32767)
    return pygame.sndarray.make_sound(arr)


# ----------------------------------------------------------------------------
# Gestor de audio
# ----------------------------------------------------------------------------
class Audio:
    def __init__(self, settings):
        self.settings = settings
        self.sounds = {}
        self.ready = False
        self.enabled = False
        self._last = {}
        self.loop_ch = None
        self.music_ch = None
        self.music = None
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(SR, -16, 2, 512)
            pygame.mixer.set_num_channels(48)
            pygame.mixer.set_reserved(2)
            self.loop_ch = pygame.mixer.Channel(0)
            self.music_ch = pygame.mixer.Channel(1)
            self.enabled = True
        except pygame.error:
            return
        threading.Thread(target=self._build, daemon=True).start()

    def _build(self):
        try:
            lib = build_library()
            for name, (data, vol) in lib.items():
                self.sounds[name] = to_sound(data, vol)
            self.sounds["crash_sweep"] = to_sound(crash_sweep(), 0.20)
            self.ready = True
            if self.settings.get("music_on"):
                self._ensure_music()
                self.apply_music()
        except Exception as e:  # el juego funciona aunque falle el audio
            print("Audio desactivado:", e)

    def _ensure_music(self):
        if self.music is None:
            self.music = to_sound(lofi_loop(), 0.5)

    def sfx_volume(self):
        s = self.settings
        if s.get("muted"):
            return 0.0
        return s.get("master", 0.8) * s.get("sfx", 0.8)

    def play(self, name, vol=1.0, pan=0.0, throttle=0.025):
        if not self.ready:
            return
        snd = self.sounds.get(name)
        if snd is None:
            return
        now = time.time()
        if now - self._last.get(name, 0) < throttle:
            return
        self._last[name] = now
        v = self.sfx_volume() * vol
        if v <= 0.001:
            return
        ch = snd.play()
        if ch:
            pan = max(-1.0, min(1.0, pan))
            ch.set_volume(v * min(1, 1 - pan), v * min(1, 1 + pan))

    def play_loop(self, name, vol=1.0):
        if not self.ready or name not in self.sounds:
            return
        self.loop_ch.play(self.sounds[name])
        self.loop_ch.set_volume(self.sfx_volume() * vol)

    def stop_loop(self, fade_ms=150):
        if self.loop_ch:
            self.loop_ch.fadeout(fade_ms)

    def apply_music(self):
        if not self.enabled:
            return
        s = self.settings
        on = s.get("music_on") and not s.get("muted")
        if on:
            if not self.ready:
                return
            self._ensure_music()
            if not self.music_ch.get_busy():
                self.music_ch.play(self.music, loops=-1, fade_ms=1500)
            self.music_ch.set_volume(s.get("master", 0.8) * s.get("music", 0.5) * 0.6)
        else:
            self.music_ch.fadeout(600)

    def set_music(self, on):
        self.settings["music_on"] = on
        if on and self.ready and self.music is None:
            threading.Thread(target=lambda: (self._ensure_music(), self.apply_music()), daemon=True).start()
        else:
            self.apply_music()
