"""Sprites pre-renderizados con supermuestreo: moneda, cartas, fichas, símbolos, gemas, cohete, caballos."""
import math

import pygame

from . import gfx
from .icons import Pen, S, C, gem as draw_gem

_cache = {}


def _c(key, fn):
    s = _cache.get(key)
    if s is None:
        s = fn()
        _cache[key] = s
    return s


def _down(big, w, h=None):
    return pygame.transform.smoothscale(big, (int(w), int(h if h else w)))


# ----------------------------------------------------------------------------
# Moneda principal
# ----------------------------------------------------------------------------
def big_coin(size, frenzy=False):
    def build():
        k = 3
        D = size * k
        s = pygame.Surface((D, D), pygame.SRCALPHA)
        c = D / 2
        R = D / 2 - 2
        if frenzy:
            light, mid, dark, deep = (255, 190, 190), (255, 110, 120), (200, 50, 70), (120, 20, 40)
        else:
            light, mid, dark, deep = (255, 246, 190), (255, 204, 72), (214, 140, 26), (128, 76, 8)
        # canto (bisel)
        for i in range(30):
            t = i / 29
            r = R * (1 - 0.1 * t)
            col = gfx.lerp_col(deep, dark, t)
            pygame.draw.circle(s, col, (c, c + R * 0.035 * (1 - t)), r)
        # estriado
        for i in range(120):
            a = i * math.tau / 120
            x1, y1 = c + R * 0.975 * math.cos(a), c + R * 0.975 * math.sin(a)
            x2, y2 = c + R * 0.905 * math.cos(a), c + R * 0.905 * math.sin(a)
            pygame.draw.line(s, gfx.mul_col(dark, 0.78 if i % 2 else 1.08), (x1, y1), (x2, y2), max(2, k * 2))
        # cara con degradado radial suave (numpy)
        face_r = R * 0.88
        import numpy as np
        yy, xx = np.mgrid[0:D, 0:D].astype(np.float32)
        lx, ly = c - face_r * 0.35, c - face_r * 0.45
        d = np.sqrt((xx - lx) ** 2 + (yy - ly) ** 2) / (face_r * 1.55)
        d = np.clip(d, 0, 1)
        stops = [(0.0, light), (0.45, mid), (1.0, dark)]
        rgb = np.zeros((D, D, 3), np.float32)
        for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
            m = (d >= t0) & (d <= t1)
            u = ((d - t0) / (t1 - t0))[m]
            for ch in range(3):
                rgb[..., ch][m] = c0[ch] + (c1[ch] - c0[ch]) * u
        face = pygame.Surface((D, D), pygame.SRCALPHA)
        pygame.surfarray.blit_array(face, rgb.transpose(1, 0, 2).astype(np.uint8))
        alpha = pygame.surfarray.pixels_alpha(face)
        alpha[:] = ((np.sqrt((xx - c) ** 2 + (yy - c) ** 2) <= face_r).T * 255).astype(np.uint8)
        del alpha
        s.blit(face, (0, 0))
        # anillo interior en relieve
        ring = face_r * 0.80
        pygame.draw.circle(s, gfx.mul_col(dark, 0.9), (c, c + k * 2), ring, max(3, k * 3))
        pygame.draw.circle(s, gfx.mul_col(light, 1.0), (c, c - k), ring, max(2, k * 2))
        pygame.draw.circle(s, mid, (c, c), ring - k * 2, max(1, k))
        # símbolo €
        fs = int(face_r * 1.15)
        f = gfx.font(fs, "bl")
        for dx, dy, col in ((k * 3, k * 4, gfx.mul_col(deep, 1.2)), (-k * 2, -k * 2, (255, 255, 235)),
                            (0, 0, gfx.mul_col(mid, 1.02))):
            t = f.render("€", True, col)
            s.blit(t, t.get_rect(center=(c + dx, c + dy + fs * 0.02)))
        # brillo
        lay = pygame.Surface((D, D), pygame.SRCALPHA)
        pygame.draw.ellipse(lay, (255, 255, 255, 70), (c - face_r * 0.75, c - face_r * 0.85, face_r * 1.0, face_r * 0.55))
        s.blit(lay, (0, 0))
        return gfx.pixelize(_down(s, size), (size, size), 2)
    return _c(("bigcoin", size, frenzy), build)


def coin_mask(size):
    def build():
        m = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(m, (255, 255, 255, 255), (size // 2, size // 2), size // 2 - 1)
        return m
    return _c(("cmask", size), build)


def small_coin(size, star=False):
    def build():
        p = Pen()
        from .icons import coin
        coin(p, (C, C), 108, mark="" if star else "€")
        if star:
            p.poly(gfx.star_points(C, C, 56, 23), (255, 250, 220))
        return gfx.pixelize(p.s, (size, size), 1)
    return _c(("scoin", size, star), build)


def coin_frames(size):
    def build():
        base = small_coin(size)
        frames = []
        for i in range(12):
            a = i / 12 * math.pi
            w = max(2, int(size * abs(math.cos(a))))
            img = pygame.transform.scale(base, (w, base.get_height()))
            if w < size * 0.5:
                img = img.copy()
                img.fill((180, 120, 20, 255), special_flags=pygame.BLEND_RGBA_MULT)
            frames.append(img)
        return frames
    return _c(("cframes", size), build)


def golden_coin(size):
    def build():
        p = Pen()
        from .icons import coin
        coin(p, (C, C), 110, face=(255, 236, 140), dark=(230, 160, 30), mark="")
        p.poly(gfx.star_points(C, C + 4, 64, 27), (200, 120, 10))
        p.poly(gfx.star_points(C, C, 64, 27), (255, 255, 235))
        return gfx.pixelize(p.s, (size, size), 2)
    return _c(("gcoin", size), build)


# ----------------------------------------------------------------------------
# Cartas
# ----------------------------------------------------------------------------
SUITS = ["♠", "♥", "♦", "♣"]
RANK_STR = {1: "A", 11: "J", 12: "Q", 13: "K"}
PIPS = {
    2: [(0.5, 0.18), (0.5, 0.82)],
    3: [(0.5, 0.18), (0.5, 0.5), (0.5, 0.82)],
    4: [(0.3, 0.18), (0.7, 0.18), (0.3, 0.82), (0.7, 0.82)],
    5: [(0.3, 0.18), (0.7, 0.18), (0.5, 0.5), (0.3, 0.82), (0.7, 0.82)],
    6: [(0.3, 0.18), (0.7, 0.18), (0.3, 0.5), (0.7, 0.5), (0.3, 0.82), (0.7, 0.82)],
    7: [(0.3, 0.18), (0.7, 0.18), (0.5, 0.34), (0.3, 0.5), (0.7, 0.5), (0.3, 0.82), (0.7, 0.82)],
    8: [(0.3, 0.18), (0.7, 0.18), (0.5, 0.34), (0.3, 0.5), (0.7, 0.5), (0.5, 0.66), (0.3, 0.82), (0.7, 0.82)],
    9: [(0.3, 0.16), (0.7, 0.16), (0.3, 0.39), (0.7, 0.39), (0.5, 0.5), (0.3, 0.61), (0.7, 0.61), (0.3, 0.84),
        (0.7, 0.84)],
    10: [(0.3, 0.16), (0.7, 0.16), (0.5, 0.28), (0.3, 0.39), (0.7, 0.39), (0.3, 0.61), (0.7, 0.61), (0.5, 0.72),
         (0.3, 0.84), (0.7, 0.84)],
}


def rank_str(r):
    return RANK_STR.get(r, str(r))


_SHEET = {}
CARD_W, CARD_H = 312, 440                     # tamaño de cada carta en la hoja original
_SUIT_ROW = {0: 0, 1: 1, 2: 3, 3: 2}          # ♠ ♥ ♦ ♣ -> fila de la hoja (♠ ♥ ♣ ♦)


def _card_sheet():
    if "img" not in _SHEET:
        import os
        path = os.path.join(os.path.dirname(__file__), "assets", "cartas.png")
        img = pygame.image.load(path)
        try:
            img = img.convert_alpha()
        except pygame.error:
            pass
        _SHEET["img"] = img
    return _SHEET["img"]


def _fit(img, w, h):
    """Reduce en dos pasos (suave, como Balatro) para que no se pierdan los detalles."""
    sw, sh = img.get_size()
    while sw > w * 2 and sh > h * 2:
        sw, sh = sw // 2, sh // 2
        img = pygame.transform.smoothscale(img, (sw, sh))
    return pygame.transform.smoothscale(img, (int(w), int(h)))


def card_sprite(card, w=92, h=130):
    """Carta de la baraja ilustrada (assets/cartas.png), escalada al tamaño pedido."""
    rank, suit = card

    def build():
        sheet = _card_sheet()
        col = (rank - 1) * CARD_W
        row = _SUIT_ROW[suit] * CARD_H
        src = sheet.subsurface((col, row, CARD_W, CARD_H))
        return _fit(src, w, h)
    return _c(("card", rank, suit, w, h), build)


def card_back(w=92, h=130):
    """Dorso a juego con la baraja: marco crema, centro granate con rombos y emblema dorado."""
    def build():
        lw, lh = 78, 110                            # misma resolución de píxel que la baraja
        s = pygame.Surface((lw, lh), pygame.SRCALPHA)
        pygame.draw.rect(s, (60, 44, 34), (0, 0, lw, lh), border_radius=5)
        pygame.draw.rect(s, (244, 232, 206), (1, 1, lw - 2, lh - 2), border_radius=4)
        inner = pygame.Rect(5, 5, lw - 10, lh - 10)
        pygame.draw.rect(s, (150, 30, 40), inner, border_radius=3)
        for y in range(inner.y + 1, inner.bottom - 1):
            for x in range(inner.x + 1, inner.right - 1):
                if (x + y) % 6 == 0 or (x - y) % 6 == 0:
                    s.set_at((x, y), (186, 52, 58))
        pygame.draw.rect(s, (226, 180, 90), inner, 1, border_radius=3)
        pygame.draw.rect(s, (226, 180, 90), inner.inflate(-6, -6), 1, border_radius=2)
        cx, cy = lw // 2, lh // 2
        for r, col in ((15, (90, 16, 24)), (13, (226, 180, 90)), (10, (150, 30, 40)), (6, (240, 206, 120))):
            pygame.draw.polygon(s, col, [(cx, cy - r), (cx + r * 0.7, cy), (cx, cy + r), (cx - r * 0.7, cy)])
        big = pygame.transform.scale(s, (lw * 4, lh * 4))
        return _fit(big, w, h)
    return _c(("back", w, h), build)


# ----------------------------------------------------------------------------
# Fichas
# ----------------------------------------------------------------------------
CHIP_COLORS = [(230, 60, 80), (60, 120, 230), (40, 170, 100), (30, 30, 40), (150, 80, 220), (240, 150, 40)]


def chip_color_for(amount):
    import math as m
    if amount <= 0:
        return CHIP_COLORS[0]
    return CHIP_COLORS[int(m.log10(max(amount, 0.01)) + 2) % len(CHIP_COLORS)]


def chip(size, col):
    def build():
        p = Pen()
        dk = gfx.mul_col(col, 0.6)
        p.circle((C, C + 10), 108, gfx.mul_col(col, 0.4))
        p.circle((C, C), 108, col)
        for i in range(8):
            a = i * math.pi / 4
            p.poly([(C + 108 * math.cos(a - 0.16), C + 108 * math.sin(a - 0.16)),
                    (C + 108 * math.cos(a + 0.16), C + 108 * math.sin(a + 0.16)),
                    (C + 80 * math.cos(a + 0.19), C + 80 * math.sin(a + 0.19)),
                    (C + 80 * math.cos(a - 0.19), C + 80 * math.sin(a - 0.19))], (250, 250, 250))
        p.circle((C, C), 74, dk)
        p.circle((C, C), 70, (250, 250, 250), 5)
        p.circle((C, C), 64, gfx.mul_col(col, 0.92))
        p.shine((C - 70, C - 92, 100, 50), 50)
        return gfx.pixelize(p.s, (size, size), 1)
    return _c(("chip", size, col), build)


def chip_with_text(size, amount):
    from .fmt import fmt_num
    key = ("chipt", size, round(amount, 4))

    def build():
        base = chip(size, chip_color_for(amount)).copy()
        txt = fmt_num(amount, 2 if amount < 10 else 0)
        fs = int(size * (0.34 if len(txt) <= 3 else 0.26 if len(txt) <= 5 else 0.22))
        t = gfx.text_surf(txt, fs, "bl", (255, 255, 255))
        base.blit(t, t.get_rect(center=(size // 2, size // 2)))
        return base
    if len(_cache) > 3000:
        _cache.clear()
    return _c(key, build)


# ----------------------------------------------------------------------------
# Símbolos de la tragaperras
# ----------------------------------------------------------------------------
def _sym_cherry(p):
    p.line((80, 150), (128, 44), (60, 140, 60), 10)
    p.line((166, 140), (128, 44), (60, 140, 60), 10)
    p.poly([(128, 44), (190, 26), (166, 66)], (80, 190, 90))
    p.poly([(128, 44), (166, 66), (150, 50)], (50, 140, 60))
    for x, y in ((80, 164), (166, 154)):
        p.circle((x + 3, y + 5), 40, (120, 10, 30))
        p.circle((x, y), 40, (226, 30, 56))
        p.circle((x - 4, y + 4), 34, (200, 20, 46))
        p.shine((x - 26, y - 28, 22, 16), 160)


def _sym_lemon(p):
    pts = [(24, 124), (48, 70), (120, 50), (192, 70), (216, 124), (192, 176), (120, 196), (48, 176)]
    p.poly([(x + 3, y + 6) for x, y in pts], (180, 140, 0))
    p.poly(pts, (255, 220, 50))
    p.ellipse((50, 74, 140, 100), (255, 236, 110))
    p.circle((24, 124), 10, (220, 180, 20))
    p.circle((216, 124), 10, (220, 180, 20))
    p.shine((70, 76, 60, 30), 150)


def _sym_orange(p):
    p.circle((C + 3, C + 10), 86, (190, 90, 0))
    p.circle((C, C + 6), 86, (255, 150, 30))
    p.circle((C - 10, C - 4), 70, (255, 172, 60))
    for (x, y) in ((90, 120), (140, 150), (110, 170), (160, 110), (150, 190), (80, 160)):
        p.circle((x, y), 3, (230, 130, 20))
    p.poly([(C, 40), (C + 50, 18), (C + 36, 52)], (80, 180, 80))
    p.line((C, 44), (C - 4, 28), (110, 80, 40), 7)
    p.shine((70, 60, 60, 36), 150)


def _sym_plum(p):
    pts = [(C, 70), (C - 30, 96), (C + 30, 96), (C - 46, 128), (C, 128), (C + 46, 128), (C - 26, 160),
           (C + 26, 160), (C, 192)]
    for (x, y) in pts:
        p.circle((x + 2, y + 4), 26, (70, 20, 100))
    for (x, y) in pts:
        p.circle((x, y), 26, (150, 60, 210))
        p.circle((x - 2, y - 2), 21, (176, 90, 236))
        p.circle((x - 8, y - 9), 6, (230, 200, 255))
    p.line((C, 52), (C + 8, 26), (110, 80, 40), 8)
    p.poly([(C + 6, 38), (C + 56, 26), (C + 36, 54)], (80, 180, 80))


def _sym_bell(p):
    pts = [(40, 178), (58, 150), (62, 92), (90, 52), (C, 40), (150, 52), (178, 92), (182, 150), (200, 178)]
    p.poly([(x + 3, y + 6) for x, y in pts], (160, 100, 0))
    p.poly(pts, (255, 200, 50))
    p.poly([(C, 40), (150, 52), (178, 92), (182, 150), (200, 178), (C + 10, 178)], (230, 166, 30))
    p.rect((34, 172, 172, 18), (200, 130, 20), 8)
    p.circle((C, 200), 18, (170, 100, 10))
    p.circle((C, 32), 12, (200, 130, 20))
    p.shine((76, 70, 30, 70), 140)


def _sym_bar(p):
    p.rect((22, 74, 196, 92), (20, 20, 26), 18)
    p.rect((22, 74, 196, 92), (240, 240, 250), 18, 6)
    p.rect((34, 86, 172, 68), (40, 40, 50), 12)
    p.text("BAR", 64, (255, 255, 255), (C, C + 2))
    p.shine((40, 84, 160, 24), 50)


def _sym_seven(p):
    p.text("7", 210, (100, 0, 20), (C + 8, C + 14))
    p.text("7", 210, (255, 210, 80), (C + 3, C + 4))
    p.text("7", 200, (232, 30, 50), (C, C))


def _sym_star(p):
    p.poly(gfx.star_points(C + 4, C + 12, 108, 46), (170, 100, 0))
    p.poly(gfx.star_points(C, C + 6, 108, 46), (255, 200, 40))
    p.poly(gfx.star_points(C, C + 6, 70, 30), (255, 232, 120))
    p.poly(gfx.star_points(C, C + 6, 30, 13), (255, 255, 230))


def _sym_wild(p):
    p.rect((14, 64, 212, 112), (110, 60, 230), 26)
    p.rect((14, 64, 212, 112), (255, 130, 200), 26, 8)
    p.rect((26, 76, 188, 88), (140, 90, 250), 18)
    p.text("WILD", 66, (255, 255, 255), (C, C + 2))
    p.shine((30, 76, 180, 30), 60)


SYMBOL_FUNCS = {"cherry": _sym_cherry, "lemon": _sym_lemon, "orange": _sym_orange, "plum": _sym_plum,
                "bell": _sym_bell, "bar": _sym_bar, "seven": _sym_seven, "star": _sym_star, "wild": _sym_wild}


def symbol(name, size):
    def build():
        p = Pen()
        SYMBOL_FUNCS[name](p)
        return gfx.pixelize(p.s, (size, size), 2 if size >= 60 else 1)
    return _c(("sym", name, size), build)


# ----------------------------------------------------------------------------
# Minas, crash
# ----------------------------------------------------------------------------
def gem_sprite(size):
    def build():
        p = Pen()
        draw_gem(p, (C, C + 6), 96)
        return gfx.pixelize(p.s, (size, size), 2)
    return _c(("gem", size), build)


def bomb_sprite(size):
    def build():
        p = Pen()
        p.circle((C + 6, C + 20), 84, (20, 20, 26))
        p.circle((C, C + 14), 84, (50, 50, 64))
        p.circle((C - 10, C + 4), 66, (64, 64, 82))
        p.rect((C + 20, 30, 40, 34), (90, 90, 110), 8)
        p.line((C + 40, 34), (C + 70, 10), (180, 140, 90), 9)
        p.shine((C - 56, C - 44, 50, 30), 100)
        return gfx.pixelize(p.s, (size, size), 2)
    return _c(("bomb", size), build)


def rocket(size):
    def build():
        p = Pen()
        p.poly([(C - 30, 150), (C - 62, 200), (C - 26, 188)], (220, 50, 70))
        p.poly([(C + 30, 150), (C + 62, 200), (C + 26, 188)], (220, 50, 70))
        p.ellipse((C - 36, 20, 72, 190), (236, 238, 248))
        p.ellipse((C - 10, 20, 46, 190), (210, 214, 230))
        p.poly([(C - 30, 60), (C, 14), (C + 30, 60)], (230, 60, 80))
        p.circle((C, 96), 18, (70, 150, 255))
        p.circle((C, 96), 18, (200, 230, 255), 5)
        p.rect((C - 22, 196, 44, 14), (120, 120, 140), 4)
        return gfx.pixelize(p.s, (size, size), 1)
    return _c(("rocket", size), build)


# ----------------------------------------------------------------------------
# Caballos (vista lateral, 6 fotogramas de galope)
# ----------------------------------------------------------------------------
def horse_frames(coat, silk, number, size=84):
    def build():
        frames = []
        for f in range(6):
            ph = f / 6 * math.tau
            big = pygame.Surface((S, S), pygame.SRCALPHA)
            p = Pen()
            p.s = big
            dk = gfx.mul_col(coat, 0.7)
            body_y = 120 + math.sin(ph * 2) * 4
            # patas (traseras y delanteras, desfase de galope)
            for (hx, off, col) in ((70, 0.0, dk), (88, 0.6, coat), (150, 2.2, dk), (166, 2.8, coat)):
                a = math.sin(ph + off) * 0.7
                knee = (hx + math.sin(a) * 22, body_y + 34 + math.cos(a) * 6)
                hoof = (knee[0] + math.sin(a * 1.6 + 0.3) * 24, knee[1] + 34)
                p.line((hx, body_y + 10), knee, col, 13)
                p.line(knee, hoof, col, 10)
                p.circle(hoof, 7, (40, 30, 26))
            # cola
            tail = [(52, body_y - 6), (34, body_y + 4 + math.sin(ph) * 8), (22, body_y + 26 + math.sin(ph) * 10)]
            p.lines(tail, (40, 28, 22), 12)
            # cuerpo
            p.ellipse((46, body_y - 26, 140, 62), coat)
            p.ellipse((60, body_y - 22, 110, 26), gfx.mul_col(coat, 1.15))
            # cuello y cabeza
            neck = [(150, body_y - 14), (176, body_y - 62), (200, body_y - 66), (186, body_y + 4)]
            p.poly(neck, coat)
            p.poly([(176, body_y - 66), (226, body_y - 46), (222, body_y - 30), (190, body_y - 40)], coat)
            p.ellipse((206, body_y - 48, 26, 20), dk)
            p.poly([(178, body_y - 70), (184, body_y - 88), (192, body_y - 68)], dk)
            p.circle((200, body_y - 56), 4, (20, 20, 20))
            p.lines([(170, body_y - 66), (160, body_y - 40), (164, body_y - 20)], (40, 28, 22), 8)
            # jinete
            p.rect((104, body_y - 34, 40, 14), (240, 240, 240), 6)
            p.poly([(110, body_y - 30), (150, body_y - 64), (166, body_y - 56), (136, body_y - 24)], silk)
            p.line((150, body_y - 58), (178, body_y - 50), silk, 10)
            p.circle((160, body_y - 78), 15, (250, 210, 170))
            p.poly([(146, body_y - 82), (174, body_y - 92), (178, body_y - 78), (146, body_y - 74)], silk)
            p.circle((128, body_y - 46), 15, (255, 255, 255))
            t = gfx.font(24, "bl").render(str(number), True, (20, 20, 30))
            big.blit(t, t.get_rect(center=(128, body_y - 46)))
            frames.append(gfx.pixelize(big, (size, size), 2))
        return frames
    return _c(("horse", coat, silk, number, size), build)


_NEWS = {}


def news_badge(w):
    """Insignia «NEWS!» (assets/news.png, del autor) de `w` píxeles de ancho."""
    if w not in _NEWS:
        if "img" not in _NEWS:
            import os
            img = pygame.image.load(os.path.join(os.path.dirname(__file__), "assets", "news.png"))
            try:
                img = img.convert_alpha()
            except pygame.error:
                pass
            _NEWS["img"] = img
        src = _NEWS["img"]
        _NEWS[w] = _fit(src, w, round(w * src.get_height() / src.get_width()))
    return _NEWS[w]
