"""Sic Bo: tres dados bajo una cúpula. Apuestas clásicas con sus pagos de casino."""
import random

import pygame

from .base import BaseGame
from .common import felt, controls_bg
from .. import gfx, art
from ..dice3d import Die
from ..fmt import fmt_money
from ..gfx import TEXT, MUTED, DIM, GOLD, GOLD_HI, GREEN, RED, ORANGE, PANEL_LO, LINE

TOTAL_PAY = {4: 60, 5: 30, 6: 17, 7: 12, 8: 8, 9: 6, 10: 6, 11: 6, 12: 6, 13: 8, 14: 12, 15: 17, 16: 30, 17: 60}


def gross_mult(key, dice):
    """Multiplicador bruto (incluye la apuesta) de una apuesta para una tirada."""
    t = sum(dice)
    triple = dice[0] == dice[1] == dice[2]
    k = key[0]
    if k == "small":
        return 2 if (4 <= t <= 10 and not triple) else 0
    if k == "big":
        return 2 if (11 <= t <= 17 and not triple) else 0
    if k == "even":
        return 2 if (t % 2 == 0 and not triple) else 0
    if k == "odd":
        return 2 if (t % 2 == 1 and not triple) else 0
    if k == "anyt":
        return 31 if triple else 0
    if k == "tot":
        return TOTAL_PAY[key[1]] + 1 if t == key[1] else 0
    if k == "dbl":
        return 11 if dice.count(key[1]) >= 2 else 0
    if k == "tri":
        return 181 if dice.count(key[1]) == 3 else 0
    if k == "one":
        c = dice.count(key[1])
        return 1 + c if c else 0
    return 0


class SicBo(BaseGame):
    gid = "sicbo"

    def setup(self):
        self.dice = [Die(6, color=(250, 244, 230)), Die(6, color=(250, 244, 230)), Die(6, color=(250, 244, 230))]
        self.bets = {}
        self.last_bets = {}
        self.rolling = False
        self.result = None
        self.hist = []
        self.win_t = 0.0
        self.peek = None          # (dado, valor) que se ve con la ventaja

    def add_bet(self, key):
        if self.rolling:
            return
        total = sum(self.bets.values()) + self.bet
        if total > self.state.money + 1e-9:
            self.show("Fondos insuficientes", RED)
            self.audio.play("error")
            return
        self.bets[key] = self.bets.get(key, 0) + self.bet
        self.result = None
        self.audio.play(f"chip{random.randint(0, 2)}")

    def roll(self):
        if self.rolling:
            return
        if not self.bets:
            self.show("Pon fichas en el tapete", MUTED)
            return
        total = sum(self.bets.values())
        if not self.take_bet(total):
            return
        self.total = total
        self.last_bets = dict(self.bets)
        self.result = None
        self.rolling = True
        vals = [random.randint(1, 6) for _ in range(3)]
        if self.use_cheat():
            import itertools
            vals = list(max(itertools.product(range(1, 7), repeat=3),
                            key=lambda r: sum(a * gross_mult(k, list(r)) for k, a in self.bets.items())))
        elif self.peek is not None:
            i, val, true = self.peek
            if true:
                vals[i] = val
        self.peek = None
        for i, d in enumerate(self.dice):
            d.roll(vals[i], 1.4 + i * 0.18)
        self.audio.play("dice")

    def update(self, dt):
        self.win_t += dt
        if self.rolling:
            done = True
            for d in self.dice:
                d.update(dt, lambda amp: self.audio.play("dice_hit", 0.3 + amp * 0.6, throttle=0.04))
                if d.rolling:
                    done = False
            if done:
                self.rolling = False
                self.finish()

    def finish(self):
        res = [d.result for d in self.dice]
        self.result = res
        self.win_t = 0.0
        self.hist.append(res)
        gross = sum(amt * gross_mult(k, res) for k, amt in self.bets.items())
        if any(k[0] == "tri" and gross_mult(k, res) for k in self.bets):
            self.feat("sicbo_triple")
        cx, cy = self.dome_center()
        self.pay(self.total, gross, label=f"{res[0]}-{res[1]}-{res[2]} = {sum(res)}", pos=(cx, cy - 120))
        if sum(self.bets.values()) > self.state.money + 1e-9:
            self.bets = {}

    def dome_center(self):
        return (self.vis.x + 170, self.vis.y + 210)

    # ----------------------------------------------------------------- tapete
    def layout(self):
        v = self.vis
        x0 = v.x + 340
        w = v.right - 20 - x0
        y = v.y + 16
        cells = []
        top = [(("small",), "PEQUEÑO", "4-10"), (("even",), "PAR", "1:1"), (("anyt",), "TRIPLE", "30:1"),
               (("odd",), "IMPAR", "1:1"), (("big",), "GRANDE", "11-17")]
        cw = w / 5
        for i, (k, a, b) in enumerate(top):
            cells.append((k, pygame.Rect(int(x0 + i * cw), y, int(cw) - 4, 70), a, b, (60, 120, 90)))
        y += 76
        cw = w / 7
        for j, t in enumerate(range(4, 18)):
            row, col = divmod(j, 7)
            cells.append((("tot", t), pygame.Rect(int(x0 + col * cw), y + row * 56, int(cw) - 4, 52), str(t),
                          f"{TOTAL_PAY[t]}:1", (40, 96, 72)))
        y += 118
        cw = w / 6
        for d in range(1, 7):
            cells.append((("dbl", d), pygame.Rect(int(x0 + (d - 1) * cw), y, int(cw) - 4, 56), f"{d}{d}", "10:1",
                          (70, 80, 110)))
        y += 60
        for d in range(1, 7):
            cells.append((("tri", d), pygame.Rect(int(x0 + (d - 1) * cw), y, int(cw) - 4, 56), f"{d}{d}{d}", "180:1",
                          (110, 60, 90)))
        y += 60
        for d in range(1, 7):
            cells.append((("one", d), pygame.Rect(int(x0 + (d - 1) * cw), y, int(cw) - 4, 64), str(d), "x1-x3",
                          (120, 90, 40)))
        return cells

    def draw(self, surf, rect):
        ui = self.ui
        v = self.vis
        felt(surf, v, (90, 40, 60), (230, 190, 120))
        cx, cy = self.dome_center()
        # cúpula
        gfx.circle(surf, (cx, cy + 6), 150, (0, 0, 0, 90))
        gfx.circle(surf, (cx, cy), 150, (120, 60, 80), border=LINE, bw=4)
        gfx.circle(surf, (cx, cy), 134, (70, 30, 50))
        offs = [(-56, 30), (54, 36), (0, -46)]
        for d, (dx, dy) in zip(self.dice, offs):
            hop = d.hop * 60
            img = d.render(120)
            surf.blit(img, img.get_rect(center=(cx + dx, cy + dy - hop)))
        gfx.glow(surf, (cx - 50, cy - 70), 60, (200, 200, 230), 0.3)
        gfx.circle(surf, (cx, cy), 150, (0, 0, 0, 0), border=(230, 200, 220), bw=4)
        if self.result and not self.rolling:
            t = sum(self.result)
            gfx.text(surf, f"TOTAL {t}", (cx, cy + 172), 18, "bl", GOLD_HI, anchor="center")
        # historial
        for i, h in enumerate(self.hist[-6:][::-1]):
            gfx.text(surf, f"{h[0]}{h[1]}{h[2]}·{sum(h)}", (v.x + 20, v.bottom - 30 - i * 22), 12, "r",
                     TEXT if i == 0 else MUTED)
        # tapete
        win = set()
        if self.result and not self.rolling:
            win = {k for k, *_ in self.layout() if gross_mult(k, self.result) > 0}
        for key, r, a, b, col in self.layout():
            wid = ("sb", key)
            h = ui.hover(r) and not self.rolling
            hv = ui.anim(wid, 1.0 if h else 0.0, 18)
            fill = (253, 162, 0) if key in win else gfx.lerp_col(col, gfx.mul_col(col, 1.35), hv)
            gfx.rrect(surf, r, (*fill, 255), 6, border=LINE, bw=4)
            gfx.text(surf, a, (r.centerx, r.y + r.h * 0.36), 12 if len(a) > 4 else 16, "b", TEXT, anchor="center",
                     max_w=r.w - 6)
            gfx.text(surf, b, (r.centerx, r.y + r.h * 0.74), 12, "r", (235, 235, 235), anchor="center", max_w=r.w - 4)
            amt = self.bets.get(key)
            if amt:
                chip = art.chip_with_text(32, amt)
                surf.blit(chip, chip.get_rect(center=(r.right - 18, r.y + 18)))
            if h:
                ui.hot_any = True
                if ui.pressed:
                    ui.active = wid
                if ui.released and ui.active == wid:
                    self.add_bet(key)
                if ui.rpressed and key in self.bets:
                    del self.bets[key]
                    self.audio.play("chip1", 0.6)
        # controles
        c = self.controls_rect(rect)
        controls_bg(surf, c)
        self.bet_control(surf, c.x + 16, c.y + 10, "VALOR DE LA FICHA")
        total = sum(self.bets.values())
        gfx.text(surf, f"En juego: {fmt_money(total)}", (c.x + 372, c.y + 14), 12, "b", GOLD_HI)
        if ui.button("clear", (c.x + 372, c.y + 38, 110, 48), "Borrar", "dark", enabled=not self.rolling, size=12):
            self.bets = {}
        if ui.button("repeat", (c.x + 490, c.y + 38, 110, 48), "Repetir", "dark",
                     enabled=not self.rolling and bool(self.last_bets), size=12):
            if sum(self.last_bets.values()) <= self.state.money + 1e-9:
                self.bets = dict(self.last_bets)
        v = self.vis
        pill = self.hint_pill(surf, v.x + 24, v.bottom - 54, 280)
        if pill and self.hint_ready() and self.peek is None and not self.rolling:
            if ui.button("hint", (pill.x, pill.y - 50, 150, 44), "Mirar un dado", "gold", size=12):
                self.use_hint()
                i = random.randrange(3)
                val = random.randint(1, 6)
                true = random.random() < self.reliable(0.75)
                self.peek = (i, val if true else random.choice([x for x in range(1, 7) if x != val]), true)
                if not true:
                    self.peek = (i, self.peek[1], False)
        if self.peek is not None:
            gfx.wavy_text(surf, f"Uno de los dados es un {self.peek[1]}", (self.dome_center()[0], v.y + 30), 14,
                          GOLD_HI, self.t, 2, 5)
        self.cheat_pill(surf, v.x + 24, v.bottom - 96, 280)
        keys = ui.keys if not ui.focus else []
        if ui.button("roll", (c.right - 170, c.y + 18, 154, 70), "AGITAR", "red", enabled=not self.rolling and
                     bool(self.bets), size=16, sound=None) or (pygame.K_SPACE in keys and not self.rolling):
            self.roll()
