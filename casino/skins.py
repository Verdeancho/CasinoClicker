"""Aspectos desbloqueables: monedas del clicker, tapetes con marco temático y la moneda de Cara o Cruz.

Todo se dibuja por código en un lienzo grande y luego se pixeliza, con el mismo estilo que el resto del juego."""
import math
import random

import numpy as np
import pygame

from . import gfx
from .data import THEME_BY_ID

_cache = {}


def _c(key, fn):
    s = _cache.get(key)
    if s is None:
        s = fn()
        _cache[key] = s
    return s


class Canvas:
    """Lienzo de dibujo con coordenadas en un espacio de 240x240 (como icons.Pen) pero a la resolución pedida."""

    def __init__(self, size=480, w=None, h=None):
        self.w = w or size
        self.h = h or size
        self.k = self.w / 240.0
        self.s = pygame.Surface((self.w, self.h), pygame.SRCALPHA)

    def P(self, p):
        return (int(p[0] * self.k), int(p[1] * self.k))

    def circle(self, c, r, col, w=0):
        pygame.draw.circle(self.s, col, self.P(c), max(1, int(r * self.k)), int(w * self.k) if w else 0)

    def ellipse(self, rect, col, w=0):
        x, y, ww, hh = rect
        pygame.draw.ellipse(self.s, col, pygame.Rect(x * self.k, y * self.k, ww * self.k, hh * self.k),
                            int(w * self.k) if w else 0)

    def poly(self, pts, col, w=0):
        pygame.draw.polygon(self.s, col, [self.P(p) for p in pts], int(w * self.k) if w else 0)

    def rect(self, r, col, rad=0, w=0):
        x, y, ww, hh = r
        pygame.draw.rect(self.s, col, pygame.Rect(x * self.k, y * self.k, ww * self.k, hh * self.k),
                         int(w * self.k) if w else 0, border_radius=int(rad * self.k))

    def line(self, a, b, col, w=4):
        pygame.draw.line(self.s, col, self.P(a), self.P(b), max(1, int(w * self.k)))
        self.circle(a, w / 2, col)
        self.circle(b, w / 2, col)

    def arc(self, c, r, a0, a1, col, w=4):
        rr = pygame.Rect(0, 0, 2 * r * self.k, 2 * r * self.k)
        rr.center = self.P(c)
        pygame.draw.arc(self.s, col, rr, a0, a1, max(1, int(w * self.k)))

    def text(self, t, size, col, center):
        from . import pixfont
        sc = max(1, int(size * self.k / 11))
        img = pixfont.render(t, col, sc, True)
        self.s.blit(img, img.get_rect(center=self.P(center)))

    def glyph(self, ch, scale, col, center):
        from . import pixfont
        img = pixfont.render(ch, col, max(1, int(scale * self.k)), True)
        self.s.blit(img, img.get_rect(center=self.P(center)))
        return img


C = 120


def _ring_ticks(cv, r0, r1, n, col, width=0.16, offset=0.0):
    for i in range(n):
        a = i * math.tau / n + offset
        cv.poly([(C + r1 * math.cos(a - width), C + r1 * math.sin(a - width)),
                 (C + r1 * math.cos(a + width), C + r1 * math.sin(a + width)),
                 (C + r0 * math.cos(a + width * 1.15), C + r0 * math.sin(a + width * 1.15)),
                 (C + r0 * math.cos(a - width * 1.15), C + r0 * math.sin(a - width * 1.15))], col)


def _coin_base(cv, rim, face, dark, light=None):
    light = light or gfx.mul_col(face, 1.2)
    cv.circle((C, C + 6), 112, gfx.mul_col(dark, 0.55))
    cv.circle((C, C), 112, dark)
    cv.circle((C, C), 106, rim)
    cv.circle((C, C), 92, dark)
    cv.circle((C, C), 88, face)
    cv.arc((C, C), 100, math.radians(25), math.radians(155), light, 5)


def _diamond(cv, c, r, col, hi=(255, 255, 255)):
    x, y = c
    cv.poly([(x, y - r), (x + r * 0.75, y), (x, y + r), (x - r * 0.75, y)], col)
    cv.poly([(x, y - r * 0.6), (x + r * 0.3, y - r * 0.1), (x - r * 0.2, y)], hi)


def _gem(cv, c, r, col):
    dk = gfx.mul_col(col, 0.55)
    x, y = c
    cv.poly([(x, y - r), (x + r, y), (x, y + r), (x - r, y)], dk)
    cv.poly([(x, y - r * 0.82), (x + r * 0.82, y), (x, y + r * 0.82), (x - r * 0.82, y)], col)
    cv.poly([(x, y - r * 0.82), (x + r * 0.4, y - r * 0.1), (x - r * 0.4, y - r * 0.1)], gfx.mul_col(col, 1.35))


def _suit(cv, ch, scale, col, c):
    cv.glyph(ch, scale, col, c)


# ---------------------------------------------------------------- monedas
def _skin_cobre(cv):
    face, dark, rim = (190, 104, 66), (110, 52, 32), (214, 128, 84)
    _coin_base(cv, rim, face, dark)
    _ring_ticks(cv, 92, 106, 8, (240, 170, 120), 0.18)
    cv.circle((C, C), 64, dark)
    cv.circle((C, C), 58, (206, 120, 80))
    _ring_ticks(cv, 34, 56, 12, (150, 74, 46), 0.12)
    cv.circle((C, C), 32, dark)
    cv.circle((C, C), 27, (224, 142, 96))
    cv.arc((C, C), 22, math.radians(40), math.radians(150), (250, 190, 150), 4)


def _skin_bronce(cv):
    face, dark, rim = (156, 104, 56), (84, 52, 24), (196, 138, 76)
    _coin_base(cv, rim, face, dark)
    leaf = (226, 176, 96)
    leaf_dk = (110, 70, 30)
    for side in (-1, 1):
        for i in range(7):
            a = math.radians(115 + i * 20)
            x = C + side * 70 * -math.cos(a)
            y = C + 70 * math.sin(a) * -1 + 10
            cv.ellipse((x - 9, y - 5, 18, 10), leaf_dk)
            cv.ellipse((x - 8, y - 5, 16, 8), leaf)
    cv.rect((C - 38, C - 38, 76, 76), dark, 10)
    cv.rect((C - 34, C - 34, 68, 68), (214, 162, 92), 9)
    for px, py in ((-18, -18), (18, -18), (0, 0), (-18, 18), (18, 18)):
        cv.circle((C + px, C + py), 7, (90, 56, 26))


def _skin_plata(cv):
    face, dark, rim = (196, 202, 210), (100, 108, 120), (226, 230, 236)
    _coin_base(cv, rim, face, dark)
    for a in (45, 135, 225, 315):
        x, y = C + 70 * math.cos(math.radians(a)), C + 70 * math.sin(math.radians(a))
        cv.poly([(x, y - 9), (x + 3, y - 3), (x + 9, y), (x + 3, y + 3), (x, y + 9), (x - 3, y + 3), (x - 9, y),
                 (x - 3, y - 3)], (250, 252, 255))
    cv.rect((C - 32, C - 44, 64, 88), (60, 64, 76), 8)
    cv.rect((C - 29, C - 41, 58, 82), (246, 246, 242), 7)
    cv.text("A", 16, (30, 34, 44), (C - 18, C - 28))
    _suit(cv, "♠", 4.0, (30, 34, 44), (C, C + 4))


def _skin_oro(cv):
    face, dark, rim = (236, 168, 44), (140, 84, 14), (250, 206, 90)
    _coin_base(cv, rim, face, dark)
    for i in range(24):
        a = i * math.tau / 24
        cv.circle((C + 98 * math.cos(a), C + 98 * math.sin(a)), 2.6, (255, 236, 150))
    for a in (0, 90, 180, 270):
        x, y = C + 80 * math.cos(math.radians(a)), C + 80 * math.sin(math.radians(a))
        _diamond(cv, (x, y), 8, (255, 230, 120), (255, 255, 220))
    cv.circle((C, C), 58, dark)
    cv.circle((C, C), 54, (90, 50, 20))
    for i in range(18):
        a0 = i * math.tau / 18
        col = (40, 30, 24) if i % 2 else (240, 220, 180)
        cv.poly([(C, C), (C + 52 * math.cos(a0), C + 52 * math.sin(a0)),
                 (C + 52 * math.cos(a0 + math.tau / 18), C + 52 * math.sin(a0 + math.tau / 18))], col)
    cv.circle((C, C), 34, (214, 150, 40))
    cv.circle((C, C), 10, (255, 220, 110))
    for a in (0, 90, 180, 270):
        cv.line((C, C), (C + 26 * math.cos(math.radians(a)), C + 26 * math.sin(math.radians(a))), (255, 214, 100), 5)
    cv.circle((C + 40, C - 30), 6, (250, 250, 250))


def _skin_acero(cv):
    face, dark, rim = (150, 166, 178), (64, 76, 88), (196, 208, 216)
    _coin_base(cv, rim, face, dark)
    for a in (0, 90, 180, 270):
        x, y = C + 96 * math.cos(math.radians(a)), C + 96 * math.sin(math.radians(a))
        _gem(cv, (x, y), 11, (90, 220, 255))
    cv.rect((C - 56, C - 34, 112, 70), (70, 80, 92), 10)
    cv.rect((C - 52, C - 30, 104, 62), (210, 220, 228), 8)
    for i in range(3):
        x = C - 34 + i * 34
        cv.rect((x - 14, C - 22, 28, 46), (30, 40, 56), 4)
        cv.text("7", 22, (90, 220, 255), (x, C + 1))
    cv.rect((C - 30, C - 48, 60, 14), (90, 220, 255), 5)
    cv.line((C + 62, C - 20), (C + 62, C + 14), (110, 120, 130), 6)
    cv.circle((C + 62, C - 24), 7, (90, 220, 255))


def _skin_diamante(cv):
    face, dark, rim = (186, 196, 208), (84, 96, 114), (226, 232, 240)
    _coin_base(cv, rim, face, dark)
    for a in (0, 90, 180, 270):
        x, y = C + 96 * math.cos(math.radians(a)), C + 96 * math.sin(math.radians(a))
        _gem(cv, (x, y), 12, (100, 200, 255))
    hat = (120, 210, 255)
    hat_dk = (40, 120, 200)
    cv.poly([(C - 60, C + 22), (C - 70, C - 34), (C - 26, C - 4), (C, C - 50), (C + 26, C - 4), (C + 70, C - 34),
             (C + 60, C + 22)], hat_dk)
    cv.poly([(C - 54, C + 16), (C - 62, C - 26), (C - 24, C + 2), (C, C - 40), (C + 24, C + 2), (C + 62, C - 26),
             (C + 54, C + 16)], hat)
    cv.poly([(C, C - 40), (C + 24, C + 2), (C, C + 10), (C - 24, C + 2)], (190, 240, 255))
    for x, y in ((C - 70, C - 34), (C, C - 50), (C + 70, C - 34)):
        cv.circle((x, y), 8, (230, 248, 255))
    cv.rect((C - 60, C + 18, 120, 22), hat_dk, 6)
    cv.rect((C - 56, C + 20, 112, 16), (150, 226, 255), 5)
    for i in range(5):
        _diamond(cv, (C - 40 + i * 20, C + 28), 6, (60, 150, 230), (220, 245, 255))


def _skin_cripto(cv):
    face, dark, rim = (240, 164, 40), (150, 86, 10), (252, 204, 90)
    _coin_base(cv, rim, face, dark)
    trace = (200, 120, 20)
    for i in range(10):
        a = i * math.tau / 10 + 0.2
        r0, r1 = 52, 84
        cv.line((C + r0 * math.cos(a), C + r0 * math.sin(a)), (C + r1 * math.cos(a), C + r1 * math.sin(a)), trace, 3)
        cv.circle((C + r1 * math.cos(a), C + r1 * math.sin(a)), 4, (255, 220, 120))
    for a in (45, 135, 225, 315):
        x, y = C + 98 * math.cos(math.radians(a)), C + 98 * math.sin(math.radians(a))
        cv.rect((x - 6, y - 6, 12, 12), (255, 226, 130), 2)
    col = (255, 236, 160)
    sh = (170, 96, 10)
    for dx, dy, cc in ((4, 5, sh), (0, 0, col)):
        cv.rect((C - 26 + dx, C - 42 + dy, 14, 84), cc)
        cv.rect((C - 26 + dx, C - 42 + dy, 46, 14), cc, 7)
        cv.rect((C - 26 + dx, C - 7 + dy, 50, 14), cc, 7)
        cv.rect((C - 26 + dx, C + 28 + dy, 50, 14), cc, 7)
        cv.rect((C + 12 + dx, C - 42 + dy, 14, 42), cc, 7)
        cv.rect((C + 16 + dx, C - 4 + dy, 14, 44), cc, 7)
        cv.rect((C - 16 + dx, C - 54 + dy, 8, 12), cc)
        cv.rect((C + 2 + dx, C - 54 + dy, 8, 12), cc)
        cv.rect((C - 16 + dx, C + 40 + dy, 8, 12), cc)
        cv.rect((C + 2 + dx, C + 40 + dy, 8, 12), cc)


def _skin_neon(cv):
    face, dark, rim = (46, 26, 70), (20, 10, 34), (110, 76, 140)
    _coin_base(cv, rim, face, dark, light=(160, 120, 200))
    glow = (230, 80, 255)
    for a in (0, 90, 180, 270):
        x, y = C + 96 * math.cos(math.radians(a)), C + 96 * math.sin(math.radians(a))
        _gem(cv, (x, y), 10, (240, 110, 255))
    for i in range(16):
        a = i * math.tau / 16
        if i % 2:
            cv.arc((C, C), 82, a, a + 0.25, (200, 70, 240), 4)
    cv.circle((C, C), 70, (36, 16, 56))
    random.seed(7)
    for _ in range(5):
        a = random.uniform(0, math.tau)
        pts = [(C + 20 * math.cos(a), C + 20 * math.sin(a))]
        for j in range(4):
            a += random.uniform(-0.6, 0.6)
            r = 24 + j * 12
            pts.append((C + r * math.cos(a), C + r * math.sin(a)))
        for p0, p1 in zip(pts, pts[1:]):
            cv.line(p0, p1, (150, 60, 200), 2)
    for w, col in ((22, (120, 30, 170)), (14, glow), (6, (255, 210, 255))):
        cv.line((C - 32, C - 40), (C + 32, C - 40), col, w)
        cv.line((C + 32, C - 40), (C - 6, C + 46), col, w)


def _skin_cosmico(cv):
    face, dark, rim = (16, 22, 52), (40, 48, 70), (80, 92, 120)
    _coin_base(cv, rim, face, dark, light=(120, 140, 180))
    for a in range(0, 360, 45):
        x, y = C + 99 * math.cos(math.radians(a)), C + 99 * math.sin(math.radians(a))
        cv.rect((x - 5, y - 9, 10, 18), (80, 200, 255) if a % 90 == 0 else (230, 90, 255), 3)
    random.seed(3)
    for _ in range(26):
        a, r = random.uniform(0, math.tau), random.uniform(0, 80)
        cv.circle((C + r * math.cos(a), C + r * math.sin(a)), random.choice((1.2, 1.8)), (220, 230, 255))
    cv.ellipse((C - 70, C - 22, 140, 44), (80, 170, 255), 3)
    cv.ellipse((C - 22, C - 70, 44, 140), (220, 100, 255), 3)
    for ch, col, (dx, dy) in (("♠", (110, 210, 255), (-24, -24)), ("♥", (255, 100, 220), (24, -24)),
                              ("♣", (200, 120, 255), (-24, 24)), ("♦", (110, 230, 255), (24, 24))):
        _suit(cv, ch, 3.6, col, (C + dx, C + dy))


SKIN_DRAW = {"cobre": _skin_cobre, "bronce": _skin_bronce, "plata": _skin_plata, "oro": _skin_oro,
             "acero": _skin_acero, "diamante": _skin_diamante, "cripto": _skin_cripto, "neon": _skin_neon,
             "cosmico": _skin_cosmico}


def coin_skin(tid, size, boost=False):
    """Moneda grande del clicker con el aspecto `tid`."""
    if tid not in SKIN_DRAW:
        from .art import big_coin
        return big_coin(size, boost)

    def build():
        cv = Canvas(480)
        SKIN_DRAW[tid](cv)
        lay = pygame.Surface((480, 480), pygame.SRCALPHA)
        pygame.draw.ellipse(lay, (255, 255, 255, 60), (90, 70, 200, 100))
        cv.s.blit(lay, (0, 0))
        img = gfx.pixelize(pygame.transform.smoothscale(cv.s, (size, size)), (size, size), 2)
        if boost:
            img = img.copy()
            img.fill((60, 20, 10, 0), special_flags=pygame.BLEND_RGBA_ADD)
        return img
    return _c(("skin", tid, size, boost), build)


def skin_icon(tid, size):
    return coin_skin(tid, size) if tid in SKIN_DRAW else __import__("casino.art", fromlist=["big_coin"]).big_coin(size)


# ---------------------------------------------------------------- Cara o Cruz
def flip_face(side, size):
    """Caras de la moneda de Cara o Cruz: CARA dorada con corona, CRUZ plateada con una cruz."""
    def build():
        cv = Canvas(480)
        if side == 0:
            face, dark, rim = (244, 190, 60), (150, 92, 14), (255, 222, 120)
            _coin_base(cv, rim, face, dark)
            for i in range(28):
                a = i * math.tau / 28
                cv.circle((C + 97 * math.cos(a), C + 97 * math.sin(a)), 2.4, (255, 240, 170))
            sh = (170, 104, 14)
            for dx, dy, col in ((4, 6, sh), (0, 0, (255, 244, 190))):
                pts = [(C - 52, C + 26), (C - 58, C - 30), (C - 28, C - 4), (C, C - 50), (C + 28, C - 4),
                       (C + 58, C - 30), (C + 52, C + 26)]
                cv.poly([(x + dx, y + dy) for x, y in pts], col)
                cv.rect((C - 54 + dx, C + 24 + dy, 108, 18), col, 4)
            for x, y, col in ((C - 58, C - 30, (220, 60, 70)), (C, C - 50, (70, 140, 230)),
                              (C + 58, C - 30, (220, 60, 70))):
                cv.circle((x, y), 8, col)
            for i in range(3):
                cv.circle((C - 30 + i * 30, C + 33), 5, (220, 60, 70) if i != 1 else (70, 140, 230))
        else:
            face, dark, rim = (200, 208, 222), (96, 106, 126), (232, 236, 244)
            _coin_base(cv, rim, face, dark)
            for i in range(28):
                a = i * math.tau / 28
                cv.circle((C + 97 * math.cos(a), C + 97 * math.sin(a)), 2.4, (246, 248, 255))
            sh = (110, 120, 140)
            for dx, dy, col in ((4, 6, sh), (0, 0, (250, 252, 255))):
                L, T = 46, 14
                cv.poly([(C - T + dx, C - L + dy), (C + T + dx, C - L + dy), (C + T * 0.6 + dx, C - T + dy),
                         (C + L + dx, C - T + dy), (C + L + dx, C + T + dy), (C + T * 0.6 + dx, C + T + dy),
                         (C + T + dx, C + L + dy), (C - T + dx, C + L + dy), (C - T * 0.6 + dx, C + T + dy),
                         (C - L + dx, C + T + dy), (C - L + dx, C - T + dy), (C - T * 0.6 + dx, C - T + dy)], col)
            cv.circle((C, C), 12, (90, 150, 230))
        lay = pygame.Surface((480, 480), pygame.SRCALPHA)
        pygame.draw.ellipse(lay, (255, 255, 255, 55), (90, 70, 200, 100))
        cv.s.blit(lay, (0, 0))
        return gfx.pixelize(pygame.transform.smoothscale(cv.s, (size, size)), (size, size), 2)
    return _c(("flip", side, size), build)


def flip_edge_col(side):
    return (150, 92, 14) if side == 0 else (96, 106, 126)


# ---------------------------------------------------------------- tapetes
FELT_STYLE = {
    # marco (material), luz del marco, sombra del marco, filete interior, adorno de esquina
    "clasico": ((120, 74, 44), (170, 112, 70), (70, 40, 22), (214, 170, 90), "chip"),
    "cobre": ((150, 80, 52), (204, 128, 88), (84, 40, 26), (226, 150, 100), "chip"),
    "bronce": ((140, 100, 52), (200, 152, 84), (76, 50, 22), (226, 182, 100), "dice"),
    "plata": ((150, 158, 170), (214, 220, 230), (78, 84, 98), (226, 232, 240), "spade"),
    "oro": ((200, 140, 34), (252, 206, 96), (110, 70, 10), (255, 220, 120), "wheel"),
    "acero": ((120, 134, 146), (190, 204, 214), (56, 64, 76), (100, 220, 255), "gem"),
    "diamante": ((150, 164, 184), (220, 230, 242), (70, 80, 100), (120, 210, 255), "joker"),
    "cripto": ((196, 132, 30), (250, 196, 80), (100, 64, 10), (240, 170, 50), "btc"),
    "neon": ((70, 40, 96), (140, 90, 180), (30, 14, 44), (230, 80, 255), "seven"),
    "cosmico": ((44, 56, 92), (90, 110, 160), (18, 22, 42), (80, 180, 255), "suits"),
}


def _texture(arr, col, seed, starry=False):
    h, w = arr.shape[1], arr.shape[0]
    rng = np.random.default_rng(seed)
    noise = rng.random((w, h))
    base = np.array(col, np.float32)
    shade = 1.0 + (noise - 0.5) * 0.10
    xx, yy = np.mgrid[0:w, 0:h]
    cx, cy = w / 2, h / 2
    vign = 1.0 - 0.18 * (((xx - cx) / cx) ** 2 + ((yy - cy) / cy) ** 2) / 2
    out = base[None, None, :] * (shade * vign)[..., None]
    if starry:
        stars = rng.random((w, h)) > 0.992
        out[stars] = (210, 220, 255)
    arr[:] = np.clip(out, 0, 255).astype(np.uint8)


def _ornament(s, kind, c, r, col, light, dark):
    x, y = c
    if kind == "chip":
        pygame.draw.circle(s, dark, (x, y + 1), r)
        pygame.draw.circle(s, (232, 228, 220), (x, y), r)
        for i in range(6):
            a = i * math.tau / 6
            pygame.draw.circle(s, (196, 50, 54), (int(x + (r - 2) * math.cos(a)), int(y + (r - 2) * math.sin(a))), 2)
        pygame.draw.circle(s, (40, 110, 80), (x, y), max(2, r - 4))
        pygame.draw.circle(s, (232, 228, 220), (x, y), max(1, r - 4), 1)
    elif kind == "dice":
        rr = pygame.Rect(0, 0, r * 2, r * 2)
        rr.center = c
        pygame.draw.rect(s, dark, rr.move(0, 1), border_radius=2)
        pygame.draw.rect(s, (236, 200, 120), rr, border_radius=2)
        for dx, dy in ((-1, -1), (1, -1), (0, 0), (-1, 1), (1, 1)):
            s.fill((90, 56, 24), (x + dx * (r // 2) - 1, y + dy * (r // 2) - 1, 2, 2))
    elif kind == "spade":
        pygame.draw.circle(s, dark, (x, y + 1), r + 1)
        pygame.draw.circle(s, light, (x, y), r + 1)
        pygame.draw.circle(s, (40, 46, 60), (x, y), r - 1)
        from . import pixfont
        g = pixfont.render("♠", light, 1)
        s.blit(g, g.get_rect(center=(x + 1, y + 1)))
    elif kind == "wheel":
        pygame.draw.circle(s, dark, (x, y + 1), r + 1)
        pygame.draw.circle(s, (240, 200, 90), (x, y), r + 1)
        for i in range(8):
            a = i * math.tau / 8
            pygame.draw.line(s, (40, 26, 20) if i % 2 else (190, 40, 40), (x, y),
                             (int(x + r * math.cos(a)), int(y + r * math.sin(a))), 2)
        pygame.draw.circle(s, (250, 220, 120), (x, y), max(1, r // 3))
    elif kind in ("gem", "joker"):
        gc = (100, 220, 255) if kind == "gem" else (110, 190, 255)
        pygame.draw.polygon(s, gfx.mul_col(gc, 0.5), [(x, y - r - 1), (x + r + 1, y), (x, y + r + 1), (x - r - 1, y)])
        pygame.draw.polygon(s, gc, [(x, y - r), (x + r, y), (x, y + r), (x - r, y)])
        pygame.draw.polygon(s, (230, 250, 255), [(x, y - r), (x + r // 2, y - 1), (x - r // 2, y - 1)])
    elif kind == "btc":
        pygame.draw.circle(s, dark, (x, y + 1), r + 1)
        pygame.draw.circle(s, (250, 196, 80), (x, y), r + 1)
        pygame.draw.circle(s, (200, 130, 20), (x, y), r - 1, 1)
        from . import pixfont
        g = pixfont.render("B", (120, 70, 10), 1, True)
        s.blit(g, g.get_rect(center=(x + 1, y + 1)))
    elif kind == "seven":
        rr = pygame.Rect(0, 0, r * 2 + 2, r * 2 + 2)
        rr.center = c
        pygame.draw.rect(s, (40, 18, 56), rr, border_radius=3)
        pygame.draw.rect(s, (200, 80, 240), rr, 1, border_radius=3)
        from . import pixfont
        g = pixfont.render("7", (250, 140, 255), 1, True)
        s.blit(g, g.get_rect(center=(x + 1, y + 1)))
    elif kind == "suits":
        pygame.draw.circle(s, dark, (x, y + 1), r + 1)
        pygame.draw.circle(s, (30, 40, 80), (x, y), r + 1)
        pygame.draw.circle(s, (80, 180, 255), (x, y), r + 1, 1)
        from . import pixfont
        g = pixfont.render(random.choice("♠♥♣♦"), (150, 210, 255), 1)
        s.blit(g, g.get_rect(center=(x + 1, y + 1)))


def felt_surf(w, h, col, theme="clasico", r=18):
    """Tapete con marco: textura de fieltro, borde del material del tema, filete y adornos en las esquinas."""
    key = ("felt", w, h, col, theme, r)
    s = _cache.get(key)
    if s is not None:
        return s
    style = FELT_STYLE.get(theme, FELT_STYLE["clasico"])
    frame, light, dark, fil, orn = style
    if theme != "clasico":
        col = THEME_BY_ID[theme][4]
    k = 2
    sw, sh = max(8, w // k), max(8, h // k)
    small = pygame.Surface((sw, sh), pygame.SRCALPHA)
    rr = max(3, r // k)
    fw = 7                                      # grosor del marco (en píxeles pequeños)
    pygame.draw.rect(small, (*dark, 255), (0, 0, sw, sh), border_radius=rr)
    pygame.draw.rect(small, (*frame, 255), (0, 0, sw, sh - 1), border_radius=rr)
    pygame.draw.rect(small, (*light, 255), (1, 1, sw - 2, sh - 3), 1, border_radius=rr)
    inner = pygame.Rect(fw, fw, sw - fw * 2, sh - fw * 2)
    pygame.draw.rect(small, (*dark, 255), inner.inflate(2, 2), border_radius=max(2, rr - 3))
    cloth = pygame.Surface(inner.size)
    arr = pygame.surfarray.pixels3d(cloth)
    _texture(arr, col, hash((w, h, theme)) % 1000, starry=theme == "cosmico")
    del arr
    mask = pygame.Surface(inner.size, pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, *inner.size), border_radius=max(2, rr - 3))
    cl = pygame.Surface(inner.size, pygame.SRCALPHA)
    cl.blit(cloth, (0, 0))
    cl.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    small.blit(cl, inner.topleft)
    # sombra interior arriba
    sh_l = pygame.Surface((inner.w, 3), pygame.SRCALPHA)
    sh_l.fill((0, 0, 0, 60))
    small.blit(sh_l, inner.topleft)
    # filete interior
    fil_r = inner.inflate(-8, -8)
    pygame.draw.rect(small, (*fil, 150), fil_r, 1, border_radius=max(2, rr - 5))
    # marcas a mitad de cada lado
    for (mx, my) in ((sw // 2, fw // 2), (sw // 2, sh - fw // 2 - 1), (fw // 2, sh // 2), (sw - fw // 2 - 1, sh // 2)):
        pygame.draw.polygon(small, (*fil, 255), [(mx, my - 2), (mx + 2, my), (mx, my + 2), (mx - 2, my)])
    # adornos de esquina
    random.seed(len(theme))
    orr = 6 if min(sw, sh) > 90 else 4
    for (cx, cy) in ((fw - 1, fw - 1), (sw - fw, fw - 1), (fw - 1, sh - fw), (sw - fw, sh - fw)):
        _ornament(small, orn, (cx, cy), orr, frame, light, dark)
    s = pygame.transform.scale(small, (sw * k, sh * k))
    if s.get_size() != (w, h):
        out = pygame.Surface((w, h), pygame.SRCALPHA)
        out.blit(s, (0, 0))
        s = out
    _cache[key] = s
    return s
