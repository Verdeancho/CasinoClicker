import math
import random

import pygame

from .base import BaseGame
from .common import dark_panel, controls_bg
from .. import gfx
from ..fmt import fmt_num
from ..gfx import TEXT, MUTED, DIM, GOLD, GOLD_HI, GREEN, BLUE

POOL = 40
DRAWS = 10
MAX_PICKS = 10
TARGET_RTP = 0.95
COLS = 8


def hypergeom(n_picks, hits, draws=DRAWS):
    return math.comb(n_picks, hits) * math.comb(POOL - n_picks, draws - hits) / math.comb(POOL, draws)


def _nice(x):
    if x < 10:
        return round(x * 10) / 10
    if x < 100:
        return round(x)
    mag = 10 ** (int(math.log10(x)) - 1)
    return round(x / mag) * mag


def build_paytables(draws, target):
    tables = {}
    for n in range(1, MAX_PICKS + 1):
        min_hits = 1 if n <= 2 else (2 if n <= 4 else math.ceil(n * 0.45))
        raw = {h: (1 / hypergeom(n, h, draws)) ** 0.72 for h in range(min_hits, n + 1)}
        rtp = sum(hypergeom(n, h, draws) * v for h, v in raw.items())
        k = target / rtp
        tables[n] = {h: _nice(v * k) for h, v in raw.items()}
    return tables


PAYTABLES = build_paytables(DRAWS, TARGET_RTP)
PAYTABLES_EXTRA = build_paytables(DRAWS + 1, 0.96)


class Keno(BaseGame):
    gid = "keno"

    def setup(self):
        self.picks = set()
        self.drawn = []
        self.drawn_t = {}
        self.queue = []
        self.drawing = False
        self.dt_acc = 0.0
        self.pbet = 0.0

    def n_draws(self):
        return DRAWS + (1 if self.state.lvl("keno_extra") else 0)

    def paytable(self, n):
        return (PAYTABLES_EXTRA if self.state.lvl("keno_extra") else PAYTABLES)[n]

    def ball_pos(self, n):
        v = self.vis
        i = n - 1
        r, c = divmod(i, COLS)
        return v.x + 50 + c * 66, v.y + 110 + r * 66

    def play(self):
        if self.drawing:
            return
        if not self.picks:
            self.show("Elige al menos un número", MUTED)
            return
        if not self.take_bet(self.bet):
            return
        self.pbet = self.bet
        self.drawn = []
        self.drawn_t = {}
        self.queue = random.sample(range(1, POOL + 1), self.n_draws())
        self.drawing = True
        self.dt_acc = 0.15
        self.banner = None

    def update(self, dt):
        for k in list(self.drawn_t):
            self.drawn_t[k] += dt
        if not self.drawing:
            return
        self.dt_acc += dt
        if self.dt_acc >= 0.2 and self.queue:
            self.dt_acc = 0
            n = self.queue.pop(0)
            self.drawn.append(n)
            self.drawn_t[n] = 0.0
            hit = n in self.picks
            self.audio.play("keno_hit" if hit else f"pop{random.randint(0, 9)}", 0.9 if hit else 0.7)
            if hit:
                x, y = self.ball_pos(n)
                self.fx.sparks(x, y, 14, (255, 220, 120), 0.9)
        if not self.queue and self.dt_acc > 0.35:
            self.drawing = False
            self.finish()

    def finish(self):
        hits = len(self.picks & set(self.drawn))
        m = self.paytable(len(self.picks)).get(hits, 0)
        if hits >= 8:
            self.state.set_flag("keno_8")
        self.pay(self.pbet, self.pbet * m, label=f"{hits} acierto{'s' if hits != 1 else ''}")

    def draw(self, surf, rect):
        ui = self.ui
        v = self.vis
        dark_panel(surf, v, 20, (14, 26, 52), (8, 14, 30))
        # bandeja de bolas sorteadas
        tray = pygame.Rect(v.x + 20, v.y + 18, 566, 56)
        gfx.rrect(surf, tray, (6, 10, 22, 255), 28, border=(50, 70, 120), bw=1)
        for i, n in enumerate(self.drawn):
            t = self.drawn_t.get(n, 1)
            k = gfx.ease_out_back(min(1, t / 0.35))
            x = tray.x + 28 + i * 51 if len(self.drawn) <= 10 else tray.x + 26 + i * 46.5
            y = tray.centery - (1 - min(1, t / 0.25)) * 40
            hit = n in self.picks
            col = (255, 200, 60) if hit else (230, 70, 80)
            r = max(2, int(21 * k))
            gfx.circle(surf, (x + 1, y + 3), r, (0, 0, 0, 110))
            gfx.circle(surf, (x, y), r, col)
            gfx.circle(surf, (x, y), max(1, r - 7), (255, 255, 255))
            if k > 0.6:
                gfx.text(surf, str(n), (x, y), 13, "bl", (30, 30, 40), anchor="center")
        # rejilla de números
        drawn = set(self.drawn)
        for n in range(1, POOL + 1):
            x, y = self.ball_pos(n)
            r = pygame.Rect(x - 29, y - 29, 58, 58)
            picked = n in self.picks
            is_drawn = n in drawn
            wid = ("keno", n)
            h = ui.hover(r) and not self.drawing
            hv = ui.anim(wid, 1.0 if h else 0.0, 18)
            if picked and is_drawn:
                col, fg = (255, 200, 60), (40, 26, 6)
                t = self.drawn_t.get(n, 1)
                gfx.glow(surf, (x, y), 46, (255, 190, 60), 0.4 + 0.2 * math.sin(ui.t * 5 + n))
                sc = 1 + 0.25 * max(0, 1 - t / 0.3)
            elif is_drawn:
                col, fg = (200, 60, 72), TEXT
                sc = 1.0
            elif picked:
                col, fg = (70, 140, 255), TEXT
                sc = 1.0
            else:
                col, fg = gfx.lerp_col((32, 46, 80), (52, 70, 120), hv), (170, 190, 220)
                sc = 1.0
            rad = int(27 * sc + 2 * hv)
            gfx.circle(surf, (x, y + 3), rad, (0, 0, 0, 90))
            gfx.circle(surf, (x, y), rad, col, border=gfx.mul_col(col, 1.4), bw=2)
            gfx.circle(surf, (x - rad * 0.3, y - rad * 0.35), max(2, rad * 0.25), (*gfx.mul_col(col, 1.5), 120))
            gfx.text(surf, str(n), (x, y), 17, "bl", fg, anchor="center")
            if h:
                ui.hot_any = True
                if ui.pressed:
                    ui.active = wid
                if ui.released and ui.active == wid:
                    if self.drawn:
                        self.drawn = []
                        self.drawn_t = {}
                    if n in self.picks:
                        self.picks.discard(n)
                        self.audio.play("tick2", 0.8)
                    elif len(self.picks) < MAX_PICKS:
                        self.picks.add(n)
                        self.audio.play(f"pop{min(9, len(self.picks) - 1)}", 0.8)
        # tabla de pagos
        pr = pygame.Rect(v.x + 600, v.y + 18, v.w - 620, v.h - 36)
        dark_panel(surf, pr, 16, (24, 38, 72), (14, 22, 44))
        n = len(self.picks)
        gfx.text(surf, f"Elegidos {n}/{MAX_PICKS}", (pr.x + 18, pr.y + 16), 16, "bl", TEXT)
        gfx.text(surf, f"se sortean {self.n_draws()} bolas", (pr.x + 18, pr.y + 44), 12, "r", MUTED)
        if n:
            hits = len(self.picks & drawn) if self.drawn and not self.drawing else None
            gfx.text(surf, "ACIERTOS", (pr.x + 18, pr.y + 76), 12, "b", MUTED)
            gfx.text(surf, "PAGO", (pr.right - 18, pr.y + 76), 12, "b", MUTED, anchor="topright")
            for j, (h, m) in enumerate(sorted(self.paytable(n).items(), reverse=True)):
                y = pr.y + 104 + j * 30
                row = pygame.Rect(pr.x + 10, y - 4, pr.w - 20, 26)
                if hits == h:
                    gfx.rrect(surf, row, (255, 200, 60, 255), 8)
                col = (40, 26, 6) if hits == h else TEXT
                gfx.text(surf, str(h), (pr.x + 22, y), 15, "b", col)
                gfx.text(surf, f"x{fmt_num(m, 1)}", (pr.right - 22, y), 15, "num", col if hits == h else GOLD_HI,
                         anchor="topright")
        else:
            gfx.text_wrapped(surf, "Haz clic en los números para elegir entre 1 y 10. Cuantos más aciertes, más "
                                   "cobras.", (pr.x + 18, pr.y + 56), 13, "r", MUTED, pr.w - 36)
        # controles
        c = self.controls_rect(rect)
        controls_bg(surf, c)
        self.bet_control(surf, c.x + 16, c.y + 12)
        if ui.button("quick", (c.x + 380, c.y + 18, 150, 34), "Al azar", "dark", enabled=not self.drawing,
                     size=12):
            k = len(self.picks) or MAX_PICKS
            self.picks = set(random.sample(range(1, POOL + 1), k))
            self.drawn = []
        if ui.button("clear", (c.x + 380, c.y + 58, 150, 34), "Borrar", "dark", enabled=not self.drawing, size=12):
            self.picks = set()
            self.drawn = []
        keys = ui.keys if not ui.focus else []
        if ui.button("play", (c.right - 200, c.y + 18, 180, 64), "JUGAR", "blue", enabled=not self.drawing, size=22,
                     sound=None) or (pygame.K_SPACE in keys and not self.drawing):
            self.play()
