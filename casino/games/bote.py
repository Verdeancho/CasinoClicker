"""El Bote: reparte fichas entre las caras del dado. La cara que sale multiplica lo apostado en ella.

Variantes: dado de 6 (x5,7), octaedro (x7,6), dodecaedro (x11,5) e icosaedro (x19)."""
import math
import random

import pygame

from .base import BaseGame
from .common import felt, controls_bg
from .. import gfx, art
from ..dice3d import Die
from ..fmt import fmt_money, fmt_num
from ..gfx import TEXT, MUTED, DIM, GOLD, GOLD_HI, GREEN, RED, ORANGE, PANEL_LO, LINE
from ..data import BOTE_PAY

KIND = {"d6": 6, "d8": 8, "d12": 12, "d20": 20}
GRID = {6: (3, 2), 8: (4, 2), 12: (4, 3), 20: (5, 4)}


class Bote(BaseGame):
    gid = "bote"

    def setup(self):
        self.on_variant()

    def on_variant(self):
        self.faces = KIND.get(self.variant, 6)
        self.die = Die(self.faces)
        self.bets = {}
        self.last_bets = {}
        self.result = None
        self.hist = []
        self.rolling = False
        self.forced = None
        self.tip = None
        self.win_t = 0.0

    def can_change_variant(self):
        return not self.rolling

    def payout(self):
        return BOTE_PAY.get(self.variant, self.faces - 1)

    def add_bet(self, f):
        if self.rolling:
            return
        total = sum(self.bets.values()) + self.bet
        if total > self.state.money + 1e-9:
            self.show("Fondos insuficientes", RED)
            self.audio.play("error")
            return
        self.bets[f] = self.bets.get(f, 0) + self.bet
        self.result = None
        self.audio.play(f"chip{random.randint(0, 2)}")

    def roll(self):
        if self.rolling:
            return
        if not self.bets:
            self.show("Pon fichas en alguna casilla", MUTED)
            return
        total = sum(self.bets.values())
        if not self.take_bet(total):
            return
        self.last_bets = dict(self.bets)
        if self.use_cheat():
            res = max(self.bets, key=lambda f: self.bets[f])
        elif self.forced is not None:
            fav = self.forced
            p = self.reliable(min(0.45, 3 / self.faces))
            res = fav if random.random() < p else random.choice([f for f in range(1, self.faces + 1) if f != fav])
        else:
            res = random.randint(1, self.faces)
        self.forced = None
        self.tip = None
        self.total = total
        self.result = None
        self.rolling = True
        self.die.roll(res, 1.7)
        self.audio.play("dice")

    def update(self, dt):
        self.win_t += dt
        if self.rolling:
            done = self.die.update(dt, lambda amp: self.audio.play("dice_hit", 0.4 + amp * 0.6, throttle=0.05))
            if done:
                self.rolling = False
                self.finish()

    def finish(self):
        res = self.die.result
        self.result = res
        self.win_t = 0.0
        self.hist.append(res)
        gross = self.bets.get(res, 0) * self.payout()
        if gross > 0 and self.faces == 20:
            self.feat("bote_d20")
        if self.faces == 20:
            single = len(self.bets) == 1
            n = self.state.count("bote_d20_run", add=1) if (gross > 0 and single) else self.state.count("bote_d20_run", 0)
            if n >= 3:
                self.feat("bote_d20_3")
        self.pay(self.total, gross, label=f"Sale el {res}", pos=self.die_center())
        if sum(self.bets.values()) > self.state.money + 1e-9:
            self.bets = {}

    def die_center(self):
        return (self.vis.x + 200, self.vis.y + self.vis.h // 2 + 10)

    def draw(self, surf, rect):
        ui = self.ui
        v = self.vis
        felt(surf, v, (36, 104, 74))
        # dado
        cx, cy = self.die_center()
        hop = self.die.hop * 110
        gfx.rrect(surf, (cx - 70 + hop * 0.2, cy + 92, 140 - hop * 0.4, 20), (0, 0, 0, 100), 8)
        img = self.die.render(240 if self.faces > 6 else 220)
        surf.blit(img, img.get_rect(center=(cx, cy - hop)))
        if self.result is not None and not self.rolling:
            k = gfx.ease_out_back(min(1, self.win_t / 0.3))
            r = pygame.Rect(0, 0, int(120 * k), int(56 * k))
            r.center = (cx, v.y + 44)
            if r.w > 10:
                gfx.box(surf, r, (*PANEL_LO, 255), 8, outline=GOLD, ow=4, shadow_off=4)
                if k > 0.6:
                    gfx.text(surf, str(self.result), r.center, 26, "bl", GOLD_HI, anchor="center")
        # historial
        for i, h in enumerate(self.hist[-8:][::-1]):
            p = (v.x + 30 + i * 38, v.bottom - 30)
            gfx.rrect(surf, (p[0] - 16, p[1] - 16, 32, 32), (*(PANEL_LO if i else (90, 70, 20)), 255), 6,
                      border=LINE, bw=4)
            gfx.text(surf, str(h), p, 12, "b", TEXT, anchor="center")
        # tablero
        cols, rows = GRID[self.faces]
        bx0 = v.x + 400
        bw = v.right - 24 - bx0
        bh = v.h - 130
        cw, chh = bw // cols, min(110, bh // rows)
        by0 = v.y + 70
        gfx.text(surf, f"La casilla ganadora paga x{fmt_num(self.payout())}", (bx0, v.y + 26), 14, "b", (220, 240, 225))
        for f in range(1, self.faces + 1):
            i = f - 1
            r = pygame.Rect(bx0 + (i % cols) * cw + 4, by0 + (i // cols) * chh + 4, cw - 8, chh - 8)
            wid = ("bote", f)
            h = ui.hover(r) and not self.rolling
            hv = ui.anim(wid, 1.0 if h else 0.0, 18)
            win = self.result == f and not self.rolling
            fill = (253, 162, 0) if win else gfx.lerp_col((30, 84, 60), (50, 120, 88), hv)
            gfx.box(surf, r.move(0, -int(3 * hv)), (*fill, 255), 8, ow=4, shadow_off=4)
            gfx.text(surf, str(f), (r.x + 12, r.y + 14), 16, "bl", TEXT, anchor="midleft")
            amt = self.bets.get(f)
            if amt:
                chip = art.chip_with_text(44 if chh > 80 else 36, amt)
                surf.blit(chip, chip.get_rect(center=(r.centerx + 8, r.centery + 6)))
            if self.tip and self.forced == f:
                gfx.text(surf, "★", (r.right - 14, r.y + 14), 14, "b", GOLD_HI, anchor="center")
            if h:
                ui.hot_any = True
                if ui.pressed:
                    ui.active = wid
                if ui.released and ui.active == wid:
                    self.add_bet(f)
                if ui.rpressed and f in self.bets:
                    del self.bets[f]
                    self.audio.play("chip1", 0.6)
        self.cheat_pill(surf, v.x + 24, v.bottom - 92, 250)
        pill = self.hint_pill(surf, bx0, v.bottom - 50, 260)
        if pill and self.hint_ready() and self.tip is None and not self.rolling:
            if ui.button("hint", (pill.right + 10, pill.y - 6, 150, 44), "Mirar dado", "gold", size=12):
                self.use_hint()
                self.forced = random.randint(1, self.faces)
                self.tip = True
                self.show(f"El {self.forced} sale más de lo normal en la próxima tirada", GOLD_HI)
        # controles
        c = self.controls_rect(rect)
        controls_bg(surf, c)
        self.bet_control(surf, c.x + 16, c.y + 10, "VALOR DE LA FICHA")
        total = sum(self.bets.values())
        gfx.text(surf, f"En juego: {fmt_money(total)}", (c.x + 372, c.y + 14), 12, "b", GOLD_HI)
        if ui.button("clear", (c.x + 372, c.y + 38, 100, 48), "Borrar", "dark", enabled=not self.rolling, size=12):
            self.bets = {}
        if ui.button("repeat", (c.x + 478, c.y + 38, 100, 48), "Repetir", "dark",
                     enabled=not self.rolling and bool(self.last_bets), size=12):
            if sum(self.last_bets.values()) <= self.state.money + 1e-9:
                self.bets = dict(self.last_bets)
        if ui.button("all", (c.x + 584, c.y + 38, 100, 48), "A todas", "dark", enabled=not self.rolling, size=12,
                     tooltip="Pone una ficha en cada casilla"):
            for f in range(1, self.faces + 1):
                self.add_bet(f)
        keys = ui.keys if not ui.focus else []
        if ui.button("roll", (c.right - 170, c.y + 18, 154, 70), "TIRAR", "green", enabled=not self.rolling and
                     bool(self.bets), size=18, sound=None) or (pygame.K_SPACE in keys and not self.rolling):
            self.roll()
