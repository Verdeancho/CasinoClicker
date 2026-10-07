import random

import pygame

from .base import BaseGame
from .common import dark_panel, controls_bg, history_pills, toggle_pill
from .. import gfx
from ..fmt import fmt_money
from ..gfx import TEXT, MUTED, DIM, GOLD, GREEN, RED, BLUE

EDGE = 0.98


class Dice(BaseGame):
    gid = "dice"

    def setup(self):
        self.target = 50.0
        self.over = True
        self.roll = None
        self.shown = 50.0
        self.marker = 50.0
        self.hist = []
        self.auto = False
        self.dragging = False
        self.result = None
        self.won = None
        self.forced = None
        self.tip = None

    def chance(self):
        return (100 - self.target) if self.over else self.target

    def mult(self):
        return EDGE * 100 / self.chance()

    def start(self):
        if self.roll:
            return
        if not self.take_bet(self.bet):
            self.auto = False
            return
        if self.use_cheat():
            # dados de imán: cae en la zona ganadora
            lo, hi = (self.target + 0.01, 99.99) if self.over else (0.0, self.target - 0.01)
            self.forced = round(random.uniform(lo, hi), 2)
        self.result = self.forced if self.forced is not None else random.randint(0, 9999) / 100
        self.forced = None
        self.tip = None
        self.roll = {"t": 0.0, "dur": 0.55 if self.auto else 0.8, "bet": self.bet, "from": self.marker,
                     "target": self.target, "over": self.over, "mult": self.mult(), "chance": self.chance()}
        self.dragging = False
        self.won = None
        self.audio.play("dice")

    def update(self, dt):
        r = self.roll
        if r:
            r["t"] += dt
            k = min(1.0, r["t"] / r["dur"])
            self.shown = random.uniform(0, 99.99) if k < 0.85 else self.result
            self.marker = r["from"] + (self.result - r["from"]) * gfx.ease_out_back(k, 1.2)
            if k >= 1:
                self.roll = None
                self.finish(r)

    def finish(self, r):
        bet = r["bet"]
        won = self.result > r["target"] if r["over"] else self.result < r["target"]
        self.won = won
        self.hist.append((f"{self.result:.2f}", GREEN if won else RED))
        if won and r["chance"] < 5:
            self.feat("dice_sniper")
        if r["chance"] < 10:
            n = self.state.count("dice_sniper", add=1) if won else self.state.count("dice_sniper", 0)
            if n >= 3:
                self.feat("dice_sniper3")
        bx = self.bar_rect()
        px = bx.x + bx.w * self.result / 100
        self.pay(bet, bet * r["mult"] if won else 0, pos=(px, bx.y - 90))
        if self.auto:
            self.later(0.3, lambda: self.auto and self.start())

    def bar_rect(self):
        v = self.vis
        return pygame.Rect(v.x + 60, v.y + 250, v.w - 120, 26)

    def draw(self, surf, rect):
        ui = self.ui
        v = self.vis
        dark_panel(surf, v, 20, (30, 34, 62), (16, 18, 34))
        gfx.glow(surf, (v.centerx, v.y + 120), 260, (40, 70, 160), 0.35)
        # número grande
        col = TEXT if self.won is None else (GREEN if self.won else RED)
        num = f"{self.shown:05.2f}"
        gfx.text(surf, num, (v.centerx, v.y + 110), 92, "num", col, anchor="center", shadow=3)
        gfx.text(surf, "TIRADA (0 - 100)", (v.centerx, v.y + 40), 13, "b", MUTED, anchor="center")
        history_pills(surf, v.right - 20, v.y + 16, self.hist, 8, 64, 24, right_to_left=True)
        # barra
        bar = self.bar_rect()
        tx = bar.x + bar.w * self.target / 100
        lose_c, win_c = (170, 50, 70), (40, 180, 110)
        left_c, right_c = (lose_c, win_c) if self.over else (win_c, lose_c)
        gfx.rrect(surf, bar.inflate(10, 10), (10, 10, 20, 255), 18)
        gfx.rrect(surf, (bar.x, bar.y, max(8, int(tx - bar.x)), bar.h), None, 13,
                  grad=((*gfx.mul_col(left_c, 1.2), 255), (*left_c, 255)))
        gfx.rrect(surf, (int(tx), bar.y, max(8, bar.right - int(tx)), bar.h), None, 13,
                  grad=((*gfx.mul_col(right_c, 1.2), 255), (*right_c, 255)))
        for val in (0, 25, 50, 75, 100):
            xx = bar.x + bar.w * val / 100
            gfx.text(surf, str(val), (xx, bar.bottom + 14), 12, "sb", DIM, anchor="midtop")
        # tirador del objetivo
        handle = pygame.Rect(0, 0, 28, 44)
        handle.center = (int(tx), bar.centery)
        hv = ui.anim(("dice", "h"), 1.0 if (ui.hover(handle.inflate(10, 10)) or self.dragging) else 0.0)
        if ui.hover(bar.inflate(0, 30)) and not self.roll:
            ui.hot_any = True
            if ui.pressed:
                self.dragging = True
        if self.dragging:
            if ui.down and not self.roll:
                old = self.target
                self.target = round(gfx.clamp((ui.mx - bar.x) / bar.w * 100, 2, 98))
                if self.target != old:
                    self.audio.play("tick0", 0.6, throttle=0.03)
            else:
                self.dragging = False
        gfx.glow(surf, handle.center, 30, (200, 200, 255), 0.3 + 0.3 * hv)
        gfx.rrect(surf, handle, None, 8, border=(255, 255, 255), bw=1, grad=((250, 250, 255, 255), (190, 194, 220, 255)))
        for k in (-5, 0, 5):
            pygame.draw.line(surf, (120, 124, 160), (handle.centerx + k, handle.y + 14), (handle.centerx + k, handle.bottom - 14), 2)
        gfx.text(surf, f"{self.target:.0f}", (tx, bar.y - 40), 16, "b", TEXT, anchor="center")
        # marcador del resultado
        if self.result is not None:
            mx = bar.x + bar.w * gfx.clamp(self.marker, 0, 100) / 100
            mc = TEXT if self.won is None else (GREEN if self.won else RED)
            mr = pygame.Rect(0, 0, 76, 34)
            mr.midbottom = (int(mx), bar.y - 54)
            gfx.rrect(surf, mr, (*mc, 255), 10)
            gfx.aa_poly(surf, mc, [(mx - 9, mr.bottom - 1), (mx + 9, mr.bottom - 1), (mx, mr.bottom + 11)])
            gfx.text(surf, f"{self.marker:.2f}", mr.center, 15, "bl", (16, 16, 26), anchor="center")
        # tarjetas de información
        y = v.y + 340
        cw = (v.w - 80) // 3
        items = [("MULTIPLICADOR", f"x{self.mult():.4g}", GOLD), ("PROBABILIDAD", f"{self.chance():.0f}%", BLUE),
                 ("GANANCIA SI ACIERTAS", "+" + fmt_money(self.bet * (self.mult() - 1)), GREEN)]
        for i, (lbl, val, col) in enumerate(items):
            r = pygame.Rect(v.x + 30 + i * (cw + 10), y, cw, 80)
            dark_panel(surf, r, 14, (40, 40, 68), (28, 28, 48))
            gfx.text(surf, lbl, (r.x + 16, r.y + 14), 12, "b", MUTED)
            gfx.text(surf, val, (r.x + 16, r.y + 36), 24, "num", col)
        # controles
        c = self.controls_rect(rect)
        controls_bg(surf, c)
        self.bet_control(surf, c.x + 16, c.y + 12)
        if ui.button("mode", (c.x + 380, c.y + 26, 170, 48), "Sacar MÁS" if self.over else "Sacar MENOS", "dark",
                     icon="upgrade" if self.over else None, enabled=not self.roll, size=15):
            self.over = not self.over
            self.target = 100 - self.target
        self.auto = toggle_pill(ui, ("dice", "auto"), surf, (c.x + 560, c.y + 38, 110, 30), "Auto", self.auto)
        pill = self.hint_pill(surf, v.x + 24, v.bottom - 52, 290)
        if pill and self.hint_ready() and self.tip is None and not self.roll:
            if ui.button("hint", (pill.right + 10, pill.y - 6, 130, 44), "Sentir", "gold", size=12):
                self.use_hint()
                self.forced = random.randint(0, 9999) / 100
                high = self.forced >= 50
                said = high if random.random() < self.reliable(0.68) else not high
                self.tip = "ALTA (50 o más)" if said else "BAJA (menos de 50)"
        if self.tip:
            gfx.wavy_text(surf, f"Presientes una tirada {self.tip}", (v.centerx, v.y + 196), 14, gfx.GOLD_HI, self.t, 2, 5)
        self.cheat_pill(surf, v.right - 290, v.bottom - 52, 266)
        if ui.button("roll", (c.right - 200, c.y + 18, 180, 64), "TIRAR", "blue", enabled=not self.roll, size=22,
                     sound=None):
            self.start()

    def on_hide(self):
        self.auto = False
