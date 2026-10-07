"""Bingo exprés (90 bolas, cartones españoles 3x9): se sacan 55 bolas del bombo.

Premio por cartón (solo el mayor): 1 línea x3 · 2 líneas x16 · BINGO x380.
Probabilidades exactas con 55 bolas: 20,76% · 1,456% · 0,026% → retorno 95,5%."""
import math
import random

import pygame

from .base import BaseGame
from .common import felt, controls_bg, toggle_pill
from .. import gfx
from ..fmt import fmt_money
from ..gfx import TEXT, MUTED, DIM, GOLD, GOLD_HI, GREEN, RED, ORANGE, PANEL_LO, LINE

DRAWS = 55
PRIZES = {1: 3, 2: 16, 3: 380}
BALL_COLS = [(255, 92, 104), (255, 170, 60), (255, 214, 80), (78, 196, 146), (0, 157, 255), (150, 112, 196),
             (244, 112, 170), (80, 204, 214), (190, 190, 200)]


def ball_color(n):
    return BALL_COLS[min(8, (n - 1) // 10)]


def make_card(rng):
    while True:
        counts = [1] * 9
        extra = 6
        while extra:
            c = rng.randrange(9)
            if counts[c] < 3:
                counts[c] += 1
                extra -= 1
        rows = [[None] * 9 for _ in range(3)]
        rs = [0, 0, 0]
        ok = True
        for c in sorted(range(9), key=lambda c: -counts[c]):
            avail = sorted(range(3), key=lambda r: (rs[r], rng.random()))
            chosen = avail[:counts[c]]
            for r in chosen:
                if rs[r] >= 5:
                    ok = False
                rs[r] += 1
            if not ok:
                break
            lo = 1 if c == 0 else c * 10
            hi = 9 if c == 0 else (90 if c == 8 else c * 10 + 9)
            nums = sorted(rng.sample(range(lo, hi + 1), counts[c]))
            for r, n in zip(sorted(chosen), nums):
                rows[r][c] = n
        if ok and rs == [5, 5, 5]:
            return rows


class Bingo(BaseGame):
    gid = "bingo"

    def setup(self):
        self.rng = random.Random()
        self.n_cards = 1
        self.cards = [make_card(self.rng)]
        self.drawn = []
        self.drawn_set = set()
        self.queue = []
        self.playing = False
        self.timer = 0.0
        self.turbo = False
        self.marks = {}
        self.lines = []
        self.pbet = 0.0
        self.angle = 0.0
        self.balls = [{"x": random.uniform(-60, 60), "y": random.uniform(-60, 60), "vx": random.uniform(-80, 80),
                       "vy": random.uniform(-80, 80), "n": random.randint(1, 90)} for _ in range(26)]
        self.flying = None
        self.big_ball = None

    def max_cards(self):
        return 2 + self.state.lvl("bingo_cards")

    def start(self):
        if self.playing:
            return
        total = self.bet * self.n_cards
        if not self.take_bet(total):
            return
        self.pbet = total
        self.cards = [make_card(self.rng) for _ in range(self.n_cards)]
        self.drawn = []
        self.drawn_set = set()
        self.queue = self.rng.sample(range(1, 91), DRAWS)
        self.marks = {}
        self.lines = [0] * self.n_cards
        self.playing = True
        self.timer = 0.0
        self.banner = None
        self.audio.play("spin_start")

    def card_lines(self, card):
        return sum(1 for row in card if all(n is None or n in self.drawn_set for n in row))

    def draw_ball(self):
        n = self.queue.pop(0)
        self.drawn.append(n)
        self.drawn_set.add(n)
        self.flying = {"n": n, "t": 0.0}
        self.audio.play("ball_pop", 0.8)
        hit = False
        for ci, card in enumerate(self.cards):
            for r in range(3):
                for c in range(9):
                    if card[r][c] == n:
                        self.marks[(ci, r, c)] = 0.0
                        hit = True
            new = self.card_lines(card)
            if new > self.lines[ci]:
                self.lines[ci] = new
                if new == 3:
                    self.feat("bingo_full")
                    if len(self.drawn) < 40:
                        self.feat("bingo_fast")
                    self.show("¡¡BINGO!!", GOLD_HI, big=True)
                    self.audio.play("win3")
                    self.fx.confetti(self.vis.centerx, self.vis.y, 160, w=self.vis.w)
                else:
                    self.feat("bingo_line")
                    self.show("¡LÍNEA!" if new == 1 else "¡DOS LÍNEAS!", GREEN)
                    self.audio.play("win1" if new == 1 else "win2")
        if hit:
            self.audio.play("keno_hit", 0.5, throttle=0.05)

    def finish(self):
        self.playing = False
        gross = sum(PRIZES.get(l, 0) for l in self.lines) * self.bet
        best = max(self.lines) if self.lines else 0
        label = {0: "Sin premio", 1: "Línea", 2: "Dos líneas", 3: "¡BINGO!"}[best]
        self.pay(self.pbet, gross, label=label)

    def update(self, dt):
        spin = 3.0 if self.playing else 0.6
        self.angle += dt * spin
        R = 108
        for b in self.balls:
            b["vy"] += 400 * dt
            # empuje del giro
            b["vx"] += -b["y"] * spin * 0.9 * dt * 4
            b["vy"] += b["x"] * spin * 0.9 * dt * 4
            b["x"] += b["vx"] * dt
            b["y"] += b["vy"] * dt
            d = math.hypot(b["x"], b["y"])
            if d > R - 12:
                nx, ny = b["x"] / d, b["y"] / d
                b["x"], b["y"] = nx * (R - 12), ny * (R - 12)
                dot = b["vx"] * nx + b["vy"] * ny
                b["vx"] -= 1.8 * dot * nx
                b["vy"] -= 1.8 * dot * ny
        if self.flying:
            self.flying["t"] += dt * (2.5 if self.turbo else 1.4)
            if self.flying["t"] >= 1:
                self.big_ball = self.flying["n"]
                self.flying = None
        for k in list(self.marks):
            self.marks[k] += dt
        if not self.playing:
            return
        self.timer += dt
        interval = 0.09 if self.turbo else 0.32
        if self.timer >= interval and self.queue:
            self.timer = 0.0
            if all(l == 3 for l in self.lines):
                self.queue = []
            else:
                self.draw_ball()
        if not self.queue and self.timer > 0.6:
            self.finish()

    # ----------------------------------------------------------------- dibujo
    def bombo_center(self):
        return (self.vis.x + 150, self.vis.y + 150)

    def draw(self, surf, rect):
        ui = self.ui
        v = self.vis
        felt(surf, v, (44, 70, 120), (230, 200, 140))
        cx, cy = self.bombo_center()
        R = 108
        # soporte
        gfx.rrect(surf, (cx - 16, cy + R - 4, 32, 70), (120, 90, 50, 255), 4, border=LINE, bw=4)
        gfx.rrect(surf, (cx - 70, cy + R + 56, 140, 18), (120, 90, 50, 255), 4, border=LINE, bw=4)
        gfx.circle(surf, (cx, cy), R + 4, (30, 40, 70), border=LINE, bw=4)
        for b in self.balls:
            gfx.circle(surf, (cx + b["x"], cy + b["y"]), 11, ball_color(b["n"]), border=LINE, bw=2)
        # radios de la jaula
        for k in range(8):
            a = self.angle + k * math.tau / 8
            x1, y1 = cx + math.cos(a) * (R + 2), cy + math.sin(a) * (R + 2)
            x2, y2 = cx - math.cos(a) * (R + 2), cy - math.sin(a) * (R + 2)
            pygame.draw.line(surf, (210, 190, 120), (x1, y1), (x2, y2), 3)
        pygame.draw.circle(surf, (230, 210, 140), (cx, cy), R + 4, 6)
        gfx.circle(surf, (cx, cy), 14, (230, 210, 140), border=LINE, bw=3)
        # bola volando y bola grande
        if self.flying:
            t = self.flying["t"]
            x = cx + R * 0.2 + t * 170
            y = cy + R - math.sin(t * math.pi) * 120 + t * 40
            gfx.circle(surf, (x, y), 18, ball_color(self.flying["n"]), border=LINE, bw=3)
        bb = pygame.Rect(v.x + 260, v.y + 230, 90, 90)
        if self.big_ball:
            gfx.circle(surf, bb.center, 44, ball_color(self.big_ball), border=LINE, bw=4)
            gfx.circle(surf, bb.center, 28, (255, 255, 255))
            gfx.text(surf, str(self.big_ball), bb.center, 18, "bl", (30, 30, 40), anchor="center")
        gfx.text(surf, f"BOLA {len(self.drawn)}/{DRAWS}", (v.x + 30, v.y + 330), 14, "b", TEXT)
        # últimas bolas
        for i, n in enumerate(self.drawn[-8:][::-1]):
            p = (v.x + 40 + i * 34, v.y + 372)
            gfx.circle(surf, p, 15, ball_color(n), border=LINE, bw=2)
            gfx.text(surf, str(n), p, 10, "b", (20, 20, 30), anchor="center")
        gfx.text_wrapped(surf, f"Premios por cartón: línea x{PRIZES[1]} · dos líneas x{PRIZES[2]} · "
                               f"BINGO x{PRIZES[3]}", (v.x + 24, v.y + 404), 12, "r", (220, 226, 240), 320)
        # cartones
        n = len(self.cards)
        area = pygame.Rect(v.x + 370, v.y + 16, v.w - 390, v.h - 32)
        cols = 1 if n <= 2 else 2
        rows = (n + cols - 1) // cols
        cw = area.w // cols - 10
        chh = min(area.h // rows - 10, int(cw / 9 * 3) + 46)
        for ci, card in enumerate(self.cards):
            cr = pygame.Rect(area.x + (ci % cols) * (cw + 10), area.y + (ci // cols) * (chh + 10), cw, chh)
            l = self.lines[ci] if ci < len(self.lines) else 0
            gfx.box(surf, cr, (*((90, 70, 20) if l == 3 else (238, 232, 216)), 255), 10, ow=4, shadow_off=5)
            gfx.text(surf, f"CARTÓN {ci + 1}", (cr.x + 14, cr.y + 18), 12, "b", (60, 50, 40) if l < 3 else TEXT,
                     anchor="midleft")
            if l:
                gfx.text(surf, {1: "LÍNEA", 2: "2 LÍNEAS", 3: "BINGO"}[l], (cr.right - 14, cr.y + 18), 12, "b",
                         GREEN if l < 3 else GOLD_HI, anchor="midright")
            cell = min((cr.w - 20) / 9, (cr.h - 40) / 3)
            gx = cr.x + (cr.w - cell * 9) / 2
            gy = cr.y + 34
            for r in range(3):
                for c in range(9):
                    rr = pygame.Rect(int(gx + c * cell) + 1, int(gy + r * cell) + 1, int(cell) - 2, int(cell) - 2)
                    num = card[r][c]
                    if num is None:
                        gfx.rrect(surf, rr, (200, 70, 80, 255), 3)
                        continue
                    gfx.rrect(surf, rr, (255, 255, 250, 255), 3, border=(150, 140, 120), bw=2)
                    gfx.text(surf, str(num), rr.center, 12 if cell > 30 else 10, "b", (40, 40, 50), anchor="center",
                             shadow=False)
                    mk = self.marks.get((ci, r, c))
                    if mk is not None:
                        k = gfx.ease_out_back(min(1, mk / 0.25))
                        rad = max(2, int(cell * 0.42 * k))
                        gfx.circle(surf, rr.center, rad, (230, 60, 90, 170) if True else None)
        # controles
        c = self.controls_rect(rect)
        controls_bg(surf, c)
        self.bet_control(surf, c.x + 16, c.y + 10, "PRECIO POR CARTÓN")
        gfx.text(surf, "CARTONES", (c.x + 372, c.y + 12), 12, "b", MUTED)
        opts = [str(i) for i in range(1, self.max_cards() + 1)]
        sel = ui.segmented("bingo_n", (c.x + 372, c.y + 32, 46 * len(opts) + 8, 50), opts, self.n_cards - 1, 14)
        if not self.playing and sel + 1 != self.n_cards:
            self.n_cards = sel + 1
            self.cards = [make_card(self.rng) for _ in range(self.n_cards)]
            self.lines = []
            self.marks = {}
        self.turbo = toggle_pill(ui, ("bingo", "turbo"), surf, (c.x + 392 + 46 * len(opts), c.y + 44, 110, 30),
                                 "Turbo", self.turbo)
        keys = ui.keys if not ui.focus else []
        if ui.button("go", (c.right - 170, c.y + 18, 154, 70), "JUGAR", "gold", enabled=not self.playing, size=16,
                     sub=fmt_money(self.bet * self.n_cards), sound=None) or (pygame.K_SPACE in keys and not self.playing):
            self.start()
