import math
import random

import pygame

from .base import BaseGame
from .common import dark_panel, controls_bg
from .. import gfx, art
from ..gfx import TEXT, MUTED, DIM, GOLD, GOLD_HI, GREEN

VALUES = [1, 2, 5, 10, 20, 50, 100, 500]
PROBS = {1: 0.170787, 2: 0.085393, 5: 0.032022, 10: 0.014944, 20: 0.005337, 50: 0.001708, 100: 0.000640, 500: 0.000085}   # retorno 95%
GOLD_FACTOR = 1.03   # boleto dorado: 97,9%
VALUE_COLORS = {1: (120, 130, 140), 2: (40, 170, 100), 5: (50, 120, 220), 10: (150, 70, 210), 20: (230, 120, 30),
                50: (220, 50, 60), 100: (230, 60, 160), 500: (200, 150, 20)}
BRUSH = 17


class Scratch(BaseGame):
    gid = "scratch"

    def setup(self):
        self.card = None
        self.last_pt = None
        self.check_t = 0
        self.reveal_anim = {}

    def grid_n(self):
        return 4 if self.state.lvl("scratch_gold") else 3

    def card_rect(self):
        v = self.vis
        return pygame.Rect(v.x + 20, v.y + 10, 560, v.h - 20)

    def cells_rect(self):
        cr = self.card_rect()
        return pygame.Rect(cr.x + 40, cr.y + 120, cr.w - 80, cr.h - 150)

    def cell(self, i, n):
        g = self.cells_rect()
        cw, ch = g.w / n, g.h / n
        r, c = divmod(i, n)
        return pygame.Rect(int(g.x + c * cw + 6), int(g.y + r * ch + 6), int(cw - 12), int(ch - 12))

    def make_outcome(self, n):
        cells = n * n
        factor = GOLD_FACTOR if n == 4 else 1.0
        u = random.random()
        prize, acc = 0, 0.0
        for v in reversed(VALUES):
            acc += PROBS[v] * factor
            if u < acc:
                prize = v
                break
        values = [prize] * 3 if prize else []
        counts = {v: 0 for v in VALUES}
        if prize:
            counts[prize] = 3
        pool = [v for v in VALUES if v != prize]
        while len(values) < cells:
            v = random.choice(pool)
            if counts[v] < 2:
                counts[v] += 1
                values.append(v)
        random.shuffle(values)
        return prize, values

    def buy(self):
        if self.card and not self.card["done"]:
            return
        if not self.take_bet(self.bet):
            return
        n = self.grid_n()
        prize, values = self.make_outcome(n)
        g = self.cells_rect()
        cover = pygame.Surface(g.size, pygame.SRCALPHA)
        for i in range(n * n):
            r = self.cell(i, n).move(-g.x, -g.y)
            silver = gfx.rrect_surf(r.w, r.h, 10, None, grad=((206, 212, 222, 255), (150, 158, 172, 255)))
            cover.blit(silver, r.topleft)
            for k in range(0, r.w, 22):
                pygame.draw.line(cover, (225, 230, 238, 255), (r.x + k, r.y), (r.x + k - 16, r.bottom), 2)
            t = gfx.text_surf("?", 34, "bl", (120, 128, 142))
            cover.blit(t, t.get_rect(center=r.center))
        self.card = {"bet": self.bet, "n": n, "prize": prize, "values": values, "cover": cover,
                     "revealed": [False] * (n * n), "done": False, "t": 0.0}
        self.reveal_anim = {}
        self.audio.play("card0")
        self.show("¡Rasca con el ratón!", TEXT)

    def scratch_at(self, p0, p1):
        g = self.cells_rect()
        cov = self.card["cover"]
        a = (p0[0] - g.x, p0[1] - g.y)
        b = (p1[0] - g.x, p1[1] - g.y)
        d = max(1, int(math.dist(a, b) / 5))
        for k in range(d + 1):
            x = a[0] + (b[0] - a[0]) * k / d
            y = a[1] + (b[1] - a[1]) * k / d
            pygame.draw.circle(cov, (0, 0, 0, 0), (int(x), int(y)), BRUSH)
        if math.dist(a, b) > 2:
            self.audio.play(f"scratch{random.randint(0, 3)}", 0.9, throttle=0.045)
            if random.random() < 0.5:
                self.fx.sparks(p1[0], p1[1], 1, (200, 206, 220), 0.4, 5, 0.4)

    def check_cells(self):
        card = self.card
        g = self.cells_rect()
        n = card["n"]
        for i in range(n * n):
            if card["revealed"][i]:
                continue
            r = self.cell(i, n).move(-g.x, -g.y)
            sub = card["cover"].subsurface(r)
            m = pygame.mask.from_surface(sub, 127)
            if m.count() < r.w * r.h * 0.5:
                self.reveal(i)
        if all(card["revealed"]):
            self.finish()

    def reveal(self, i):
        card = self.card
        card["revealed"][i] = True
        g = self.cells_rect()
        r = self.cell(i, card["n"]).move(-g.x, -g.y)
        pygame.draw.rect(card["cover"], (0, 0, 0, 0), r)
        self.reveal_anim[i] = 0.0
        v = card["values"][i]
        self.audio.play(f"pop{min(9, VALUES.index(v) + 2)}", 0.6, throttle=0.02)

    def reveal_all(self):
        if not self.card or self.card["done"]:
            return
        for i in range(len(self.card["revealed"])):
            if not self.card["revealed"][i]:
                self.reveal(i)
        self.finish()

    def finish(self):
        card = self.card
        if card["done"]:
            return
        card["done"] = True
        prize = card["prize"]
        if prize == VALUES[-1]:
            self.feat("scratch_top")
        cr = self.card_rect()
        self.pay(card["bet"], card["bet"] * prize, label=f"¡Tres x{prize}!" if prize else "Sin premio",
                 pos=(cr.centerx, cr.y + 80))

    def update(self, dt):
        for k in list(self.reveal_anim):
            self.reveal_anim[k] += dt
        if self.card:
            self.card["t"] += dt

    def draw(self, surf, rect):
        ui = self.ui
        cr = self.card_rect()
        gold = self.state.lvl("scratch_gold")
        n = self.card["n"] if self.card else self.grid_n()
        top, bot = ((255, 214, 90), (220, 150, 40)) if gold else ((70, 210, 190), (30, 140, 130))
        gfx.shadow(surf, cr, 24, 16, 140, (0, 10))
        gfx.rrect(surf, cr, None, 24, border=(255, 255, 255), bw=3, grad=((*top, 255), (*bot, 255)))
        for k in range(14):
            x = cr.x + 30 + k * 38
            gfx.aa_poly(surf, (255, 255, 255, 140), gfx.star_points(x, cr.y + 26, 7, 3))
        gfx.text(surf, "RASCA Y GANA" + (" DORADO" if gold else ""), (cr.centerx, cr.y + 60), 30, "bl", (30, 30, 50),
                 anchor="center")
        gfx.text(surf, "¡Encuentra 3 premios iguales!", (cr.centerx, cr.y + 92), 14, "b", (40, 50, 60),
                 anchor="center")
        g = self.cells_rect()
        gfx.rrect(surf, g.inflate(12, 12), (255, 255, 255, 120), 14)
        card = self.card
        for i in range(n * n):
            r = self.cell(i, n)
            gfx.rrect(surf, r, (252, 252, 248, 255), 10, border=(210, 210, 214), bw=1)
            if card:
                v = card["values"][i]
                winner = card["done"] and card["prize"] and v == card["prize"]
                ra = self.reveal_anim.get(i)
                sc = gfx.ease_out_back(min(1, ra / 0.35)) if ra is not None else 1.0
                if winner:
                    gfx.glow(surf, r.center, 60, (255, 200, 60), 0.5 + 0.2 * math.sin(card["t"] * 6))
                    gfx.rrect(surf, r, (255, 246, 190, 255), 10, border=(255, 190, 40), bw=3)
                col = VALUE_COLORS[v]
                img = gfx.text_surf(f"x{v}", 30 if n == 3 else 24, "bl", col)
                gfx.blit_center(surf, gfx.scaled(img, max(0.05, sc)), r.center)
        if card:
            surf.blit(card["cover"], g.topleft)
            # rascar
            if not card["done"] and ui.down and ui.hover(g):
                p = (ui.mx, ui.my)
                self.scratch_at(self.last_pt or p, p)
                self.last_pt = p
                self.check_t += ui.dt
                if self.check_t > 0.08:
                    self.check_t = 0
                    self.check_cells()
            else:
                self.last_pt = None
            if ui.hover(g) and not card["done"]:
                ui.hot_any = True
                surf.blit(art.small_coin(36), (ui.mx - 8, ui.my - 30))
        else:
            ov = pygame.Surface(g.size, pygame.SRCALPHA)
            ov.fill((40, 40, 60, 150))
            surf.blit(ov, g.topleft)
            gfx.text(surf, "Compra un boleto para empezar", g.center, 18, "b", TEXT, anchor="center")
        # premios
        pr = pygame.Rect(cr.right + 16, self.vis.y + 10, self.vis.right - cr.right - 16, self.vis.h - 20)
        dark_panel(surf, pr, 18)
        gfx.text(surf, "PREMIOS", (pr.x + 18, pr.y + 16), 15, "bl", GOLD)
        gfx.text(surf, "3 iguales", (pr.right - 16, pr.y + 20), 11, "sb", MUTED, anchor="topright")
        for k, v in enumerate(reversed(VALUES)):
            y = pr.y + 52 + k * 44
            rr = pygame.Rect(pr.x + 14, y, pr.w - 28, 36)
            hit = card and card["done"] and card["prize"] == v
            gfx.rrect(surf, rr, (*(gfx.mul_col(VALUE_COLORS[v], 0.35) if not hit else (120, 90, 20)), 255), 10)
            gfx.text(surf, f"x{v}", (rr.x + 14, rr.centery), 18, "bl", gfx.mul_col(VALUE_COLORS[v], 1.4),
                     anchor="midleft")
            gfx.text(surf, "premio máx." if v == VALUES[-1] else "", (rr.right - 12, rr.centery), 10, "r", MUTED,
                     anchor="midright")
        # controles
        c = self.controls_rect(rect)
        controls_bg(surf, c)
        self.bet_control(surf, c.x + 16, c.y + 12, "PRECIO DEL BOLETO")
        can_buy = not card or card["done"]
        if ui.button("reveal", (c.right - 390, c.y + 22, 170, 56), "Rascar todo", "dark",
                     enabled=bool(card and not card["done"]), size=16):
            self.reveal_all()
        if ui.button("buy", (c.right - 200, c.y + 18, 180, 64), "COMPRAR", "green", enabled=can_buy, size=20,
                     sound=None):
            self.buy()
