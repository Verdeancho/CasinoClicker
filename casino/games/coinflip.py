import math
import random

import pygame

from .base import BaseGame
from .common import felt, controls_bg, history_pills, toggle_pill
from .. import gfx, skins
from ..fmt import fmt_money
from ..gfx import TEXT, MUTED, GOLD, GOLD_HI, GREEN, RED

PAYOUT = 1.96
HINT_P = 0.70          # fiabilidad oculta del chivatazo
SIZE = 180


class CoinFlip(BaseGame):
    gid = "coinflip"

    def setup(self):
        self.anim = None
        self.result = 0
        self.hist = []
        self.streak = 0
        self.auto = False
        self.side = 0
        self.forced = None     # resultado ya decidido (chivatazo o trampa)
        self.tip = None
        self.last_win = 0.0    # lo cobrado en la última tirada ganada (para "doblar")
        self.rest_t = 1.0      # tiempo desde que cayó (para el rebote)

    # ---------------------------------------------------------------- juego
    def flip(self, side, amount=None):
        if self.anim:
            return
        amount = self.bet if amount is None else amount
        if not self.take_bet(amount):
            self.auto = False
            return
        # hazaña "doble o nada x7": apostar todo lo ganado en la tirada anterior
        ride = self.state.count("coin_ride")
        if not (self.last_win > 0 and amount >= self.last_win * 0.999):
            ride = 0
        self.state.count("coin_ride", ride)
        self.side = side
        if self.use_cheat():
            self.forced = side
        self.result = self.forced if self.forced is not None else random.randint(0, 1)
        self.forced = None
        self.tip = None
        # medias vueltas: su paridad decide qué cara queda arriba al caer
        half_turns = 2 * random.randint(4, 6) + self.result
        self.anim = {"t": 0.0, "dur": 1.15, "turns": half_turns, "bet": amount}
        self.audio.play("whoosh")

    def update(self, dt):
        self.rest_t += dt
        a = self.anim
        if not a:
            return
        a["t"] += dt
        if a["t"] >= a["dur"]:
            self.anim = None
            self.rest_t = 0.0
            self.finish(a["bet"])

    def finish(self, bet):
        won = self.side == self.result
        self.audio.play("ting", 0.8)
        self.hist.append(("CARA" if self.result == 0 else "CRUZ", GREEN if won else RED))
        self.streak = self.streak + 1 if won else 0
        if self.streak >= 10:
            self.feat("coin_streak10")
        payout = self.pay(bet, bet * PAYOUT if won else 0, label=f"¡{'CARA' if self.result == 0 else 'CRUZ'}!",
                          pos=(self.vis.centerx, self.vis.centery - 60))
        if won:
            ride = self.state.count("coin_ride", add=1)
            if ride >= 7:
                self.feat("coin_ride7")
            self.last_win = payout
        else:
            self.state.count("coin_ride", 0)
            self.last_win = 0.0
        self.fx.ring(self.vis.centerx, self.vis.centery + 30, GOLD, 60, 160, 0.5, 3)
        if self.auto:
            self.later(0.45, lambda: self.auto and self.flip(self.side))

    # ---------------------------------------------------------------- dibujo
    def coin_pose(self):
        """(altura, escala vertical con signo, giro) de la moneda en este instante."""
        a = self.anim
        if a:
            t = min(1.0, a["t"] / a["dur"])
            h = math.sin(t * math.pi) * 200 * (1 - 0.15 * t)
            ang = gfx.ease_out_cubic(t) * a["turns"] * math.pi
            return h, math.cos(ang), 0.0
        # pequeño rebote al caer
        rt = self.rest_t
        if rt < 0.5:
            bounce = abs(math.sin(rt * 2 * math.pi)) * 22 * math.exp(-rt * 7)
            wob = math.sin(rt * 26) * math.exp(-rt * 8)
            return bounce, (1.0 if self.result == 0 else -1.0) * (1 - 0.18 * abs(wob)), wob * 8
        return 0.0, 1.0 if self.result == 0 else -1.0, 0.0

    def draw(self, surf, rect):
        vis = self.vis
        felt(surf, vis)
        cx, base_y = vis.centerx, vis.centery + 50
        h, sy, rot = self.coin_pose()
        side = 0 if sy >= 0 else 1
        k = 1 + h / 1000
        size = int(SIZE * k)
        # sombra: se encoge y aclara al subir
        sw = int(SIZE * 0.9 * (1 - h / 420))
        sh = gfx.shadow_surf(max(10, sw), 22, 12, 10, int(150 * max(0.2, 1 - h / 300)))
        surf.blit(sh, sh.get_rect(center=(cx, base_y + SIZE * 0.5 + 4)))
        img = skins.flip_face(side, size)
        hgt = max(2, int(size * abs(sy)))
        y = base_y - h
        edge = int((1 - abs(sy)) * 18 * k)
        if edge > 1:
            er = pygame.Rect(0, 0, size - 6, hgt + edge)
            er.center = (cx, int(y + edge / 2))
            pygame.draw.ellipse(surf, gfx.INK, er.inflate(4, 4))
            pygame.draw.ellipse(surf, skins.flip_edge_col(side), er)
        face = pygame.transform.scale(img, (size, hgt))
        if abs(rot) > 0.3:
            face = pygame.transform.rotate(face, rot)
        gfx.blit_center(surf, face, (cx, y))
        if not self.anim and self.hist and self.rest_t < 1.5:
            gfx.glow(surf, (cx, y), 150, (130, 100, 20), 0.3 * max(0, 1 - self.rest_t / 1.5))
        # cabecera de la mesa
        gfx.text(surf, f"Paga x{PAYOUT}", (vis.x + 28, vis.y + 22), 16, "b", (255, 230, 160))
        gfx.text(surf, f"Racha: {self.streak}", (vis.x + 28, vis.y + 48), 14, "b", GREEN if self.streak else MUTED)
        ride = self.state.count("coin_ride")
        if ride and not self.state.flags.get("coin_ride7"):
            gfx.text(surf, f"Doble o nada: {ride}/7", (vis.x + 28, vis.y + 72), 12, "b", GOLD_HI)
        history_pills(surf, vis.right - 24, vis.y + 22, self.hist, 10, 58, 24, right_to_left=True)
        # controles
        c = self.controls_rect(rect)
        controls_bg(surf, c)
        self.bet_control(surf, c.x + 16, c.y + 12)
        busy = self.anim is not None
        ui = self.ui
        if ui.button("heads", (c.right - 360, c.y + 18, 165, 64), "CARA", "gold", enabled=not busy, size=20, sound=None):
            self.flip(0)
        if ui.button("tails", (c.right - 186, c.y + 18, 165, 64), "CRUZ", "blue", enabled=not busy, size=20, sound=None):
            self.flip(1)
        can_double = self.last_win > 0 and not busy and self.state.money >= self.last_win - 1e-9
        if ui.button("double", (c.x + 372, c.y + 14, 128, 40), "DOBLAR", "red", enabled=can_double, size=12,
                     sound=None, tooltip=f"Apuesta todo lo que acabas de ganar ({fmt_money(self.last_win)}) "
                                         "al mismo lado."):
            self.flip(self.side, self.last_win)
        self.auto = toggle_pill(ui, ("cf", "auto"), surf, (c.x + 376, c.y + 66, 120, 30), "Auto", self.auto)
        # ventaja y trampa
        pill = self.hint_pill(surf, vis.x + 24, vis.bottom - 54, 300)
        if pill and self.hint_ready() and self.tip is None and not busy:
            if ui.button("hint", (pill.right + 10, pill.y - 6, 150, 44), "Escuchar", "gold", size=12):
                self.use_hint()
                self.forced = random.randint(0, 1)
                said = self.forced if random.random() < self.reliable(HINT_P) else 1 - self.forced
                self.tip = "CARA" if said == 0 else "CRUZ"
        if self.tip:
            gfx.wavy_text(surf, f"«Psst... saldrá {self.tip}»", (vis.centerx, vis.y + 80), 16, GOLD_HI, self.t, 2, 5)
        self.cheat_pill(surf, vis.right - 290, vis.bottom - 54, 266)

    def on_hide(self):
        self.auto = False
