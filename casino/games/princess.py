"""Princesa Estelar: tragaperras de cascadas estilo Starlight Princess."""
import math
import random

import pygame

from .base import BaseGame
from .common import controls_bg, toggle_pill
from . import princess_logic as L
from .. import gfx
from ..icons import Pen, C, gem as draw_gem
from ..fmt import fmt_money, fmt_num
from ..gfx import TEXT, MUTED, DIM, GOLD, GOLD_HI, GREEN, RED, ORANGE, PINK, PURPLE, LINE, INK, PANEL_LO

CELL = 88
GRAV = 5200.0

_art = {}


def _sym_pen(name):
    p = Pen()
    if name == "sun":
        for k in range(12):
            a = k * math.tau / 12
            p.poly([(C + 70 * math.cos(a - 0.2), C + 70 * math.sin(a - 0.2)), (C + 110 * math.cos(a), C + 110 * math.sin(a)),
                    (C + 70 * math.cos(a + 0.2), C + 70 * math.sin(a + 0.2))], (240, 80, 50))
        p.circle((C, C), 76, (255, 150, 40))
        p.circle((C - 8, C - 8), 58, (255, 210, 80))
        p.circle((C - 22, C - 24), 18, (255, 245, 190))
    elif name == "heart":
        col = (255, 90, 160)
        p.circle((C - 42, C - 26), 52, col)
        p.circle((C + 42, C - 26), 52, col)
        p.poly([(C - 92, C - 10), (C + 92, C - 10), (C, C + 96)], col)
        p.circle((C - 52, C - 42), 18, (255, 200, 225))
    elif name == "moon":
        p.circle((C, C), 96, (160, 110, 250))
        p.circle((C + 46, C - 30), 82, (0, 0, 0, 0))
        p.circle((C - 50, C + 10), 10, (210, 180, 255))
        p.circle((C - 30, C + 50), 7, (210, 180, 255))
    elif name == "star":
        p.poly(gfx.star_points(C, C + 8, 108, 46), (60, 140, 255))
        p.poly(gfx.star_points(C, C + 8, 66, 28), (150, 200, 255))
        p.poly(gfx.star_points(C - 10, C - 4, 22, 9), (240, 250, 255))
    elif name == "red":
        draw_gem(p, (C, C + 6), 92, (235, 60, 80))
    elif name == "blue":
        pts = [(C + 96 * math.cos(-math.pi / 2 + k * math.tau / 5), C + 8 + 96 * math.sin(-math.pi / 2 + k * math.tau / 5))
               for k in range(5)]
        p.poly(pts, (50, 100, 230))
        p.poly([(x * 0.6 + C * 0.4, y * 0.6 + (C + 8) * 0.4) for x, y in pts], (110, 160, 255))
        p.poly([pts[0], pts[1], (C, C + 8)], (160, 200, 255))
    elif name == "green":
        pts = [(C, C - 104), (C + 76, C), (C, C + 104), (C - 76, C)]
        p.poly(pts, (40, 170, 90))
        p.poly([(C, C - 104), (C + 76, C), (C, C)], (90, 220, 130))
        p.poly([(C, C - 60), (C + 30, C), (C, C + 60), (C - 30, C)], (150, 240, 170))
    elif name == "teal":
        pts = [(C + 96 * math.cos(k * math.tau / 10), C + 96 * math.sin(k * math.tau / 10)) for k in range(10)]
        p.poly(pts, (30, 170, 170))
        p.poly([(x * 0.62 + C * 0.38, y * 0.62 + C * 0.38) for x, y in pts], (80, 220, 210))
        p.circle((C - 20, C - 24), 14, (200, 255, 250))
    elif name == "yellow":
        pts = [(C + 96 * math.cos(math.pi / 6 + k * math.tau / 6), C + 96 * math.sin(math.pi / 6 + k * math.tau / 6))
               for k in range(6)]
        p.poly(pts, (230, 170, 30))
        p.poly([(x * 0.6 + C * 0.4, y * 0.6 + C * 0.4) for x, y in pts], (255, 220, 90))
        p.circle((C - 18, C - 22), 13, (255, 250, 210))
    elif name == "scatter":
        p.circle((C, C + 10), 106, (255, 120, 190))           # pelo
        p.rect((C - 106, C + 10, 212, 100), (255, 120, 190), 20)
        p.circle((C, C + 18), 74, (255, 220, 196))             # cara
        p.poly([(C - 80, C - 10), (C - 30, C - 70), (C + 10, C - 40), (C + 50, C - 74), (C + 82, C - 6),
                (C + 40, C - 26), (C, C - 10), (C - 40, C - 24)], (255, 120, 190))   # flequillo
        p.poly([(C - 50, C - 70), (C - 30, C - 112), (C - 10, C - 82), (C, C - 120), (C + 10, C - 82), (C + 30, C - 112),
                (C + 50, C - 70)], (255, 210, 70))              # tiara
        p.circle((C, C - 96), 9, (90, 200, 255))
        for dx in (-30, 30):
            p.ellipse((C + dx - 15, C + 4, 30, 38), (60, 120, 230))
            p.circle((C + dx - 4, C + 12), 7, (255, 255, 255))
        p.ellipse((C - 52, C + 44, 22, 12), (255, 160, 170))
        p.ellipse((C + 30, C + 44, 22, 12), (255, 160, 170))
        p.arc((C - 16, C + 44, 32, 22), math.pi * 1.1, math.pi * 1.9, (200, 70, 90), 5)
    return p.s


def sym_img(name, size=CELL - 6):
    key = (name, size)
    if key not in _art:
        _art[key] = gfx.pixelize(_sym_pen(name), (size, size), 2)
    return _art[key]


def orb_color(v):
    if v >= 100:
        return (255, 90, 70)
    if v >= 25:
        return (255, 190, 50)
    if v >= 10:
        return (170, 110, 255)
    if v >= 5:
        return (70, 150, 255)
    return (70, 210, 140)


def orb_img(v, size=CELL - 8):
    key = ("orb", v, size)
    if key not in _art:
        p = Pen()
        col = orb_color(v)
        p.circle((C, C + 6), 104, gfx.mul_col(col, 0.5))
        p.circle((C, C), 104, col)
        p.circle((C - 14, C - 14), 80, gfx.mul_col(col, 1.25))
        p.circle((C - 40, C - 44), 22, (255, 255, 255))
        base = gfx.pixelize(p.s, (size, size), 2)
        t = gfx.text_surf(f"x{v}", 22 if v < 100 else 16, "bl", TEXT)
        base.blit(t, t.get_rect(center=(size // 2, size // 2 + 2)))
        _art[key] = base
    return _art[key]


class Cell:
    __slots__ = ("s", "v", "y", "vy", "pop", "dead", "landed")

    def __init__(self, s, v, y=0.0):
        self.s, self.v = s, v
        self.y = y
        self.vy = 0.0
        self.pop = 0.0
        self.dead = False
        self.landed = y >= 0


class Princess(BaseGame):
    gid = "princess"

    def setup(self):
        self.rng = random.Random()
        gen = L.Gen(L.PARAMS["base"], self.rng)
        self.logic = L.new_grid(gen)
        self.cells = [[Cell(s, v) for (s, v) in col] for col in self.logic]
        self.phase = "idle"
        self.timer = 0.0
        self.gen = None
        self.seq = 0.0
        self.wins = {}
        self.in_fs = False
        self.fs_left = 0
        self.fs_mult = 0
        self.fs_total = 0.0
        self.fs_spins = 0
        self.round_bet = 0.0
        self.round_cost = 0.0
        self.round_gross = 0.0
        self.round_bought = False
        self.auto = False
        self.turbo = False
        self.ante = False
        self.last_win = 0.0
        self.win_disp = 0.0
        self.mult_pop = 0.0
        self.flyers = []
        self.big = None
        self.pending_trigger = False
        self.blessed = False       # orbes dobles en el próximo bonus (legendaria)
        self.blessed_fs = False

    # ------------------------------------------------------------ geometría
    def origin(self):
        return self.vis.x + 18, self.vis.y + 64

    def cell_xy(self, c, r):
        x0, y0 = self.origin()
        return x0 + c * CELL, y0 + r * CELL

    def speed(self):
        return 2.0 if self.turbo else 1.0

    def mode(self):
        if self.in_fs:
            return "fs"
        return "ante" if (self.ante and self.state.lvl("princess_ante")) else "base"

    def can_change_variant(self):
        return self.phase == "idle" and not self.in_fs

    # --------------------------------------------------------------- tiradas
    def spin(self):
        if self.phase != "idle":
            return
        if not self.in_fs:
            cost = self.bet * (1.25 if self.mode() == "ante" else 1.0)
            if self.bet > self.state.max_bet() + 1e-9:
                self.show("Supera tu límite de apuesta", RED)
                return
            if not self.take_bet_cost(cost):
                self.auto = False
                return
            self.round_bet = self.bet
            self.round_cost = cost
            self.round_gross = 0.0
            self.round_bought = False
            self.last_win = 0.0
        else:
            self.fs_left -= 1
            self.fs_spins += 1
        self.gen = L.Gen(L.PARAMS[self.mode()], self.rng)
        self.seq = 0.0
        self.banner = None
        self.phase = "clear"
        self.timer = 0.0
        self.audio.play("spin_start", 0.8)

    def take_bet_cost(self, cost):
        if cost > self.state.money + 1e-9:
            self.state.log("No tienes suficiente dinero", (254, 95, 85), "error")
            return False
        if self.bet < self.gdef.min_bet - 1e-9:
            return False
        self.state.wager(self.gid, cost)
        self.audio.play(f"chip{random.randint(0, 2)}", 0.7)
        return True

    def buy_bonus(self):
        if self.phase != "idle" or self.in_fs:
            return
        cost = self.bet * L.BUY_COST
        if self.bet > self.state.max_bet() + 1e-9:
            self.show("La apuesta supera tu límite", RED)
            return
        if not self.take_bet_cost(cost):
            return
        self.round_bet = self.bet
        self.round_cost = cost
        self.round_gross = 0.0
        self.round_bought = True
        self.start_fs()

    def start_fs(self):
        self.in_fs = True
        self.fs_left = L.FREE_SPINS
        self.fs_mult = 0
        self.fs_total = 0.0
        self.fs_spins = 0
        self.blessed_fs = self.blessed
        self.blessed = False
        self.feat("princess_bonus")
        self.audio.play("scatter")
        self.audio.play("win3", 0.6)
        self.big = {"text": f"¡{L.FREE_SPINS} TIRADAS GRATIS!", "t": 0.0, "col": PINK}
        self.fx.confetti(self.vis.centerx, self.vis.y, 120, w=self.vis.w)
        self.phase = "intro"
        self.timer = 0.0

    def build_drop(self):
        """Rejilla nueva que cae desde arriba, columna a columna."""
        self.logic = L.new_grid(self.gen)
        self.cells = []
        for c, col in enumerate(self.logic):
            cells = []
            for r, (s, v) in enumerate(col):
                cells.append(Cell(s, v, -(ROWS_PX + 60) - c * 70 / self.speed()))
            self.cells.append(cells)

    def do_tumble(self):
        new, falls = L.tumble(self.logic, self.wins, self.gen)
        cells = []
        for c in range(L.COLS):
            col_cells = [None] * L.ROWS
            n_new = sum(1 for src, _ in falls[c] if src is None)
            for src, dst in falls[c]:
                s, v = new[c][dst]
                if src is None:
                    cell = Cell(s, v, -(n_new - dst) * CELL - 30)
                else:
                    cell = self.cells[c][src]
                    cell.y = (src - dst) * CELL
                    cell.vy = 0.0
                    cell.landed = cell.y >= 0
                col_cells[dst] = cell
            cells.append(col_cells)
        self.logic = new
        self.cells = cells

    def update_fall(self, dt):
        settled = True
        for c, col in enumerate(self.cells):
            for cell in col:
                if cell.y < 0 or cell.vy != 0:
                    settled = False
                    cell.vy += GRAV * self.speed() * dt
                    cell.y += cell.vy * dt
                    if cell.y >= 0:
                        if not cell.landed:
                            cell.landed = True
                            if cell.vy > 900:
                                self.audio.play("dice_hit", 0.35, pan=(c - 2.5) / 4, throttle=0.04)
                        cell.y = 0
                        cell.vy = -cell.vy * 0.18 if cell.vy > 700 else 0.0
                        if abs(cell.vy) < 120:
                            cell.vy = 0.0
        return settled

    def check(self):
        self.wins = L.find_wins(self.logic)
        if self.wins:
            amt = sum(L.pay_for(s, len(p)) for s, p in self.wins.items())
            self.seq += amt
            for ps in self.wins.values():
                for (c, r) in ps:
                    self.cells[c][r].pop = 1.0
            x, y = self.cell_xy(3, 2)
            self.fx.text(x, y, f"+{fmt_money(amt * self.round_bet)}", GOLD_HI, 22, 0.9, 40)
            self.audio.play("win1", 0.6)
            self.phase = "show"
            self.timer = 0.0
        else:
            self.end_sequence()

    def explode(self):
        for ps in self.wins.values():
            for (c, r) in ps:
                x, y = self.cell_xy(c, r)
                cell = self.cells[c][r]
                col = {"sun": (255, 170, 50), "heart": PINK, "moon": PURPLE, "star": (80, 160, 255)}.get(cell.s, GOLD_HI)
                self.fx.sparks(x + CELL / 2, y + CELL / 2, 6, col, 0.9, 10, 0.5)
        self.audio.play("tumble", 0.8)
        self.do_tumble()
        self.phase = "fall"

    def end_sequence(self):
        orbs = L.orb_sum(self.logic)
        scat = L.scatters(self.logic)
        win = self.seq
        orb_cells = [(c, r) for c in range(L.COLS) for r in range(L.ROWS) if self.logic[c][r][0] == "orb"]
        if self.in_fs:
            win = self.seq * L.FS_MULT
            if self.seq > 0 and orbs > 0:
                self.fs_mult += orbs * (2 if self.blessed_fs else 1)
                win = self.seq * L.FS_MULT * self.fs_mult
                self.launch_orbs(orb_cells, to_mult=True)
            self.fs_total = min(L.MAX_WIN, self.fs_total + win)
            self.last_win = win
            if win >= 100:
                self.feat("princess_100x")
            if scat >= 3:
                self.fs_left += L.RETRIGGER
                self.feat("princess_retrigger")
                self.audio.play("scatter")
                self.big = {"text": f"¡+{L.RETRIGGER} TIRADAS!", "t": 0.0, "col": PINK}
            self.phase = "pause"
            self.timer = 0.0
        else:
            if self.seq > 0 and orbs > 0:
                win = self.seq * orbs
                self.launch_orbs(orb_cells, to_mult=False)
            trig = scat >= 4
            if trig:
                win += L.SCATTER_PAY[min(6, scat)]
            win = min(win, L.MAX_WIN)
            self.last_win = win
            self.round_gross += win
            if win >= 100:
                self.feat("princess_100x")
            if trig:
                self.pending_trigger = True
                self.phase = "pause"
                self.timer = 0.0
            else:
                self.finish_round()

    def launch_orbs(self, cells, to_mult):
        target = self.mult_box_center() if to_mult else self.win_box_center()
        for k, (c, r) in enumerate(cells):
            x, y = self.cell_xy(c, r)
            self.flyers.append({"x0": x + CELL / 2, "y0": y + CELL / 2, "x1": target[0], "y1": target[1],
                                "t": -k * 0.08, "dur": 0.55 / self.speed(), "v": self.logic[c][r][1]})
        if cells:
            self.audio.play("orb")

    def finish_round(self):
        """Liquida la ronda (tirada normal o bonus completo)."""
        gross = self.round_gross * self.round_bet
        self.pay(self.round_cost, gross, label="Premio" if gross > 0 else None,
                 pos=(self.vis.x + 280, self.vis.y + 260), quiet=gross <= 0)
        self.phase = "idle"
        if self.auto and not self.in_fs:
            self.later(0.45 / self.speed(), lambda: self.auto and self.phase == "idle" and self.spin())

    def end_fs(self):
        self.in_fs = False
        self.round_gross += self.fs_total
        total = self.round_gross
        self.big = {"text": f"BONUS: x{fmt_num(total)}", "t": 0.0, "col": GOLD_HI}
        if total * self.round_bet > self.round_cost:
            self.fx.coins(self.vis.centerx, self.vis.y + 200, 40, 1.6, 24)
        self.finish_round()

    # ---------------------------------------------------------------- update
    def update(self, dt):
        dt_s = dt * self.speed()
        self.timer += dt_s
        self.win_disp = gfx.approach(self.win_disp, self.last_win, dt, 10)
        self.mult_pop = max(0.0, self.mult_pop - dt * 3)
        if self.big:
            self.big["t"] += dt
            if self.big["t"] > 2.2:
                self.big = None
        for f in self.flyers[:]:
            f["t"] += dt
            if f["t"] >= f["dur"]:
                self.flyers.remove(f)
                self.mult_pop = 1.0
                self.audio.play("count", 1.0, throttle=0.03)
        for col in self.cells:
            for cell in col:
                if cell.pop > 0 and self.phase != "show":
                    cell.pop = max(0.0, cell.pop - dt * 4)
        ph = self.phase
        if ph == "clear":
            for col in self.cells:
                for cell in col:
                    cell.vy += GRAV * self.speed() * dt
                    cell.y += cell.vy * dt
            if self.timer > 0.22:
                self.build_drop()
                self.phase = "drop"
        elif ph in ("drop", "fall"):
            if self.update_fall(dt):
                self.phase = "settle"
                self.timer = 0.0
        elif ph == "settle":
            if self.timer > 0.08:
                self.check()
        elif ph == "show":
            if self.timer > 0.7:
                self.explode()
        elif ph == "intro":
            if self.timer > 1.6:
                self.phase = "idle"
                self.spin()
        elif ph == "pause":
            if self.timer > (0.9 if not self.flyers else 1.2):
                if self.pending_trigger:
                    self.pending_trigger = False
                    self.start_fs()
                elif self.in_fs:
                    if self.fs_left > 0 and self.fs_total < L.MAX_WIN:
                        self.phase = "idle"
                        self.spin()
                    else:
                        self.end_fs()
                else:
                    self.finish_round()

    # ----------------------------------------------------------------- dibujo
    def mult_box_center(self):
        pr = self.panel_rect()
        return (pr.centerx, pr.y + 190)

    def win_box_center(self):
        pr = self.panel_rect()
        return (pr.centerx, pr.y + 300)

    def panel_rect(self):
        x0, y0 = self.origin()
        x = x0 + L.COLS * CELL + 20
        return pygame.Rect(x, self.vis.y, self.vis.right - x, self.vis.h)

    def draw(self, surf, rect):
        ui = self.ui
        v = self.vis
        fs = self.in_fs
        bgc = (70, 34, 96) if fs else (46, 40, 86)
        gfx.box(surf, v, (*bgc, 255), 14, ow=4, shadow_off=6)
        # estrellas de fondo
        for k in range(26):
            sx = v.x + (k * 137) % v.w
            sy = v.y + (k * 71) % v.h
            if (int(self.t * 3) + k) % 5 == 0:
                surf.fill((255, 230, 250), (sx, sy, 4, 4))
            else:
                surf.fill((150, 120, 200), (sx, sy, 2, 2))
        x0, y0 = self.origin()
        gw, gh = L.COLS * CELL, L.ROWS * CELL
        title = "TIRADAS GRATIS" if fs else "PRINCESA ESTELAR"
        gfx.wavy_text(surf, title, (x0 + gw / 2, v.y + 30), 22, PINK if fs else GOLD_HI, self.t, 2, 4, weight="bl")
        frame = pygame.Rect(x0 - 8, y0 - 8, gw + 16, gh + 16)
        gfx.box(surf, frame, (24, 16, 40, 255), 10, outline=(255, 180, 220) if fs else LINE, ow=4, shadow_off=0)
        ui.push_clip(pygame.Rect(x0, y0, gw, gh))
        for c in range(L.COLS):
            for r in range(L.ROWS):
                if (c + r) % 2 == 0:
                    surf.fill((34, 24, 54), (x0 + c * CELL, y0 + r * CELL, CELL, CELL))
        for c, col in enumerate(self.cells):
            for r, cell in enumerate(col):
                x, y = x0 + c * CELL, y0 + r * CELL + cell.y
                if y > y0 + gh + 10 or y < y0 - CELL - 10:
                    continue
                img = orb_img(cell.v) if cell.s == "orb" else sym_img(cell.s)
                if cell.pop > 0:
                    k = 1 + 0.18 * math.sin(self.timer * 18) * cell.pop
                    gfx.glow(surf, (x + CELL / 2, y + CELL / 2), 54, (255, 220, 120), 0.6 * cell.pop)
                    img = gfx.scaled(img, k)
                if cell.s == "scatter":
                    gfx.glow(surf, (x + CELL / 2, y + CELL / 2), 50, (255, 120, 200), 0.4 + 0.2 * math.sin(self.t * 5))
                if cell.s == "orb":
                    img = pygame.transform.rotate(img, math.sin(self.t * 4 + c + r) * 8)
                surf.blit(img, img.get_rect(center=(int(x + CELL / 2), int(y + CELL / 2))))
        ui.pop_clip()
        # orbes volando
        for f in self.flyers:
            if f["t"] < 0:
                continue
            k = gfx.ease_in_out(min(1, f["t"] / f["dur"]))
            x = f["x0"] + (f["x1"] - f["x0"]) * k
            y = f["y0"] + (f["y1"] - f["y0"]) * k - math.sin(k * math.pi) * 80
            img = gfx.scaled(orb_img(f["v"]), 1 - 0.4 * k)
            surf.blit(img, img.get_rect(center=(int(x), int(y))))
        # panel derecho
        pr = self.panel_rect()
        gfx.box(surf, pr, (*PANEL_LO, 255), 12, ow=4, shadow_off=5)
        princess = sym_img("scatter", 96)
        surf.blit(princess, princess.get_rect(center=(pr.centerx, pr.y + 66 + math.sin(self.t * 2) * 5)))
        if fs:
            gfx.text(surf, f"TIRADAS: {self.fs_left}", (pr.centerx, pr.y + 132), 16, "bl", TEXT, anchor="center")
        elif self.has_hint("princess_orbs"):
            if self.blessed:
                gfx.text(surf, "Próximo bonus: ORBES x2", (pr.centerx, pr.y + 132), 12, "b", GOLD_HI, anchor="center")
            else:
                ready = self.hint_ready("princess_orbs")
                if ui.button("bless", (pr.x + 14, pr.y + 116, pr.w - 28, 32), "Princesa favorita" if ready else
                             "Favorita: recargando", "gold", enabled=ready, size=12,
                             tooltip="Los orbes de tu próximo bonus valdrán el doble."):
                    self.use_hint("princess_orbs")
                    self.blessed = True
        else:
            gfx.text(surf, "8+ iguales = premio", (pr.centerx, pr.y + 132), 12, "r", MUTED, anchor="center")
        mb = pygame.Rect(pr.x + 14, pr.y + 154, pr.w - 28, 72)
        gfx.box(surf, mb, (*((110, 40, 90) if fs else (50, 44, 70)), 255), 10, ow=4, shadow_off=4)
        gfx.text(surf, ("MULTIPLICADOR" + (" · ORBES x2" if self.blessed_fs else "")) if fs else "ORBES x2 - x500",
                 (mb.centerx, mb.y + 16), 12, "b", GOLD_HI if fs and self.blessed_fs else MUTED, anchor="center",
                 max_w=mb.w - 10)
        if fs:
            k = 1 + 0.3 * self.mult_pop
            img = gfx.scaled(gfx.text_surf(f"x{self.fs_mult}", 28, "bl", GOLD_HI), k)
            surf.blit(img, img.get_rect(center=(mb.centerx, mb.y + 48)))
        else:
            gfx.text(surf, "se suman al final", (mb.centerx, mb.y + 48), 12, "r", DIM, anchor="center")
        wb = pygame.Rect(pr.x + 14, pr.y + 236, pr.w - 28, 120)
        gfx.box(surf, wb, (40, 34, 56, 255), 10, ow=4, shadow_off=4)
        gfx.text(surf, "ÚLTIMA TIRADA", (wb.centerx, wb.y + 16), 12, "b", MUTED, anchor="center")
        gfx.text(surf, fmt_money(self.win_disp * (self.round_bet or self.bet)), (wb.centerx, wb.y + 46), 16, "bl",
                 GOLD_HI, anchor="center", max_w=wb.w - 10)
        if fs:
            gfx.text(surf, "TOTAL BONUS", (wb.centerx, wb.y + 76), 12, "b", MUTED, anchor="center")
            gfx.text(surf, fmt_money(self.fs_total * self.round_bet), (wb.centerx, wb.y + 100), 14, "bl", PINK,
                     anchor="center", max_w=wb.w - 10)
        # botones del panel
        by = wb.bottom + 14
        idle = self.phase == "idle" and not fs
        cost = self.bet * L.BUY_COST
        if ui.button("buy", (pr.x + 14, by, pr.w - 28, 56), "COMPRAR BONUS", "pink", enabled=idle and
                     self.state.money >= cost, size=13, sub=fmt_money(cost), sound=None):
            self.modal_buy()
        by += 66
        if self.state.lvl("princess_ante"):
            self.ante = toggle_pill(ui, ("pr", "ante"), surf, (pr.x + 16, by, 200, 30), "Ante (+25%)", self.ante,
                                    enabled=idle)
            by += 36
        self.turbo = toggle_pill(ui, ("pr", "turbo"), surf, (pr.x + 16, by, 200, 30), "Turbo", self.turbo)
        # rótulo grande
        if self.big:
            t = self.big["t"]
            k = gfx.ease_out_back(min(1, t / 0.35))
            r = pygame.Rect(0, 0, int(gw * 0.9 * k), int(110 * k))
            r.center = (x0 + gw / 2, y0 + gh / 2)
            if r.w > 20:
                gfx.box(surf, r, (40, 20, 50, 240), 14, outline=self.big["col"], ow=4, shadow_off=6)
                if k > 0.7:
                    gfx.wavy_text(surf, self.big["text"], r.center, 26, self.big["col"], self.t, 3, 6, weight="bl")
        # controles
        c = self.controls_rect(rect)
        controls_bg(surf, c)
        self.bet_control(surf, c.x + 16, c.y + 10)
        gfx.text(surf, "TABLA", (c.x + 372, c.y + 12), 12, "b", MUTED)
        if ui.button("pay", (c.x + 372, c.y + 32, 120, 50), "Premios", "dark", size=12):
            self.show_pay = not getattr(self, "show_pay", False)
        self.auto = toggle_pill(ui, ("pr", "auto"), surf, (c.x + 510, c.y + 44, 120, 30), "Auto", self.auto)
        keys = ui.keys if not ui.focus else []
        if ui.button("spin", (c.right - 200, c.y + 18, 184, 70), "GIRAR", "red", enabled=idle, size=20,
                     sound=None) or (idle and pygame.K_SPACE in keys):
            self.spin()
        if getattr(self, "show_pay", False):
            self.draw_paytable(surf)
        if getattr(self, "confirm_buy", False):
            self.draw_confirm(surf)

    def modal_buy(self):
        self.confirm_buy = True

    def draw_confirm(self, surf):
        ui = self.ui
        r = pygame.Rect(0, 0, 460, 200)
        r.center = self.vis.center
        gfx.box(surf, r, (*gfx.PANEL, 255), 12, ow=4, shadow_off=8)
        cost = self.bet * L.BUY_COST
        gfx.text(surf, "¿COMPRAR EL BONUS?", (r.centerx, r.y + 32), 16, "bl", PINK, anchor="center")
        gfx.text(surf, f"{L.FREE_SPINS} tiradas gratis por {fmt_money(cost)}", (r.centerx, r.y + 70), 12, "r", TEXT,
                 anchor="center")
        if ui.button("cb_no", (r.x + 24, r.bottom - 74, 190, 52), "Cancelar", "dark", size=13):
            self.confirm_buy = False
        if ui.button("cb_yes", (r.right - 214, r.bottom - 74, 190, 52), "Comprar", "pink", size=13, sound=None):
            self.confirm_buy = False
            self.buy_bonus()

    def draw_paytable(self, surf):
        r = pygame.Rect(self.vis.x + 30, self.vis.y + 40, self.vis.w - 60, self.vis.h - 80)
        gfx.box(surf, r, (*gfx.PANEL, 250), 12, ow=4, shadow_off=8)
        gfx.text(surf, "PREMIOS (x apuesta)   8-9 · 10-11 · 12+", (r.x + 24, r.y + 24), 14, "bl", ORANGE)
        for i, s in enumerate(L.SYMBOLS):
            col, row = divmod(i, 5)
            x = r.x + 24 + col * (r.w // 2)
            y = r.y + 60 + row * 70
            surf.blit(sym_img(s, 60), (x, y))
            p = L.PAY[s]
            gfx.text(surf, f"{fmt_num(p[0])} · {fmt_num(p[1])} · {fmt_num(p[2])}", (x + 76, y + 30), 14, "b", TEXT,
                     anchor="midleft")
        x = r.x + 24 + r.w // 2
        y = r.y + 60 + 4 * 70
        surf.blit(sym_img("scatter", 60), (x, y))
        gfx.text(surf, "4/5/6: 3x · 5x · 100x + 15 gratis", (x + 76, y + 30), 12, "b", PINK, anchor="midleft")
        gfx.text(surf, "En las tiradas gratis todo paga el DOBLE y los orbes se acumulan.", (r.x + 24, r.bottom - 34),
                 12, "b", GOLD_HI)
        if self.ui.button("pay_close", (r.right - 150, r.y + 12, 130, 44), "Cerrar", "gold", size=12):
            self.show_pay = False

    def on_hide(self):
        self.auto = False


ROWS_PX = L.ROWS * CELL
