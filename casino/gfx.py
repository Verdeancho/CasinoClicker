"""Motor gráfico con estética indie-retro: fuente pixelada, bordes en píxel, sombras sólidas,
brillos por bandas y fondo de pintura en remolino. Mantiene la API anterior para toda la app."""
import math
import os
from functools import lru_cache

import numpy as np
import pygame
import pygame.gfxdraw as gd

from . import pixfont

W, H = 1600, 900

# ----------------------------------------------------------------------------
# Paleta (inspirada en Balatro)
# ----------------------------------------------------------------------------
BG_TOP = (22, 44, 40)
BG_BOT = (14, 30, 28)
PANEL = (48, 60, 66)
PANEL_HI = (64, 78, 86)
PANEL_LO = (34, 43, 48)
LINE = (20, 26, 30)
INK = (14, 18, 22)
TEXT = (255, 255, 255)
MUTED = (178, 190, 196)
DIM = (112, 124, 132)
GOLD = (245, 186, 86)
GOLD_HI = (255, 216, 120)
GOLD_DK = (190, 126, 40)
GREEN = (78, 196, 146)
GREEN_DK = (44, 138, 98)
RED = (254, 95, 85)
RED_DK = (184, 56, 52)
BLUE = (0, 157, 255)
BLUE_DK = (0, 104, 186)
PURPLE = (150, 112, 196)
PURPLE_DK = (100, 70, 140)
PINK = (244, 112, 170)
CYAN = (80, 204, 214)
ORANGE = (253, 162, 0)
FELT = (40, 96, 74)
FELT_DK = (26, 66, 50)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
SHADOW_COL = (12, 16, 20)


def hexc(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_col(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def mul_col(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c[:3])


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


# ----------------------------------------------------------------------------
# Easing
# ----------------------------------------------------------------------------
def ease_out_cubic(t):
    return 1 - (1 - t) ** 3


def ease_out_quart(t):
    return 1 - (1 - t) ** 4


def ease_in_out(t):
    return 4 * t * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def ease_out_back(t, s=1.70158):
    t -= 1
    return t * t * ((s + 1) * t + s) + 1


def ease_out_elastic(t):
    if t <= 0 or t >= 1:
        return t
    return 2 ** (-10 * t) * math.sin((t * 10 - 0.75) * (2 * math.pi / 3)) + 1


def approach(cur, target, dt, speed=12.0):
    return cur + (target - cur) * (1 - math.exp(-speed * dt))


# ----------------------------------------------------------------------------
# Fuentes: TTF solo para el arte interno; el texto de la interfaz usa la fuente pixelada
# ----------------------------------------------------------------------------
FONT_DIR = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
FONT_FILES = {"r": "segoeui.ttf", "sb": "seguisb.ttf", "b": "segoeuib.ttf", "bl": "seguibl.ttf",
              "num": "bahnschrift.ttf", "sym": "seguisym.ttf", "mono": "consola.ttf"}


@lru_cache(maxsize=None)
def font(size, weight="r"):
    path = os.path.join(FONT_DIR, FONT_FILES.get(weight, "segoeui.ttf"))
    try:
        return pygame.font.Font(path, int(size))
    except (OSError, FileNotFoundError):
        return pygame.font.Font(None, int(size * 1.3))


def px_scale(size):
    """Tamaño 'en puntos' de la API antigua → escala entera de la fuente pixelada."""
    if size <= 10:
        return 1
    if size <= 18:
        return 2
    if size <= 27:
        return 3
    if size <= 35:
        return 4
    return max(5, int(size / 7.2))


def text_surf(s, size=16, weight="r", color=TEXT, shadow=True):
    sc = px_scale(size)
    return pixfont.render(str(s), tuple(color[:3]), sc, weight == "bl", SHADOW_COL if shadow else None)


def text_w(s, size=16, weight="r"):
    return pixfont.width(str(s), px_scale(size), weight == "bl") + px_scale(size)


def text(dst, s, pos, size=16, weight="r", color=TEXT, anchor="topleft", alpha=255, shadow=None, max_w=None):
    s = str(s)
    use_shadow = shadow is not False and (color[0] + color[1] + color[2]) > 260
    if max_w and text_w(s, size, weight) > max_w:
        while len(s) > 1 and text_w(s + "…", size, weight) > max_w:
            s = s[:-1]
        s = s.rstrip() + "…"
    surf = text_surf(s, size, weight, color, use_shadow)
    r = surf.get_rect(**{anchor: (int(pos[0]), int(pos[1]))})
    if alpha < 255:
        surf = surf.copy()
        surf.set_alpha(int(alpha))
    dst.blit(surf, r)
    return r


def wavy_text(dst, s, pos, size, color, t, amp=3, speed=5.0, anchor="center", weight="r"):
    """Texto que ondula letra a letra (muy de Balatro)."""
    sc = px_scale(size)
    total = text_w(s, size, weight)
    if anchor == "center":
        x = pos[0] - total / 2
        y = pos[1] - pixfont.CELL_H * sc / 2
    else:
        x, y = pos
    for i, ch in enumerate(str(s)):
        g = pixfont.render(ch, tuple(color[:3]), sc, weight == "bl", SHADOW_COL)
        dy = math.sin(t * speed + i * 0.55) * amp
        dst.blit(g, (int(x), int(y + dy)))
        x += pixfont.width(ch, sc, weight == "bl") + pixfont.SPACING * sc


def wrap(s, size, weight, max_w):
    words = str(s).split()
    lines, cur = [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if text_w(t, size, weight) <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def line_height(size):
    return int(pixfont.CELL_H * px_scale(size) * 0.95)


def text_wrapped(dst, s, pos, size, weight, color, max_w, line_h=None, alpha=255):
    line_h = max(line_h or 0, line_height(size))
    lines = wrap(s, size, weight, max_w)
    for i, ln in enumerate(lines):
        text(dst, ln, (pos[0], pos[1] + i * line_h), size, weight, color, alpha=alpha)
    return len(lines) * line_h


# ----------------------------------------------------------------------------
# Superficies cacheadas
# ----------------------------------------------------------------------------
_surf_cache = {}


def _cached(key, builder):
    s = _surf_cache.get(key)
    if s is None:
        if len(_surf_cache) > 3000:
            _surf_cache.clear()
        s = builder()
        _surf_cache[key] = s
    return s


def vgradient(w, h, top, bot, bands=8):
    """Degradado vertical en bandas (aspecto retro)."""
    def build():
        hh = max(1, h)
        s = pygame.Surface((1, hh), pygame.SRCALPHA)
        for y in range(hh):
            t = y / max(1, hh - 1)
            t = min(bands - 1, int(t * bands)) / max(1, bands - 1)
            c = [int(top[i] + (bot[i] - top[i]) * t) for i in range(len(top))]
            if len(c) == 3:
                c.append(255)
            s.set_at((0, y), c)
        return pygame.transform.scale(s, (max(1, w), hh))
    return _cached(("vg", w, h, top, bot, bands), build)


def _flat(fill, grad):
    if grad:
        a, b = grad
        c = tuple(int((a[i] + b[i]) / 2) for i in range(3))
        alpha = int((a[3] if len(a) > 3 else 255) + (b[3] if len(b) > 3 else 255)) // 2
        return (*c, alpha)
    if fill is None:
        return (0, 0, 0, 0)
    return fill if len(fill) == 4 else (*fill, 255)


def rrect_surf(w, h, r, fill, border=None, bw=0, grad=None):
    """Rectángulo redondeado con esquinas en píxel (se dibuja a media resolución)."""
    w, h = max(1, int(w)), max(1, int(h))

    def build():
        k = 2 if (w >= 8 and h >= 8) else 1
        sw, sh = max(1, w // k), max(1, h // k)
        small = pygame.Surface((sw, sh), pygame.SRCALPHA)
        col = _flat(fill, grad)
        rr = max(0, int(r) // k)
        pygame.draw.rect(small, col, small.get_rect(), border_radius=rr)
        if grad:   # banda clara arriba para dar volumen
            a = grad[0]
            top = (*a[:3], a[3] if len(a) > 3 else 255)
            band = pygame.Surface((sw, sh), pygame.SRCALPHA)
            pygame.draw.rect(band, top, (0, 0, sw, max(1, sh // 2)), border_top_left_radius=rr,
                             border_top_right_radius=rr)
            mask = pygame.Surface((sw, sh), pygame.SRCALPHA)
            pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=rr)
            band.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            small.blit(band, (0, 0))
        if border and bw:
            bc = border if len(border) == 4 else (*border, 255)
            pygame.draw.rect(small, bc, small.get_rect(), max(1, int(round(bw / k))), border_radius=rr)
        return pygame.transform.scale(small, (w, h))
    return _cached(("rr", w, h, r, fill, border, bw, grad), build)


def rrect(dst, rect, fill, r=10, border=None, bw=0, grad=None, alpha=255):
    rect = pygame.Rect(rect)
    s = rrect_surf(rect.w, rect.h, r, fill, border, bw, grad)
    if alpha < 255:
        s = s.copy()
        s.set_alpha(int(alpha))
    dst.blit(s, rect.topleft)


def box(dst, rect, fill, r=10, outline=LINE, ow=4, shadow_off=6, lip=None):
    """Caja estilo Balatro: sombra sólida desplazada, relleno plano, contorno oscuro grueso."""
    rect = pygame.Rect(rect)
    if shadow_off:
        rrect(dst, rect.move(0, shadow_off), (0, 0, 0, 110), r)
    rrect(dst, rect, fill, r, border=outline, bw=ow)
    if lip:
        rrect(dst, (rect.x + ow, rect.bottom - ow - lip, rect.w - ow * 2, lip), (*mul_col(fill, 0.78), 255), 2)


def shadow_surf(w, h, r, blur=14, alpha=120):
    """Sombra sólida (sin desenfoque) con la misma geometría que la versión antigua."""
    def build():
        pad = blur * 2
        s = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
        s.blit(rrect_surf(w, h, r, (0, 0, 0, min(150, alpha))), (pad, pad))
        return s
    return _cached(("sh", w, h, r, blur, alpha), build)


def shadow(dst, rect, r=10, blur=14, alpha=120, offset=(0, 6)):
    rect = pygame.Rect(rect)
    rrect(dst, rect.move(offset[0], max(4, offset[1])), (0, 0, 0, min(140, alpha)), r)


def glow_surf(radius, color, strength=1.0, additive=True):
    """Brillo radial en bandas y píxeles gruesos."""
    radius = max(4, int(radius))

    def build():
        k = 3
        n = max(2, radius * 2 // k)
        yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
        d = np.sqrt((xx - n / 2 + 0.5) ** 2 + (yy - n / 2 + 0.5) ** 2) / (n / 2)
        inten = np.clip(1 - d, 0, 1) ** 1.6
        inten = np.floor(inten * 4) / 4 * strength
        inten = np.clip(inten, 0, 1)
        s = pygame.Surface((n, n), pygame.SRCALPHA)
        rgb = np.zeros((n, n, 3), np.float32)
        for i in range(3):
            rgb[..., i] = color[i] * (inten if additive else 1.0)
        pygame.surfarray.blit_array(s, np.clip(rgb, 0, 255).astype(np.uint8).transpose(1, 0, 2))
        a = pygame.surfarray.pixels_alpha(s)
        a[:] = (inten * 255).astype(np.uint8).T
        del a
        return pygame.transform.scale(s, (radius * 2, radius * 2))
    return _cached(("glow", radius, color, strength, additive), build)


def glow(dst, center, radius, color, strength=1.0, additive=True):
    strength = round(clamp(strength * 0.7, 0, 1.2) * 10) / 10
    if strength <= 0:
        return
    radius = max(4, int(radius) // 4 * 4)
    color = tuple(int(c) // 16 * 16 for c in color[:3])
    s = glow_surf(radius, color, strength, additive)
    dst.blit(s, (int(center[0] - radius), int(center[1] - radius)),
             special_flags=pygame.BLEND_RGB_ADD if additive else 0)


def circle_surf(r, color, border=None, bw=0):
    def build():
        size = int(r * 2 + 2)
        k = 2 if size >= 10 else 1
        n = max(1, size // k)
        small = pygame.Surface((n, n), pygame.SRCALPHA)
        c = (n // 2, n // 2)
        rr = max(1, int(r / k))
        col = color if len(color) == 4 else (*color, 255)
        pygame.draw.circle(small, col, c, rr)
        if border and bw:
            bc = border if len(border) == 4 else (*border, 255)
            pygame.draw.circle(small, bc, c, rr, max(1, int(round(bw / k))))
        return pygame.transform.scale(small, (n * k, n * k))
    return _cached(("circ", int(r), color, border, bw), build)


def circle(dst, center, r, color, border=None, bw=0):
    s = circle_surf(r, color, border, bw)
    dst.blit(s, (int(center[0] - s.get_width() / 2), int(center[1] - s.get_height() / 2)))


def aa_poly(dst, color, pts):
    ipts = [(int(x), int(y)) for x, y in pts]
    if len(ipts) >= 3:
        gd.filled_polygon(dst, ipts, color)


def thick_aaline(dst, color, pts, width=3):
    if len(pts) < 2:
        return
    hw = width / 2
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        dx, dy = x2 - x1, y2 - y1
        L = math.hypot(dx, dy) or 1
        nx, ny = -dy / L * hw, dx / L * hw
        aa_poly(dst, color, [(x1 + nx, y1 + ny), (x2 + nx, y2 + ny), (x2 - nx, y2 - ny), (x1 - nx, y1 - ny)])
    for x, y in pts[1:-1]:
        gd.filled_circle(dst, int(x), int(y), max(1, int(hw)), color)


def star_points(cx, cy, ro, ri, n=5, rot=-math.pi / 2):
    pts = []
    for i in range(n * 2):
        r = ro if i % 2 == 0 else ri
        a = rot + i * math.pi / n
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def blit_center(dst, surf, center, alpha=255):
    r = surf.get_rect(center=(int(center[0]), int(center[1])))
    if alpha < 255:
        surf = surf.copy()
        surf.set_alpha(int(alpha))
    dst.blit(surf, r)
    return r


def scaled(surf, factor):
    if abs(factor - 1) < 0.01:
        return surf
    w, h = surf.get_size()
    return pygame.transform.scale(surf, (max(1, int(w * factor)), max(1, int(h * factor))))


def ss_canvas(w, h):
    return pygame.Surface((int(w * 3), int(h * 3)), pygame.SRCALPHA)


def finish_ss(big, w, h):
    return pygame.transform.smoothscale(big, (int(w), int(h)))


# ----------------------------------------------------------------------------
# Pixelado de sprites
# ----------------------------------------------------------------------------
def pixelize(surf, size=None, factor=3, outline=INK, colors=24):
    """Convierte cualquier imagen en pixel art: reduce, umbraliza el alfa, posteriza, contorna y amplía."""
    w, h = surf.get_size()
    tw, th = size if size else (w, h)
    sw, sh = max(1, tw // factor), max(1, th // factor)
    if outline is not None:
        sw, sh = max(1, sw - 2), max(1, sh - 2)
    small = pygame.transform.smoothscale(surf, (sw, sh))
    rgb = pygame.surfarray.pixels3d(small)
    q = 256 // colors
    rgb[:] = (rgb // q) * q + q // 2
    del rgb
    a = pygame.surfarray.pixels_alpha(small)
    mask = a > 110
    a[:] = np.where(mask, 255, 0).astype(np.uint8)
    del a
    if outline is not None:
        m = np.zeros((sw + 2, sh + 2), bool)
        m[1:-1, 1:-1] = mask
        ring = (np.roll(m, 1, 0) | np.roll(m, -1, 0) | np.roll(m, 1, 1) | np.roll(m, -1, 1)) & ~m
        ol = pygame.Surface((sw + 2, sh + 2), pygame.SRCALPHA)
        ol.fill((*outline, 255))
        oa = pygame.surfarray.pixels_alpha(ol)
        oa[:] = np.where(ring, 255, 0).astype(np.uint8)
        del oa
        ol.blit(small, (1, 1))
        small = ol
    return pygame.transform.scale(small, (small.get_width() * factor, small.get_height() * factor))


# ----------------------------------------------------------------------------
# Fondo animado y paneles
# ----------------------------------------------------------------------------
_SW, _SH = W // 4, H // 4
_yy, _xx = np.mgrid[0:_SH, 0:_SW].astype(np.float32)
_ux = (_xx - _SW / 2) / _SH
_uy = (_yy - _SH / 2) / _SH
_r = np.sqrt(_ux ** 2 + _uy ** 2)
_ang0 = np.arctan2(_uy, _ux)
SWIRL_COLS = np.array([(18, 38, 35), (24, 50, 46), (31, 63, 57), (40, 78, 70), (52, 94, 84)], np.uint8)
_swirl_small = pygame.Surface((_SW, _SH))
_swirl_big = pygame.Surface((W, H))
_swirl_t = -1.0


def swirl_bg(dst, t, colors=None):
    """Fondo de pintura en remolino (estilo Balatro, sin ojo de pez)."""
    global _swirl_t
    if abs(t - _swirl_t) > 1 / 30:
        _swirl_t = t
        a = _ang0 + 1.6 / (_r + 0.35) + t * 0.07
        v = (np.sin(a * 3 + _r * 7 - t * 0.35) * 0.55
             + np.sin(_ux * 3.1 + t * 0.21 + np.cos(_uy * 4 - t * 0.17)) * 0.45)
        v += np.sin((_ux + _uy) * 9 + a * 2) * 0.12
        idx = np.clip(((v + 1.15) / 2.3 * 5).astype(np.int32), 0, 4)
        cols = colors if colors is not None else SWIRL_COLS
        pygame.surfarray.blit_array(_swirl_small, cols[idx].transpose(1, 0, 2))
        pygame.transform.scale(_swirl_small, (W, H), _swirl_big)
    dst.blit(_swirl_big, (0, 0))


def background():
    s = pygame.Surface((W, H))
    swirl_bg(s, 0)
    return s


def panel(dst, rect, r=16, alpha=245, hi=False):
    rect = pygame.Rect(rect)
    rrect(dst, rect.move(0, 8), (0, 0, 0, 110), r)
    rrect(dst, rect, (*(PANEL_HI if hi else PANEL), alpha), r, border=LINE, bw=4)
