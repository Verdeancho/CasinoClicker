import math
import random

import pygame

from .base import BaseGame
from .common import dark_panel, controls_bg
from .. import gfx
from ..fmt import fmt_num
from ..gfx import TEXT, MUTED, DIM, GOLD, GREEN

TABLES = {
    8: {"Bajo": [5.6, 2.1, 1.1, 1, 0.5, 1, 1.1, 2.1, 5.6],
        "Medio": [13, 3, 1.3, 0.7, 0.4, 0.7, 1.3, 3, 13],
        "Alto": [29, 4, 1.5, 0.3, 0.2, 0.3, 1.5, 4, 29]},
    12: {"Bajo": [10, 3, 1.6, 1.4, 1.1, 1, 0.5, 1, 1.1, 1.4, 1.6, 3, 10],
         "Medio": [33, 11, 4, 2, 1.1, 0.6, 0.3, 0.6, 1.1, 2, 4, 11, 33],
         "Alto": [170, 24, 8.1, 2, 0.7, 0.2, 0.2, 0.2, 0.7, 2, 8.1, 24, 170]},
    16: {"Bajo": [16, 9, 2, 1.4, 1.4, 1.2, 1.1, 1, 0.5, 1, 1.1, 1.2, 1.4, 1.4, 2, 9, 16],
         "Medio": [110, 41, 10, 5, 3, 1.5, 1, 0.5, 0.3, 0.5, 1, 1.5, 3, 5, 10, 41, 110],
         "Alto": [1000, 130, 26, 9, 4, 2, 0.2, 0.2, 0.2, 0.2, 0.2, 2, 4, 9, 26, 130, 1000]},
}
RISKS = ["Bajo", "Medio", "Alto"]
SEG_T = 0.105


class Plinko(BaseGame):
    gid = "plinko"

    def setup(self):
        self.rows = 12
        self.risk = "Medio"
        self.balls = []
        self.pending = 0
        self.peg_hit = {}
        self.bucket_hit = {}
        self.recent = []

    def geom(self):
        v = self.vis
        top = v.y + 40
        bottom = v.bottom - 56
        gap = min(46, (v.w - 260) / (self.rows + 2))
        rh = (bottom - top) / self.rows
        return v.centerx - 40, top, gap, rh, bottom

    def peg(self, r, j):
        cx, top, gap, rh, _ = self.geom()
        return cx + (j - (r + 2) / 2) * gap, top + r * rh

    def bucket_x(self, k):
        cx, top, gap, rh, bottom = self.geom()
        return cx + (k - self.rows / 2) * gap

    def bucket_color(self, k):
        d = abs(k - self.rows / 2) / (self.rows / 2)
        return gfx.lerp_col((255, 214, 80), (255, 70, 100), d)

    def drop(self, count):
        if count > 1 and not self.state.lvl("plinko_rain"):
            return
        for i in range(count):
            if not self.take_bet(self.bet):
                break
            self.pending += 1
            self.later(i * 0.09, lambda b=self.bet: self.spawn(b))

    def spawn(self, bet):
        self.pending -= 1
        cx, top, gap, rh, bottom = self.geom()
        rights = 0
        pts = [(cx + random.uniform(-4, 4), top - 34)]
        path = []
        for r in range(self.rows):
            pts.append((cx + (rights - r / 2) * gap, top + r * rh - 10))
            path.append((r, rights + 1))
            rights += random.randint(0, 1)
        pts.append((cx + (rights - self.rows / 2) * gap, bottom - 6))
        self.balls.append({"pts": pts, "path": path, "t": 0.0, "k": rights, "bet": bet, "rows": self.rows,
                           "risk": self.risk, "trail": [], "seg": -1, "hue": random.choice(
                               [(255, 90, 170), (255, 120, 200), (255, 70, 150)])})

    def update(self, dt):
        done = []
        for b in self.balls:
            b["t"] += dt
            seg = int(b["t"] / SEG_T)
            if seg != b["seg"]:
                if 0 <= seg - 1 < len(b["path"]) and seg - 1 >= 0:
                    r, j = b["path"][seg - 1]
                    self.peg_hit[(r, j)] = 0.0
                    self.audio.play(f"peg{random.randint(0, 7)}", 0.8, pan=(b["pts"][seg][0] - self.vis.centerx) / 500,
                                    throttle=0.012)
                b["seg"] = seg
            if seg >= len(b["pts"]) - 1:
                done.append(b)
                continue
            f = (b["t"] - seg * SEG_T) / SEG_T
            (x1, y1), (x2, y2) = b["pts"][seg], b["pts"][seg + 1]
            x = x1 + (x2 - x1) * f
            y = y1 + (y2 - y1) * f * f - 12 * math.sin(math.pi * f) * (0.3 if seg == 0 else 1)
            b["pos"] = (x, y)
            b["trail"].append((x, y))
            del b["trail"][:-7]
        for b in done:
            self.balls.remove(b)
            self.land(b)
        for k in list(self.peg_hit):
            self.peg_hit[k] += dt
            if self.peg_hit[k] > 0.4:
                del self.peg_hit[k]
        for k in list(self.bucket_hit):
            self.bucket_hit[k] += dt
            if self.bucket_hit[k] > 0.5:
                del self.bucket_hit[k]

    def land(self, b):
        k = b["k"]
        m = TABLES[b["rows"]][b["risk"]][k]
        self.bucket_hit[k] = 0.0
        tier = 0 if m < 1 else 1 if m < 1.5 else 2 if m < 4 else 3 if m < 15 else 4 if m < 100 else 5
        self.audio.play(f"land{tier}", 0.8, throttle=0.03)
        self.recent.append((f"x{fmt_num(m, 1)}", self.bucket_color(k)))
        if k in (0, b["rows"]):
            self.feat("plinko_edge")
        x = self.bucket_x(k)
        payout = self.state.settle(self.gid, b["bet"], b["bet"] * m, count_streak=m != 1)
        net = payout - b["bet"]
        self.fx.text(x, self.geom()[4] - 30, f"x{fmt_num(m, 1)}", GREEN if net > 0 else (255, 120, 140), 16, 0.8, 40)
        if m >= 10:
            self.fx.sparks(x, self.geom()[4], 30, self.bucket_color(k), 1.5)
            self.audio.play("win2" if m < 100 else "win3")
            self.show(f"¡x{fmt_num(m)}!  +{fmt_num(net)} €", GOLD, big=m >= 100)
        if m >= 100:
            self.fx.confetti(self.vis.centerx, self.vis.y, 120, w=self.vis.w)

    def draw(self, surf, rect):
        ui = self.ui
        v = self.vis
        dark_panel(surf, v, 20, (26, 16, 48), (10, 8, 22))
        cx, top, gap, rh, bottom = self.geom()
        gfx.glow(surf, (cx, top + (bottom - top) / 2), 300, (90, 40, 140), 0.35)
        pr = max(3, int(gap * 0.11))
        for r in range(self.rows):
            for j in range(r + 3):
                x, y = self.peg(r, j)
                hit = self.peg_hit.get((r, j))
                if hit is not None:
                    k = 1 - hit / 0.4
                    gfx.glow(surf, (x, y), int(18 + 10 * k), (255, 120, 200), 0.8 * k)
                    gfx.circle(surf, (x, y), pr + 2 * k, (255, 230, 245))
                else:
                    gfx.circle(surf, (x, y), pr, (220, 214, 240))
        tbl = TABLES[self.rows][self.risk]
        for k, m in enumerate(tbl):
            x = self.bucket_x(k)
            hit = self.bucket_hit.get(k)
            dy = int(math.sin(min(1, hit / 0.5) * math.pi) * 8) if hit is not None else 0
            br = pygame.Rect(0, 0, int(gap - 4), 30)
            br.center = (int(x), int(bottom + 10 + dy))
            col = self.bucket_color(k)
            if hit is not None:
                gfx.glow(surf, br.center, 40, col, 0.6 * (1 - hit / 0.5))
            gfx.rrect(surf, br, None, 7, grad=((*gfx.mul_col(col, 1.15), 255), (*gfx.mul_col(col, 0.7), 255)))
            gfx.text(surf, fmt_num(m, 1) if m < 10 else fmt_num(m, 0), br.center, 10 if self.rows == 16 else 12, "bl",
                     (40, 14, 20), anchor="center")
        for b in self.balls:
            if "pos" not in b:
                continue
            for i, (tx, ty) in enumerate(b["trail"]):
                a = (i + 1) / len(b["trail"])
                gfx.circle(surf, (tx, ty), 3 + 4 * a, (*b["hue"], int(70 * a)))
            gfx.glow(surf, b["pos"], 26, b["hue"], 0.6)
            gfx.circle(surf, b["pos"], 8, b["hue"], border=(255, 220, 240), bw=2)
        # panel derecho: últimos resultados
        n = self.rows
        gfx.text(surf, f"{n} filas · riesgo {self.risk}", (v.x + 22, v.y + 18), 13, "b", MUTED)
        ry = v.y + (66 if self.state.lvl("plinko_rain") else 20)
        for i, (txt, col) in enumerate(self.recent[-12:][::-1]):
            r = pygame.Rect(v.right - 86, ry + i * 34, 66, 28)
            if r.bottom > v.bottom - 70:
                break
            a = 255 - i * 16
            gfx.rrect(surf, r, (*gfx.mul_col(col, 0.7), 255), 8, alpha=a)
            gfx.text(surf, txt, r.center, 12, "bl", (30, 10, 16), anchor="center", alpha=a)
        # controles
        c = self.controls_rect(rect)
        controls_bg(surf, c)
        self.bet_control(surf, c.x + 16, c.y + 12, "APUESTA POR BOLA")
        locked = bool(self.balls or self.pending)
        gfx.text(surf, "FILAS", (c.x + 376, c.y + 12), 12, "b", MUTED)
        sel = ui.segmented("pl_rows", (c.x + 376, c.y + 32, 132, 38), ["8", "12", "16"], [8, 12, 16].index(self.rows), 14)
        if not locked:
            self.rows = [8, 12, 16][sel]
        gfx.text(surf, "RIESGO", (c.x + 520, c.y + 12), 12, "b", MUTED)
        sel = ui.segmented("pl_risk", (c.x + 520, c.y + 32, 180, 38), RISKS, RISKS.index(self.risk), 13)
        if not locked:
            self.risk = RISKS[sel]
        keys = ui.keys if not ui.focus else []
        if ui.button("drop", (c.right - 160, c.y + 18, 140, 64), "SOLTAR", "pink", size=19, sound=None) or \
                pygame.K_SPACE in keys:
            self.drop(1)
        if self.state.lvl("plinko_rain"):
            if ui.button("rain", (v.right - 156, v.y + 16, 140, 40), "Lluvia x10", "primary", size=14, sound=None):
                self.drop(10)
