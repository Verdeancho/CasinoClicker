"""Piezas compartidas por los juegos: tapetes, barra de controles, cartas animadas, historial."""
import math
import random

import pygame

from .. import gfx, art
from ..gfx import TEXT, MUTED

_cache = {}


def felt_surf(w, h, col=(40, 96, 74), border=(214, 170, 90), r=18):
    """Tapete retro: color plano con tramado sutil, contorno grueso y filete dorado."""
    key = ("felt", w, h, col, border, r)
    s = _cache.get(key)
    if s is None:
        import numpy as np
        sw, sh = max(1, w // 2), max(1, h // 2)
        small = pygame.Surface((sw, sh), pygame.SRCALPHA)
        small.fill((*col, 255))
        arr = pygame.surfarray.pixels3d(small)
        yy, xx = np.mgrid[0:sw, 0:sh]
        dither = ((xx + yy) % 4 == 0) | ((xx - yy) % 4 == 0)
        dark = np.array(gfx.mul_col(col, 0.9), np.uint8)
        arr[dither] = dark
        del arr
        big = pygame.transform.scale(small, (sw * 2, sh * 2))
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.blit(big, (0, 0))
        mask = gfx.rrect_surf(w, h, r, (255, 255, 255, 255))
        s.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        s.blit(gfx.rrect_surf(w, h, r, (0, 0, 0, 0), border=gfx.LINE, bw=4), (0, 0))
        if border:
            s.blit(gfx.rrect_surf(w - 20, h - 20, max(2, r - 6), (0, 0, 0, 0), border=(*border, 200), bw=2), (10, 10))
        _cache[key] = s
    return s


THEME = {"felt": "clasico"}     # lo fija la app con el tema elegido por el jugador


def felt(surf, rect, col=(40, 96, 74), border=(214, 170, 90), r=18):
    """Tapete de mesa con el marco del tema actual."""
    from .. import skins
    rect = pygame.Rect(rect)
    gfx.rrect(surf, rect.move(0, 6), (0, 0, 0, 110), r)
    surf.blit(skins.felt_surf(rect.w, rect.h, col, THEME["felt"], r), rect.topleft)


def dark_panel(surf, rect, r=14, top=None, bot=None, border=None):
    gfx.box(surf, rect, (*gfx.PANEL_LO, 255), r, ow=4, shadow_off=5)


def controls_bg(surf, rect):
    gfx.box(surf, rect, (*gfx.PANEL_HI, 255), 12, ow=4, shadow_off=5)


def history_pills(surf, x, y, items, max_n=12, w=52, h=24, right_to_left=False):
    """items: lista de (texto, color). Dibuja pastillas, la más reciente primero."""
    items = items[-max_n:][::-1]
    for i, (txt, col) in enumerate(items):
        xx = x - (i + 1) * (w + 6) if right_to_left else x + i * (w + 6)
        r = pygame.Rect(xx, y, w, h)
        a = 255 if i == 0 else max(120, 255 - i * 14)
        gfx.rrect(surf, r, (*gfx.mul_col(col, 0.7), 255), 6, border=gfx.LINE, bw=4, alpha=a)
        gfx.text(surf, txt, r.center, 12, "b", TEXT, anchor="center", alpha=a, max_w=w - 6)


class CardObj:
    """Carta que vuela desde un origen hasta su destino y puede girarse."""

    def __init__(self, card, src, dst, delay=0.0, face_up=True, w=92, h=130, dur=0.38):
        self.card = card
        self.src = src
        self.dst = dst
        self.age = -delay
        self.dur = dur
        self.face_up = face_up
        self.flip = 1.0 if face_up else 0.0     # 0 = dorso, 1 = cara
        self.flip_target = self.flip
        self.w, self.h = w, h
        self.sounded = False
        self.lift = 0.0
        self.hl = None

    def update(self, dt, audio=None):
        self.age += dt
        if self.age >= 0 and not self.sounded:
            self.sounded = True
            if audio:
                audio.play(f"card{random.randint(0, 2)}", 0.9, throttle=0.02)
        if self.flip != self.flip_target:
            step = dt * 4.0
            self.flip = min(self.flip_target, self.flip + step) if self.flip < self.flip_target else \
                max(self.flip_target, self.flip - step)

    def reveal(self, audio=None):
        if self.flip_target != 1.0:
            self.flip_target = 1.0
            self.face_up = True
            if audio:
                audio.play(f"card{random.randint(0, 2)}", 0.7, throttle=0.02)

    @property
    def done(self):
        return self.age >= self.dur

    def pos(self):
        if self.age <= 0:
            return self.src
        t = gfx.ease_out_cubic(min(1.0, self.age / self.dur))
        return (self.src[0] + (self.dst[0] - self.src[0]) * t, self.src[1] + (self.dst[1] - self.src[1]) * t)

    def draw(self, surf):
        if self.age < 0:
            return
        x, y = self.pos()
        y -= self.lift
        # giro: escala horizontal |cos|
        f = self.flip
        sx = abs(math.cos(f * math.pi))
        show_face = f >= 0.5
        img = art.card_sprite(self.card, self.w, self.h) if show_face else art.card_back(self.w, self.h)
        t = min(1.0, max(0.0, self.age / self.dur))
        rot = (1 - gfx.ease_out_cubic(t)) * 18
        if sx < 0.999:
            img = pygame.transform.scale(img, (max(2, int(self.w * sx) // 2 * 2), img.get_height()))
        if rot > 0.5:
            img = pygame.transform.rotate(img, rot)
        sh = gfx.shadow_surf(self.w, self.h, 10, 8, 110)
        surf.blit(sh, (x - self.w / 2 - 16 + 3, y - self.h / 2 - 16 + 6 + self.lift * 0.5))
        r = img.get_rect(center=(int(x), int(y)))
        surf.blit(img, r)
        if self.hl:
            gfx.rrect(surf, pygame.Rect(0, 0, self.w + 6, self.h + 6).move(x - self.w / 2 - 3, y - self.h / 2 - 3),
                      (0, 0, 0, 0), 12, border=self.hl, bw=3)


def toggle_pill(ui, wid, surf, rect, label, on, color=gfx.GREEN, enabled=True):
    """Interruptor tipo píldora. Devuelve el nuevo estado."""
    rect = pygame.Rect(rect)
    h = enabled and ui.hover(rect)
    if h:
        ui.hot_any = True
        ui.frame_hover = wid
        if ui.pressed:
            ui.active = wid
    v = ui.anim(wid, 1.0 if on else 0.0, 14)
    sw = pygame.Rect(rect.x, rect.centery - 12, 46, 24)
    gfx.rrect(surf, sw, (*gfx.lerp_col((34, 43, 48), color, v), 255), 6, border=gfx.LINE, bw=4)
    kn = pygame.Rect(0, 0, 16, 16)
    kn.center = (int(sw.x + 12 + 22 * v), sw.centery)
    gfx.rrect(surf, kn, (255, 255, 255, 255), 3)
    gfx.text(surf, label, (sw.right + 10, rect.centery), 12, "b", TEXT if enabled else gfx.DIM, anchor="midleft")
    if enabled and ui.released and ui.active == wid and h:
        if ui.audio:
            ui.audio.play("ui")
        return not on
    return on
