import math
import random

import pygame

from .base import BaseGame
from .common import dark_panel, controls_bg
from .. import gfx, art
from ..fmt import fmt_money, fmt_num
from ..gfx import TEXT, MUTED, DIM, GOLD, GOLD_HI, GREEN, RED

EDGE = 0.97
N = 5
TILE = 86
GAP = 10


def multiplier(mines, safe, tiles=N * N):
    m = EDGE
    for i in range(safe):
        m *= (tiles - i) / (tiles - mines - i)
    return m


class Mines(BaseGame):
    gid = "mines"

    def setup(self):
        self.n_mines = 3
        self.active = False
        self.pbet = 0.0
        self.mines = set()
        self.revealed = {}      # índice -> tiempo de revelado
        self.free = set()
        self.exploded = None
        self.ended = False
        self.found = set()
        self.radar = None
        self.xray = False

    def tiles(self):
        return N * N - len(self.free)

    def grid_origin(self):
        v = self.vis
        size = N * TILE + (N - 1) * GAP
        return v.x + 30, v.y + (v.h - size) // 2

    def safe_count(self):
        return len(self.found)

    def start(self):
        if self.active:
            return
        if not self.take_bet(self.bet):
            return
        self.pbet = self.bet
        self.active = True
        self.ended = False
        self.exploded = None
        self.revealed = {}
        self.free = set()
        self.found = set()
        self.mines = set(random.sample(range(N * N), self.n_mines))
        if self.state.lvl("mines_detector"):
            f = random.choice([i for i in range(N * N) if i not in self.mines])
            self.free.add(f)
            self.revealed[f] = self.t
        self.radar = None
        if self.hint_ready():
            self.use_hint()
            if random.random() < self.reliable(0.80):
                self.radar = random.choice(sorted(self.mines))
            else:   # falsa alarma: marca una casilla que en realidad es segura
                self.radar = random.choice([i for i in range(N * N) if i not in self.mines and i not in self.free])
        self.xray = self.use_cheat()
        self.banner = None

    def reveal(self, i):
        if not self.active or i in self.revealed or i == self.radar:
            return
        self.revealed[i] = self.t
        x0, y0 = self.grid_origin()
        r, c = divmod(i, N)
        cx, cy = x0 + c * (TILE + GAP) + TILE / 2, y0 + r * (TILE + GAP) + TILE / 2
        if i in self.mines:
            self.exploded = i
            self.active = False
            self.ended = True
            for m in self.mines:
                self.revealed.setdefault(m, self.t + 0.15 + random.uniform(0, 0.3))
            self.audio.play("bomb")
            self.fx.flash(cx, cy, 140, (255, 140, 60))
            self.fx.sparks(cx, cy, 50, (255, 140, 60), 2.0, 12, 0.9)
            self.fx.add_shake(8)
            self.pay(self.pbet, 0, label="¡BOOM!", quiet=True)
            return
        self.found.add(i)
        k = self.safe_count()
        self.audio.play(f"gem{min(15, k - 1)}")
        self.fx.sparks(cx, cy, 18, (120, 255, 190), 1.0, 9)
        if k + len(self.free) >= N * N - self.n_mines:
            if self.n_mines >= 3:
                self.feat("mines_clear")
            if self.n_mines >= 10:
                self.feat("mines_clear10")
            self.cashout()

    def cashout(self):
        if not self.active:
            return
        self.active = False
        self.ended = True
        k = self.safe_count()
        m = multiplier(self.n_mines, k, self.tiles()) if k else 1.0
        for i in range(N * N):
            self.revealed.setdefault(i, self.t + 0.1 + random.uniform(0, 0.35))
        if k:
            self.audio.play("cashout")
        self.pay(self.pbet, self.pbet * m, label=f"{k} gemas", quiet=True)

    def draw(self, surf, rect):
        ui = self.ui
        v = self.vis
        dark_panel(surf, v, 20, (26, 22, 46), (14, 12, 26))
        x0, y0 = self.grid_origin()
        board = pygame.Rect(x0 - 16, y0 - 16, N * TILE + (N - 1) * GAP + 32, N * TILE + (N - 1) * GAP + 32)
        gfx.rrect(surf, board, (12, 10, 22, 255), 20, border=(70, 60, 110), bw=1)
        for i in range(N * N):
            r, c = divmod(i, N)
            tr = pygame.Rect(x0 + c * (TILE + GAP), y0 + r * (TILE + GAP), TILE, TILE)
            rt = self.revealed.get(i)
            shown = rt is not None and self.t >= rt
            wid = ("mine", i)
            h = self.active and not shown and ui.hover(tr)
            hv = ui.anim(wid, 1.0 if h else 0.0, 18)
            if not shown:
                lift = int(4 * hv)
                tt = tr.move(0, -lift)
                gfx.rrect(surf, tr.move(0, 5), (8, 8, 16, 255), 14)
                top = gfx.lerp_col((74, 70, 120), (110, 100, 180), hv) if self.active else (52, 50, 80)
                gfx.rrect(surf, tt, None, 14, border=gfx.mul_col(top, 1.4), bw=1,
                          grad=((*gfx.mul_col(top, 1.15), 255), (*gfx.mul_col(top, 0.8), 255)))
                if hv > 0.05:
                    gfx.glow(surf, tt.center, 50, (120, 100, 220), 0.3 * hv)
                gfx.circle(surf, tt.center, 6, gfx.mul_col(top, 0.7))
                if i == self.radar and self.active:
                    gfx.rrect(surf, tt.inflate(-8, -8), (0, 0, 0, 0), 8, border=gfx.RED, bw=4)
                    gfx.text(surf, "MINA", tt.center, 12, "b", gfx.RED, anchor="center")
                elif self.xray and self.active and i in self.mines:
                    gfx.text(surf, "X", tt.center, 16, "bl", (220, 140, 255), anchor="center")
                if h:
                    ui.hot_any = True
                    if ui.pressed:
                        ui.active = wid
                    if ui.released and ui.active == wid:
                        self.reveal(i)
            else:
                age = self.t - rt
                k = min(1.0, age / 0.25)
                sx = abs(math.cos((1 - k) * math.pi / 2)) if k < 1 else 1
                is_mine = i in self.mines
                mine_found = i in self.found or i in self.free
                if is_mine:
                    base = (150, 40, 50) if i == self.exploded else (60, 34, 50)
                else:
                    base = (30, 110, 80) if mine_found else (36, 50, 56)
                w = max(2, int(TILE * sx))
                cell = pygame.Rect(0, 0, w, TILE)
                cell.center = tr.center
                gfx.rrect(surf, cell, None, 14, grad=((*gfx.mul_col(base, 1.2), 255), (*gfx.mul_col(base, 0.7), 255)))
                if k >= 1:
                    if is_mine:
                        img = art.bomb_sprite(60)
                    else:
                        img = art.gem_sprite(62)
                        if not mine_found:
                            img = img.copy()
                            img.set_alpha(110)
                        else:
                            gfx.glow(surf, tr.center, 48, (60, 220, 150), 0.35 + 0.1 * math.sin(ui.t * 3 + i))
                    pop = gfx.ease_out_back(min(1, (age - 0.25) / 0.3)) if age < 0.55 else 1
                    gfx.blit_center(surf, gfx.scaled(img, max(0.05, pop)), tr.center)
                if i in self.free:
                    gfx.text(surf, "gratis", (tr.centerx, tr.bottom - 12), 10, "b", (200, 255, 220), anchor="center")
        # panel lateral
        px = board.right + 20
        pr = pygame.Rect(px, v.y + 20, v.right - px - 20, v.h - 40)
        dark_panel(surf, pr, 18, (36, 32, 62), (22, 20, 40))
        k = self.safe_count()
        gfx.text(surf, "MINAS", (pr.x + 20, pr.y + 18), 13, "b", MUTED)
        if ui.button("m-", (pr.x + 20, pr.y + 40, 44, 44), "-", "dark", enabled=not self.active, size=22):
            self.n_mines = max(1, self.n_mines - 1)
        gfx.rrect(surf, (pr.x + 70, pr.y + 40, 70, 44), (12, 12, 22, 255), 10, border=(70, 66, 104), bw=1)
        gfx.text(surf, str(self.n_mines), (pr.x + 105, pr.y + 62), 24, "num", GOLD_HI, anchor="center")
        if ui.button("m+", (pr.x + 146, pr.y + 40, 44, 44), "+", "dark", enabled=not self.active, size=22):
            self.n_mines = min(24, self.n_mines + 1)
        for j, val in enumerate((1, 3, 5, 10, 24)):
            if ui.button(("mq", val), (pr.x + 20 + j * 52, pr.y + 92, 46, 30), str(val), "ghost",
                         enabled=not self.active, size=12, selected=self.n_mines == val):
                self.n_mines = val
        gfx.text(surf, f"Gemas: {N * N - self.n_mines}", (pr.right - 20, pr.y + 18), 13, "b", (120, 240, 180),
                 anchor="topright")
        self.hint_pill(surf, pr.x + 20, pr.bottom - 50, pr.w - 40)
        self.cheat_pill(surf, pr.x + 20, pr.bottom - 92, pr.w - 40)
        y = pr.y + 140
        pygame.draw.line(surf, (60, 56, 90), (pr.x + 20, y), (pr.right - 20, y))
        y += 14
        if self.active:
            cur = multiplier(self.n_mines, k, self.tiles()) if k else 1.0
            gfx.text(surf, "MULTIPLICADOR", (pr.x + 20, y), 12, "b", MUTED)
            gfx.text(surf, f"x{fmt_num(cur)}", (pr.x + 20, y + 18), 38, "num", GOLD_HI)
            gfx.text(surf, f"Cobras {fmt_money(self.pbet * cur)}", (pr.x + 20, y + 66), 15, "b", TEXT)
            left = N * N - self.n_mines - k - len(self.free)
            hidden = N * N - len(self.revealed)
            if left > 0:
                p = (hidden - self.n_mines) / hidden if hidden else 0
                gfx.text(surf, f"Siguiente gema: x{fmt_num(multiplier(self.n_mines, k + 1, self.tiles()))}", (pr.x + 20, y + 100), 14,
                         "b", (120, 240, 180))
                gfx.text(surf, f"Probabilidad de acierto: {p * 100:.1f}%", (pr.x + 20, y + 124), 13, "r", MUTED)
        else:
            gfx.text(surf, "TABLA DE MULTIPLICADORES", (pr.x + 20, y), 12, "b", MUTED)
            for j, sfound in enumerate((1, 2, 3, 5, 8, 12, 16)):
                if sfound > N * N - self.n_mines:
                    break
                yy = y + 26 + j * 28
                gfx.text(surf, f"{sfound} gema{'s' if sfound > 1 else ''}", (pr.x + 20, yy), 14, "sb", TEXT)
                gfx.text(surf, f"x{fmt_num(multiplier(self.n_mines, sfound, self.tiles()))}", (pr.right - 20, yy), 14, "b", GOLD_HI,
                         anchor="topright")
        # controles
        c = self.controls_rect(rect)
        controls_bg(surf, c)
        self.bet_control(surf, c.x + 16, c.y + 12)
        keys = ui.keys if not ui.focus else []
        if self.active:
            if ui.button("rand", (c.x + 380, c.y + 22, 160, 56), "Casilla al azar", "dark", size=14):
                hidden = [i for i in range(N * N) if i not in self.revealed]
                if hidden:
                    self.reveal(random.choice(hidden))
            cur = multiplier(self.n_mines, k, self.tiles()) if k else 1.0
            if ui.button("cash", (c.right - 220, c.y + 18, 200, 64), "RETIRAR", "gold", size=20,
                         sub=fmt_money(self.pbet * cur), sound=None) or pygame.K_SPACE in keys:
                self.cashout()
        else:
            if ui.button("start", (c.right - 220, c.y + 18, 200, 64), "APOSTAR", "green", size=20, sound=None) or \
                    pygame.K_SPACE in keys:
                self.start()
