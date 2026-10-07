"""Iconos vectoriales procedurales. Se dibujan en un lienzo de 240x240 y se reducen con
suavizado, así que salen nítidos a cualquier tamaño."""
import math

import pygame

from . import gfx

S = 240
C = S // 2


class Pen:
    def __init__(self):
        self.s = pygame.Surface((S, S), pygame.SRCALPHA)

    # primitivas (coordenadas en el espacio 240x240)
    def circle(self, c, r, col, w=0, s=None):
        pygame.draw.circle(s or self.s, col, (int(c[0]), int(c[1])), int(r), int(w))

    def ellipse(self, rect, col, w=0, s=None):
        pygame.draw.ellipse(s or self.s, col, pygame.Rect(rect), int(w))

    def poly(self, pts, col, w=0, s=None):
        pygame.draw.polygon(s or self.s, col, [(int(x), int(y)) for x, y in pts], int(w))

    def rect(self, r, col, rad=0, w=0, s=None):
        pygame.draw.rect(s or self.s, col, pygame.Rect(r), int(w), border_radius=int(rad))

    def line(self, a, b, col, w=6, s=None):
        pygame.draw.line(s or self.s, col, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), int(w))
        self.circle(a, w / 2 - 0.5, col, s=s)
        self.circle(b, w / 2 - 0.5, col, s=s)

    def lines(self, pts, col, w=6, s=None):
        for a, b in zip(pts, pts[1:]):
            self.line(a, b, col, w, s)

    def arc(self, rect, a0, a1, col, w=6, s=None):
        pygame.draw.arc(s or self.s, col, pygame.Rect(rect), a0, a1, int(w))

    def text(self, t, size, col, center, weight="bl", s=None):
        surf = gfx.font(size, weight).render(t, True, col)
        (s or self.s).blit(surf, surf.get_rect(center=(int(center[0]), int(center[1]))))

    def layer(self):
        return pygame.Surface((S, S), pygame.SRCALPHA)

    def merge(self, layer, alpha=255):
        if alpha < 255:
            layer.set_alpha(alpha)
        self.s.blit(layer, (0, 0))

    def shine(self, rect, alpha=90):
        lay = self.layer()
        pygame.draw.ellipse(lay, (255, 255, 255, 255), pygame.Rect(rect))
        self.merge(lay, alpha)

    def blit_rot(self, sub, center, angle):
        r = pygame.transform.rotozoom(sub, angle, 1.0)
        self.s.blit(r, r.get_rect(center=(int(center[0]), int(center[1]))))


# ----------------------------------------------------------------------------
# Piezas reutilizables
# ----------------------------------------------------------------------------
def coin(p, c, r, face=(255, 204, 64), dark=(196, 132, 20), mark="€"):
    p.circle((c[0], c[1] + r * 0.09), r, gfx.mul_col(dark, 0.7))
    p.circle(c, r, dark)
    p.circle(c, r * 0.92, face)
    p.circle(c, r * 0.74, gfx.mul_col(face, 0.86), w=max(2, r * 0.06))
    if mark:
        p.text(mark, int(r * 1.0), gfx.mul_col(dark, 0.95), (c[0] + r * 0.03, c[1] + r * 0.04))
        p.text(mark, int(r * 1.0), (255, 246, 200), c)
    p.shine((c[0] - r * 0.65, c[1] - r * 0.75, r * 0.8, r * 0.5), 80)


def card(w=110, h=150, rank="A", suit="♠", col=(25, 25, 30), back=False):
    sub = pygame.Surface((w + 8, h + 8), pygame.SRCALPHA)
    pygame.draw.rect(sub, (0, 0, 0, 90), (6, 8, w, h), border_radius=14)
    if back:
        pygame.draw.rect(sub, (150, 30, 50), (2, 2, w, h), border_radius=14)
        pygame.draw.rect(sub, (230, 190, 90), (10, 10, w - 16, h - 16), 3, border_radius=9)
    else:
        pygame.draw.rect(sub, (252, 250, 244), (2, 2, w, h), border_radius=14)
        pygame.draw.rect(sub, (200, 200, 205), (2, 2, w, h), 2, border_radius=14)
        f = gfx.font(int(h * 0.30), "bl")
        t = f.render(rank, True, col)
        sub.blit(t, (12, 4))
        fs = gfx.font(int(h * 0.42), "sym")
        st = fs.render(suit, True, col)
        sub.blit(st, st.get_rect(center=(w / 2 + 4, h * 0.62)))
    return sub


# ----------------------------------------------------------------------------
# Iconos
# ----------------------------------------------------------------------------
def i_coinflip(p):
    coin(p, (C + 10, C + 14), 82, mark="")
    p.poly(gfx.star_points(C + 10, C + 14, 46, 19), (178, 112, 10))
    p.poly(gfx.star_points(C + 10, C + 10, 46, 19), (255, 244, 190))
    for i, a in enumerate((200, 225, 250)):
        rr = 108
        x, y = C + 10 + rr * math.cos(math.radians(a)), C + 14 + rr * math.sin(math.radians(a))
        p.line((x, y), (x + 14 * math.cos(math.radians(a)), y + 14 * math.sin(math.radians(a))),
               (255, 230, 140), 7)


def _die(size, pips, col=(250, 250, 252), pip=(220, 40, 60)):
    sub = pygame.Surface((size + 10, size + 10), pygame.SRCALPHA)
    pygame.draw.rect(sub, (0, 0, 0, 80), (8, 10, size, size), border_radius=int(size * 0.22))
    pygame.draw.rect(sub, (200, 200, 214), (3, 7, size, size), border_radius=int(size * 0.22))
    pygame.draw.rect(sub, col, (3, 3, size, size), border_radius=int(size * 0.22))
    q = size / 4
    pos = {1: [(2, 2)], 2: [(1, 1), (3, 3)], 3: [(1, 1), (2, 2), (3, 3)], 4: [(1, 1), (3, 1), (1, 3), (3, 3)],
           5: [(1, 1), (3, 1), (2, 2), (1, 3), (3, 3)], 6: [(1, 1), (3, 1), (1, 2), (3, 2), (1, 3), (3, 3)]}[pips]
    for gx, gy in pos:
        pygame.draw.circle(sub, pip, (int(3 + gx * q), int(3 + gy * q)), int(size * 0.09))
    return sub


def i_dice(p):
    p.blit_rot(_die(104, 5), (C - 30, C + 22), 16)
    p.blit_rot(_die(96, 3, pip=(30, 30, 40)), (C + 40, C - 26), -14)


def i_slots(p):
    p.rect((34, 30, 160, 186), (150, 24, 48), 26)
    p.rect((34, 30, 160, 186), (230, 60, 80), 26, 6)
    p.rect((48, 70, 132, 80), (250, 246, 236), 12)
    for i in range(3):
        x = 48 + 22 + i * 44
        p.text("7", 54, (210, 30, 50), (x, 110))
    p.line((92, 70), (92, 150), (220, 210, 190), 3)
    p.line((136, 70), (136, 150), (220, 210, 190), 3)
    p.rect((60, 40, 108, 22), (255, 210, 80), 10)
    p.line((204, 70), (204, 140), (190, 190, 205), 8)
    p.circle((204, 62), 14, (240, 60, 80))
    p.rect((60, 170, 108, 26), (100, 14, 30), 10)
    p.shine((52, 74, 60, 24), 70)


def i_scratch(p):
    p.rect((26, 50, 188, 140), (40, 190, 170), 20)
    p.rect((26, 50, 188, 140), (20, 120, 110), 20, 5)
    p.rect((44, 80, 152, 80), (196, 204, 214), 12)
    lay = p.layer()
    pygame.draw.rect(lay, (0, 0, 0, 0), (0, 0, S, S))
    p.poly(gfx.star_points(100, 120, 34, 14), (255, 200, 60))
    for k in range(6):
        p.line((60 + k * 14, 150), (110 + k * 14, 86), (240, 244, 250), 6)
    coin(p, (176, 160), 38, mark="")


def i_roulette(p):
    p.circle((C, C + 6), 104, (60, 30, 12))
    p.circle((C, C), 104, (120, 70, 30))
    p.circle((C, C), 92, (40, 24, 10))
    n = 18
    for i in range(n):
        a0 = i * 2 * math.pi / n
        a1 = (i + 1) * 2 * math.pi / n
        col = (24, 150, 70) if i == 0 else ((210, 40, 50) if i % 2 else (25, 25, 30))
        pts = [(C, C)] + [(C + 88 * math.cos(a0 + (a1 - a0) * k / 6), C + 88 * math.sin(a0 + (a1 - a0) * k / 6))
                          for k in range(7)]
        p.poly(pts, col)
    p.circle((C, C), 54, (150, 90, 40))
    p.circle((C, C), 54, (220, 170, 70), 4)
    for k in range(4):
        a = k * math.pi / 2 + 0.4
        p.line((C, C), (C + 42 * math.cos(a), C + 42 * math.sin(a)), (240, 200, 90), 8)
    p.circle((C, C), 14, (255, 220, 110))
    p.circle((C + 60, C - 52), 11, (250, 250, 250))


def i_blackjack(p):
    p.blit_rot(card(108, 148, "K", "♥", (210, 30, 50)), (C - 26, C + 6), 14)
    p.blit_rot(card(108, 148, "A", "♠"), (C + 26, C + 4), -10)


def i_hilo(p):
    p.blit_rot(card(100, 140, "7", "♣"), (C - 18, C + 4), 0)
    p.poly([(186, 40), (222, 90), (198, 90), (198, 118), (174, 118), (174, 90), (150, 90)], (60, 210, 120))
    p.poly([(186, 206), (222, 156), (198, 156), (198, 128), (174, 128), (174, 156), (150, 156)], (240, 80, 90))


def i_crash(p):
    k = 0.16
    pts = [(22 + i * 8.5, 212 - 104 * (math.exp(k * i) - 1) / (math.exp(k * 18) - 1)) for i in range(19)]
    p.lines(pts, (255, 150, 60), 11)
    rk = pygame.Surface((90, 160), pygame.SRCALPHA)
    pygame.draw.polygon(rk, (255, 170, 40), [(45, 150), (30, 118), (60, 118)])
    pygame.draw.polygon(rk, (255, 230, 120), [(45, 140), (37, 118), (53, 118)])
    pygame.draw.ellipse(rk, (235, 236, 245), (24, 10, 42, 116))
    pygame.draw.polygon(rk, (230, 60, 80), [(24, 90), (8, 120), (28, 116)])
    pygame.draw.polygon(rk, (230, 60, 80), [(66, 90), (82, 120), (62, 116)])
    pygame.draw.circle(rk, (80, 160, 255), (45, 52), 11)
    pygame.draw.circle(rk, (200, 230, 255), (45, 52), 11, 3)
    p.blit_rot(rk, (170, 70), -38)


def gem(p, c, r, col=(70, 230, 160)):
    x, y = c
    top = [(x - r, y - r * 0.25), (x - r * 0.55, y - r * 0.8), (x + r * 0.55, y - r * 0.8), (x + r, y - r * 0.25)]
    p.poly(top + [(x, y + r)], gfx.mul_col(col, 0.75))
    p.poly(top, gfx.mul_col(col, 1.15))
    p.poly([(x - r, y - r * 0.25), (x + r, y - r * 0.25), (x, y + r)], col)
    p.poly([(x - r * 0.35, y - r * 0.25), (x + r * 0.35, y - r * 0.25), (x, y + r)], gfx.mul_col(col, 1.25))
    p.poly([(x - r * 0.55, y - r * 0.8), (x - r * 0.15, y - r * 0.25), (x - r, y - r * 0.25)], (255, 255, 255))


def i_mines(p):
    p.circle((76, 92), 46, (40, 40, 52))
    p.circle((70, 86), 46, (60, 60, 76))
    p.line((96, 50), (112, 30), (150, 120, 90), 8)
    p.circle((116, 26), 9, (255, 180, 60))
    p.shine((44, 58, 30, 18), 90)
    gem(p, (148, 140), 72)


def i_plinko(p):
    for r in range(5):
        for k in range(r + 2):
            x = C + (k - (r + 1) / 2) * 38
            y = 44 + r * 36
            p.circle((x, y), 7, (220, 220, 240))
    p.circle((C + 18, 128), 18, (255, 100, 180))
    p.shine((C + 6, 114, 14, 9), 120)
    cols = [(255, 92, 104), (255, 160, 70), (255, 214, 80), (255, 160, 70), (255, 92, 104)]
    for i, col in enumerate(cols):
        p.rect((24 + i * 39, 204, 34, 22), col, 6)


def i_wheel(p):
    cols = [(255, 92, 104), (255, 200, 72), (88, 164, 255), (64, 220, 140), (176, 120, 255), (255, 150, 60)]
    p.circle((C, C + 14), 98, (90, 40, 110))
    n = 12
    for i in range(n):
        a0 = i * 2 * math.pi / n
        a1 = (i + 1) * 2 * math.pi / n
        pts = [(C, C + 14)] + [(C + 88 * math.cos(a0 + (a1 - a0) * k / 5), C + 14 + 88 * math.sin(a0 + (a1 - a0) * k / 5))
                               for k in range(6)]
        p.poly(pts, cols[i % len(cols)])
    p.circle((C, C + 14), 26, (60, 24, 80))
    p.poly(gfx.star_points(C, C + 14, 18, 8), (255, 220, 110))
    p.poly([(C - 18, 6), (C + 18, 6), (C, 44)], (250, 250, 250))
    p.poly([(C - 18, 6), (C + 18, 6), (C, 44)], (60, 24, 80), 3)


def i_horses(p):
    cx, cy = C, C + 6
    lay = p.layer()
    pygame.draw.circle(lay, (210, 170, 70), (cx, cy), 86)
    pygame.draw.circle(lay, (0, 0, 0, 0), (cx, cy), 50)
    pygame.draw.rect(lay, (0, 0, 0, 0), (cx - 50, cy + 10, 100, 100))
    pygame.draw.rect(lay, (0, 0, 0, 0), (cx - 86, cy + 70, 172, 60))
    p.merge(lay)
    p.rect((cx - 86, cy + 52, 38, 26), (230, 190, 90), 6)
    p.rect((cx + 48, cy + 52, 38, 26), (230, 190, 90), 6)
    for k in range(7):
        a = math.pi * (0.95 + k * 0.183)
        p.circle((cx + 68 * math.cos(a), cy + 68 * math.sin(a)), 6, (120, 90, 30))
    p.shine((cx - 70, cy - 74, 70, 30), 70)


def i_keno(p):
    p.circle((C, C + 8), 92, (30, 60, 140))
    p.circle((C, C), 92, (60, 130, 255))
    p.circle((C, C), 52, (250, 250, 252))
    p.text("7", 70, (30, 60, 140), (C, C + 2))
    p.shine((C - 64, C - 76, 70, 36), 90)


def i_videopoker(p):
    p.blit_rot(card(96, 134, "Q", "♦", (210, 30, 50)), (C - 46, C + 16), 18)
    p.blit_rot(card(96, 134, "K", "♣"), (C, C + 4), 0)
    p.blit_rot(card(96, 134, "A", "♥", (210, 30, 50)), (C + 46, C + 16), -18)


# ---- negocios
def i_hucha(p):
    pink, dk = (255, 150, 190), (220, 100, 150)
    p.ellipse((30, 60, 170, 130), dk)
    p.ellipse((30, 54, 170, 130), pink)
    p.poly([(70, 70), (84, 30), (108, 64)], dk)
    for x in (66, 150):
        p.rect((x, 160, 26, 44), dk, 10)
    p.ellipse((178, 96, 44, 50), dk)
    p.circle((190, 112), 5, (130, 50, 90))
    p.circle((206, 112), 5, (130, 50, 90))
    p.circle((150, 92), 8, (60, 30, 50))
    p.rect((92, 60, 48, 10), (140, 60, 100), 5)
    coin(p, (116, 30), 24, mark="")
    p.shine((60, 74, 70, 30), 80)


def i_chicles(p):
    p.rect((70, 150, 100, 70), (210, 40, 60), 14)
    p.rect((104, 176, 32, 24), (60, 20, 30), 6)
    p.circle((C, 96), 72, (200, 230, 255))
    cols = [(255, 92, 104), (255, 200, 72), (88, 164, 255), (64, 220, 140), (176, 120, 255)]
    import random
    rng = random.Random(3)
    for k in range(14):
        a, d = rng.uniform(0, 6.28), rng.uniform(0, 52)
        p.circle((C + d * math.cos(a), 104 + d * math.sin(a) * 0.8), 15, cols[k % 5])
    p.shine((70, 40, 60, 40), 110)
    p.rect((96, 18, 48, 16), (210, 40, 60), 6)


def i_limonada(p):
    p.poly([(60, 40), (180, 40), (164, 214), (76, 214)], (220, 236, 250))
    p.poly([(68, 90), (172, 90), (164, 210), (76, 210)], (255, 220, 70))
    p.line((140, 10), (124, 160), (255, 92, 104), 10)
    p.circle((176, 52), 34, (255, 220, 70))
    p.circle((176, 52), 26, (255, 245, 170))
    for k in range(6):
        a = k * math.pi / 3
        p.line((176, 52), (176 + 24 * math.cos(a), 52 + 24 * math.sin(a)), (255, 220, 70), 3)
    for (x, y) in ((96, 130), (130, 160), (110, 186)):
        p.circle((x, y), 6, (255, 250, 220))


def i_loteria(p):
    p.rect((30, 60, 180, 120), (88, 164, 255), 14)
    for y in (60, 180):
        for k in range(9):
            p.circle((42 + k * 20, y), 6, (0, 0, 0, 0))
    p.rect((44, 76, 152, 88), (240, 246, 255), 8)
    for k in range(3):
        p.circle((76 + k * 44, 120), 18, [(255, 92, 104), (255, 200, 72), (64, 220, 140)][k])
        p.text(str([7, 3, 9][k]), 24, (255, 255, 255), (76 + k * 44, 120))


def i_bar(p):
    p.rect((50, 64, 110, 150), (255, 190, 60), 14)
    p.rect((160, 96, 40, 80), (220, 230, 240), 18, 12)
    for y in (100, 140, 180):
        p.circle((86, y), 6, (255, 230, 150))
    p.ellipse((40, 34, 70, 50), (250, 250, 245))
    p.ellipse((84, 26, 70, 54), (250, 250, 245))
    p.ellipse((126, 38, 50, 44), (250, 250, 245))
    p.rect((50, 54, 110, 22), (250, 250, 245))
    p.shine((60, 80, 24, 110), 70)


def i_bingo(p):
    p.circle((C, C + 8), 92, (200, 100, 20))
    p.circle((C, C), 92, (255, 150, 60))
    p.circle((C, C), 54, (255, 255, 255))
    p.text("B", 64, (200, 100, 20), (C, C + 2))
    p.shine((C - 64, C - 76, 70, 36), 90)


def i_clandestino(p):
    col = (176, 120, 255)
    p.poly([(14, 92), (60, 66), (120, 84), (180, 66), (226, 92), (210, 150), (160, 160), (120, 132),
            (80, 160), (30, 150)], col)
    p.ellipse((52, 94, 50, 34), (30, 16, 50))
    p.ellipse((138, 94, 50, 34), (30, 16, 50))
    p.poly([(120, 84), (180, 66), (226, 92), (210, 150)], gfx.mul_col(col, 0.8))
    p.line((14, 92), (0, 70), (255, 200, 72), 5)
    p.shine((40, 70, 60, 20), 80)


def i_barco(p):
    p.rect((90, 40, 26, 50), (255, 92, 104), 4)
    p.rect((126, 50, 26, 40), (255, 92, 104), 4)
    p.rect((60, 84, 130, 36), (240, 240, 250), 8)
    for k in range(5):
        p.circle((78 + k * 24, 102), 6, (88, 164, 255))
    p.poly([(26, 118), (214, 118), (186, 170), (52, 170)], (40, 60, 110))
    for k in range(4):
        p.arc((10 + k * 56, 170, 60, 34), 0, math.pi, (88, 164, 255), 7)


def i_vegas(p):
    p.rect((112, 120, 16, 110), (120, 120, 140))
    p.poly(gfx.star_points(C, 86, 92, 40), (255, 92, 104))
    p.poly(gfx.star_points(C, 86, 74, 30), (255, 200, 72))
    for pt in gfx.star_points(C, 86, 92, 40):
        p.circle(pt, 6, (255, 250, 220))
    p.text("$", 54, (180, 40, 60), (C, 88))


def i_offshore(p):
    p.poly([(20, 82), (C, 22), (220, 82)], (88, 200, 140))
    p.rect((26, 82, 188, 14), (60, 160, 110))
    for k in range(5):
        p.rect((40 + k * 36, 102, 18, 88), (220, 240, 230), 4)
    p.rect((20, 192, 200, 22), (60, 160, 110), 4)
    p.text("$", 34, (40, 110, 70), (C, 60))


def i_cripto(p):
    coin(p, (C, C), 96, (255, 170, 50), (200, 110, 10), mark="₿")


def i_petrolera(p):
    col = (150, 160, 180)
    p.line((70, 220), (C, 26), col, 10)
    p.line((170, 220), (C, 26), col, 10)
    for y in (90, 140, 190):
        w = (y - 26) * 0.29
        p.line((C - w, y), (C + w, y), col, 7)
    p.line((C - 22, 90), (C + 36, 140), col, 5)
    p.line((C + 22, 90), (C - 36, 140), col, 5)
    p.poly([(186, 120), (204, 150), (196, 172), (176, 172), (168, 150)], (30, 30, 40))
    p.circle((186, 158), 16, (30, 30, 40))


def i_orbital(p):
    p.circle((C, C), 60, (70, 220, 230))
    p.circle((C - 14, C - 10), 60, (120, 240, 245))
    p.circle((C, C), 60, (70, 220, 230), 0)
    p.shine((C - 44, C - 46, 50, 30), 90)
    lay = p.layer()
    pygame.draw.ellipse(lay, (255, 200, 72), (14, 96, 212, 52), 9)
    rot = pygame.transform.rotate(lay, 18)
    p.s.blit(rot, rot.get_rect(center=(C, C)))
    p.circle((196, 52), 10, (255, 255, 255))


def i_dimensional(p):
    cols = [(90, 30, 160), (140, 60, 220), (200, 110, 255), (240, 180, 255), (255, 255, 255)]
    for k, col in enumerate(cols):
        p.ellipse((20 + k * 18, 40 + k * 16, 200 - k * 36, 160 - k * 32), col, 0 if k == 4 else 10)


def i_multiverso(p):
    col = (255, 92, 104)
    pts = []
    for k in range(101):
        t = k / 100 * 2 * math.pi
        d = 1 + math.sin(t) ** 2
        pts.append((C + 92 * math.cos(t) / d, C + 92 * math.sin(t) * math.cos(t) / d))
    p.lines(pts, col, 22)
    p.lines(pts, (255, 180, 190), 6)
    for (x, y) in ((40, 40), (200, 50), (190, 200), (50, 196)):
        p.poly(gfx.star_points(x, y, 12, 4, 4), (255, 240, 200))


# ---- interfaz / categorías
def i_click(p):
    pts = [(80, 30), (80, 190), (116, 156), (142, 214), (168, 202), (142, 146), (192, 146)]
    p.poly([(x + 6, y + 8) for x, y in pts], (0, 0, 0, 90))
    p.poly(pts, (250, 250, 255))
    p.poly(pts, (40, 40, 60), 6)


def i_chip(p, col=(230, 60, 80)):
    p.circle((C, C + 8), 96, gfx.mul_col(col, 0.6))
    p.circle((C, C), 96, col)
    for k in range(8):
        a = k * math.pi / 4
        p.poly([(C + 96 * math.cos(a - 0.17), C + 96 * math.sin(a - 0.17)),
                (C + 96 * math.cos(a + 0.17), C + 96 * math.sin(a + 0.17)),
                (C + 70 * math.cos(a + 0.2), C + 70 * math.sin(a + 0.2)),
                (C + 70 * math.cos(a - 0.2), C + 70 * math.sin(a - 0.2))], (250, 250, 250))
    p.circle((C, C), 58, gfx.mul_col(col, 0.85))
    p.circle((C, C), 58, (250, 250, 250), 4)
    p.poly(gfx.star_points(C, C, 34, 14), (255, 255, 255))


def i_casino(p):
    i_chip(p)


def i_business(p):
    for k, h in enumerate((60, 100, 140)):
        p.rect((40 + k * 56, 200 - h, 40, h), (64, 220, 140), 8)
    p.lines([(34, 150), (100, 100), (140, 120), (204, 48)], (255, 255, 255), 12)
    p.poly([(214, 30), (214, 76), (176, 44)], (255, 255, 255))


def i_golden(p):
    col = (70, 200, 110)
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        cx, cy = C + 44 * math.cos(a), C - 10 + 44 * math.sin(a)
        p.circle((cx + 18 * math.cos(a + 1.57), cy + 18 * math.sin(a + 1.57)), 32, col)
        p.circle((cx - 18 * math.cos(a + 1.57), cy - 18 * math.sin(a + 1.57)), 32, col)
    p.line((C, C), (C + 30, 222), (50, 150, 80), 12)
    p.circle((C, C - 10), 14, (120, 230, 150))


def i_gear(p):
    col = (200, 200, 220)
    for k in range(8):
        a = k * math.pi / 4
        p.poly([(C + 70 * math.cos(a - 0.22), C + 70 * math.sin(a - 0.22)),
                (C + 100 * math.cos(a - 0.16), C + 100 * math.sin(a - 0.16)),
                (C + 100 * math.cos(a + 0.16), C + 100 * math.sin(a + 0.16)),
                (C + 70 * math.cos(a + 0.22), C + 70 * math.sin(a + 0.22))], col)
    p.circle((C, C), 76, col)
    p.circle((C, C), 34, (0, 0, 0, 0))


def i_sound(p, on=True):
    col = (220, 220, 235)
    p.rect((30, 88, 46, 64), col, 6)
    p.poly([(70, 90), (130, 40), (130, 200), (70, 150)], col)
    if on:
        for k, r in enumerate((40, 70)):
            p.arc((120 - r, C - r, r * 2, r * 2), -0.9, 0.9, col, 12)
    else:
        p.line((158, 86), (214, 154), (255, 92, 104), 14)
        p.line((214, 86), (158, 154), (255, 92, 104), 14)


def i_sound_on(p):
    i_sound(p, True)


def i_sound_off(p):
    i_sound(p, False)


def i_music(p):
    col = (220, 220, 235)
    p.rect((86, 40, 14, 130), col)
    p.rect((176, 24, 14, 130), col)
    p.poly([(86, 40), (190, 18), (190, 50), (86, 72)], col)
    p.ellipse((44, 150, 60, 44), col)
    p.ellipse((134, 134, 60, 44), col)


def i_trophy(p, col=(255, 200, 72)):
    p.rect((76, 186, 88, 26), gfx.mul_col(col, 0.7), 6)
    p.rect((108, 150, 24, 40), gfx.mul_col(col, 0.8))
    p.arc((24, 50, 70, 80), math.pi / 2, math.pi * 1.5, col, 12)
    p.arc((146, 50, 70, 80), -math.pi / 2, math.pi / 2, col, 12)
    p.poly([(60, 34), (180, 34), (170, 110), (C, 160), (70, 110)], col)
    p.ellipse((60, 20, 120, 30), gfx.mul_col(col, 1.15))
    p.poly(gfx.star_points(C, 84, 22, 9), (255, 255, 255))


def i_trophy_off(p):
    i_trophy(p, (90, 90, 115))


def i_crown(p):
    col = (255, 200, 72)
    p.poly([(30, 180), (24, 70), (76, 120), (C, 44), (164, 120), (216, 70), (210, 180)], col)
    p.rect((30, 176, 180, 30), gfx.mul_col(col, 0.8), 6)
    for x, y, c in ((24, 70, (255, 92, 104)), (C, 44, (88, 164, 255)), (216, 70, (64, 220, 140))):
        p.circle((x, y), 14, c)
    p.circle((C, 150), 14, (255, 92, 104))


def i_lock(p):
    col = (150, 148, 180)
    p.arc((70, 30, 100, 110), 0, math.pi, col, 18)
    p.rect((62, 80, 18, 20), col)
    p.rect((160, 80, 18, 20), col)
    p.rect((50, 96, 140, 110), col, 18)
    p.circle((C, 140), 14, (40, 40, 60))
    p.rect((114, 140, 12, 34), (40, 40, 60), 4)


def i_back(p):
    p.lines([(150, 40), (70, 120), (150, 200)], (230, 230, 245), 26)


def i_star(p):
    p.poly(gfx.star_points(C, C + 8, 104, 44), (255, 200, 72))
    p.poly(gfx.star_points(C, C + 8, 60, 26), (255, 232, 150))


def i_stats(p):
    for k, h in enumerate((80, 140, 110, 180)):
        p.rect((28 + k * 50, 210 - h, 36, h), [(88, 164, 255), (176, 120, 255), (64, 220, 140), (255, 200, 72)][k], 8)


def i_bolt(p):
    p.poly([(140, 14), (52, 136), (112, 136), (92, 226), (190, 96), (128, 96)], (255, 214, 80))


def i_coin(p):
    coin(p, (C, C), 100)


def i_cards(p):
    i_blackjack(p)


def i_upgrade(p):
    p.poly([(C, 20), (214, 120), (160, 120), (160, 216), (80, 216), (80, 120), (26, 120)], (64, 220, 140))


def i_vip(p):
    i_crown(p)


def i_clover(p):
    i_golden(p)


# ---- juegos nuevos
def _cup(p, x, y, w, h, col=(214, 60, 50)):
    p.poly([(x - w * 0.36, y - h), (x + w * 0.36, y - h), (x + w * 0.5, y), (x - w * 0.5, y)], col)
    p.poly([(x - w * 0.36, y - h), (x - w * 0.18, y - h), (x - w * 0.26, y), (x - w * 0.5, y)], gfx.mul_col(col, 1.25))
    p.rect((x - w * 0.55, y - 8, w * 1.1, 16), gfx.mul_col(col, 0.7), 6)
    p.rect((x - w * 0.4, y - h - 8, w * 0.8, 12), gfx.mul_col(col, 0.8), 5)


def i_trilero(p):
    _cup(p, 60, 170, 80, 110)
    _cup(p, 180, 170, 80, 110)
    p.circle((C, 196), 20, (250, 250, 250))
    p.circle((C - 6, 190), 6, (255, 255, 255))
    _cup(p, C, 120, 80, 100, (230, 90, 70))


def i_bote(p):
    sub = pygame.Surface((S, S), pygame.SRCALPHA)
    pygame.draw.polygon(sub, (60, 180, 110), [(C, 20), (220, 90), (190, 210), (50, 210), (20, 90)])
    pygame.draw.polygon(sub, (120, 230, 160), [(C, 20), (220, 90), (C, 120), (20, 90)])
    pygame.draw.polygon(sub, (40, 140, 80), [(20, 90), (C, 120), (C, 210), (50, 210)])
    p.s.blit(sub, (0, 0))
    p.text("20", 64, (255, 255, 255), (C, 92))


def i_sicbo(p):
    p.blit_rot(_die(84, 3), (C - 50, C + 40), 12)
    p.blit_rot(_die(84, 5), (C + 50, C + 40), -10)
    p.blit_rot(_die(84, 6, pip=(30, 30, 40)), (C, C - 40), 4)


def i_bingo_game(p):
    for k, col in enumerate(((255, 92, 104), (255, 200, 72), (88, 164, 255))):
        x = 60 + k * 60
        p.circle((x + 4, 170), 44, gfx.mul_col(col, 0.6))
        p.circle((x, 166), 44, col)
        p.circle((x, 166), 24, (255, 255, 255))
        p.text(str([7, 23, 90][k]), 28, (40, 40, 50), (x, 167))
    p.arc((40, 20, 160, 160), 0.3, math.pi - 0.3, (200, 200, 220), 10)


def i_baccarat(p):
    p.blit_rot(card(100, 140, "9", "♦", (210, 30, 50)), (C - 30, C + 6), 12)
    p.blit_rot(card(100, 140, "K", "♠"), (C + 30, C), -8)
    i_chip_small(p)


def i_chip_small(p):
    p.circle((190, 196), 34, (40, 40, 50))
    p.circle((190, 192), 34, (230, 60, 80))
    p.circle((190, 192), 20, (250, 250, 250), 5)


def i_poker(p):
    p.blit_rot(card(96, 136, "A", "♠"), (C - 36, C - 4), 14)
    p.blit_rot(card(96, 136, "A", "♥", (210, 30, 50)), (C + 24, C - 10), -6)
    for k in range(4):
        y = 214 - k * 14
        p.ellipse((116, y - 10, 100, 30), (30, 140, 80) if k % 2 else (230, 60, 80))
        p.ellipse((116, y - 14, 100, 30), (60, 190, 110) if k % 2 else (255, 100, 110))


def i_princess(p):
    p.circle((C, C + 16), 100, (255, 120, 190))
    p.circle((C, C + 22), 70, (255, 220, 196))
    p.poly([(C - 74, C), (C - 30, C - 56), (C + 10, C - 30), (C + 46, C - 60), (C + 76, C),
            (C + 36, C - 18), (C, C - 4), (C - 40, C - 18)], (255, 120, 190))
    p.poly([(C - 50, C - 60), (C - 30, C - 104), (C - 10, C - 74), (C, C - 112), (C + 10, C - 74), (C + 30, C - 104),
            (C + 50, C - 60)], (255, 210, 70))
    for dx in (-28, 28):
        p.ellipse((C + dx - 14, C + 10, 28, 34), (60, 120, 230))
        p.circle((C + dx - 4, C + 18), 6, (255, 255, 255))
    p.poly(gfx.star_points(196, 52, 26, 11), (255, 230, 120))


def i_mail(p):
    paper = (236, 226, 200)
    p.rect((24, 60, 192, 132), paper, 10)
    p.poly([(24, 66), (C, 140), (216, 66)], (200, 186, 152))
    p.lines([(28, 68), (C, 136), (212, 68)], (150, 132, 100), 8)
    p.circle((C, 128), 16, (220, 60, 60))


def i_lastbet(p):
    """Dos botones, rojo y azul."""
    for (x, y), col in (((84, 132), (226, 54, 62)), ((160, 108), (40, 110, 236))):
        p.circle((x, y + 10), 52, (20, 20, 30))
        p.circle((x, y), 50, col)
        p.circle((x - 16, y - 18), 14, (255, 255, 255))


def i_palette(p):
    wood = (226, 176, 112)
    p.poly([(40, 120), (60, 64), (116, 34), (180, 40), (218, 86), (214, 140), (180, 160), (150, 150),
            (128, 168), (140, 200), (110, 214), (64, 196), (36, 160)], wood)
    p.circle((150, 186), 22, (0, 0, 0, 0))
    for (x, y), col in (((86, 76), (255, 92, 104)), ((132, 62), (255, 210, 70)), ((178, 82), (64, 220, 140)),
                        ((186, 128), (88, 164, 255)), ((74, 128), (176, 120, 255))):
        p.circle((x, y), 17, col)
        p.circle((x - 5, y - 5), 5, (255, 255, 255))


_ICON_FUNCS = {k[2:]: v for k, v in globals().items() if k.startswith("i_") and callable(v)}
_cache = {}


def icon(name, size):
    """Icono pixelado con contorno oscuro."""
    key = (name, int(size))
    s = _cache.get(key)
    if s is None:
        size = int(size)
        f = 2 if size >= 40 else 1
        s = gfx.pixelize(_raw(name), (size, size), f)
        _cache[key] = s
    return s


def badge(name, size, col, ring=True):
    """Icono sobre una placa redondeada de color con contorno grueso (estilo carta/joker)."""
    key = ("badge", name, int(size), col, ring)
    s = _cache.get(key)
    if s is None:
        size = int(size)
        s = pygame.Surface((size, size + 4), pygame.SRCALPHA)
        r = max(4, size // 4)
        s.blit(gfx.rrect_surf(size, size, r, (0, 0, 0, 110)), (0, 4))
        s.blit(gfx.rrect_surf(size, size, r, (*col, 255), border=gfx.INK, bw=4), (0, 0))
        s.blit(gfx.rrect_surf(size - 8, max(2, size // 3), max(2, r - 4), (*gfx.mul_col(col, 1.18), 255)), (4, 4))
        ic = icon(name, int(size * 0.72))
        s.blit(ic, ic.get_rect(center=(size // 2, size // 2)))
        _cache[key] = s
    return s


# iconos que salen de una textura pixel art (se escalan sin suavizado)
IMAGE_ICONS = {"pickaxe": ("pickaxe", "pickaxe_3.png")}


def _raw(name):
    key = ("raw", name)
    s = _cache.get(key)
    if s is None and name in IMAGE_ICONS:
        import os
        folder, fn = IMAGE_ICONS[name]
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", folder, fn)
        img = pygame.image.load(path).convert_alpha()
        s = pygame.Surface((S, S), pygame.SRCALPHA)
        big = pygame.transform.scale(img, (int(S * 0.8), int(S * 0.8)))
        s.blit(big, big.get_rect(center=(C, C)))
        _cache[key] = s
        return s
    if s is None:
        p = Pen()
        _ICON_FUNCS.get(name, i_star)(p)
        s = p.s
        _cache[key] = s
    return s
