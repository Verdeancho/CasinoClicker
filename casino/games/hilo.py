import math
import random

import pygame

from .base import BaseGame
from .common import felt, controls_bg, dark_panel, CardObj
from .. import gfx, art
from ..fmt import fmt_money, fmt_num
from ..gfx import TEXT, MUTED, GOLD, GOLD_HI, GREEN, RED

EDGE = 0.97
BIG_W, BIG_H = 150, 212


def rand_card():
    return (random.randint(1, 13), random.randint(0, 3))


class HiLo(BaseGame):
    gid = "hilo"

    def setup(self):
        self.active = False
        self.pbet = 0.0
        self.mult = 1.0
        self.card = rand_card()
        self.trail = []
        self.correct = 0
        self.life_used = False
        self.flip = None   # animación de giro
        self.mult_disp = 1.0
        self.next = None       # siguiente carta ya decidida (vistazo)
        self.tip = None
        self.auto_on = False
        self.auto_text = "3.00"
        self.xray = False        # baraja ordenada (trampa)

    def p_higher(self):
        return (13 - self.card[0]) / 13

    def p_lower(self):
        return (self.card[0] - 1) / 13

    @staticmethod
    def factor(p):
        return EDGE / p if p > 0 else 0

    def start(self):
        if self.active or self.flip:
            return
        if not self.take_bet(self.bet):
            return
        self.pbet = self.bet
        self.mult = 1.0
        self.correct = 0
        self.life_used = False
        self.active = True
        self.xray = self.use_cheat()
        if self.xray:
            self.next = rand_card()
        self.trail = [(self.card, None)]
        self.show("¿Mayor o menor?", TEXT)

    def next_card(self, on_done):
        new = self.next if self.next is not None else rand_card()
        self.next = rand_card() if self.xray else None
        self.tip = None
        self.flip = {"t": 0.0, "old": self.card, "new": new, "cb": on_done}
        self.audio.play(f"card{random.randint(0, 2)}")

    def guess(self, higher):
        if not self.active or self.flip:
            return
        old = self.card
        p = self.p_higher() if higher else self.p_lower()
        f = self.factor(p)

        def check(new):
            ok = new[0] > old[0] if higher else new[0] < old[0]
            v = self.vis
            if ok:
                self.mult *= f
                self.correct += 1
                self.trail.append((new, True))
                self.audio.play(f"gem{min(15, self.correct - 1)}")
                self.fx.sparks(v.centerx, v.y + 200, 16, (120, 255, 180))
                self.show(f"¡Bien! x{fmt_num(self.mult)}", GREEN)
                if self.correct >= 10:
                    self.feat("hilo_10")
                if self.auto_on and self.state.lvl("hilo_auto"):
                    from ..fmt import parse_amount
                    tgt = parse_amount(self.auto_text)
                    if tgt and self.mult >= tgt:
                        self.later(0.3, self.cashout)
            else:
                self.trail.append((new, False))
                self.active = False
                self.xray = False
                self.fx.add_shake(4)
                self.pay(self.pbet, 0, label=f"Sale {art.rank_str(new[0])}")
        self.next_card(check)

    def skip(self):
        if not self.active or self.flip:
            return
        self.next_card(lambda new: self.trail.append((new, None)))

    def cashout(self):
        if not self.active or self.flip:
            return
        self.active = False
        self.xray = False
        self.audio.play("cashout")
        self.pay(self.pbet, self.pbet * self.mult, label=f"Retirada x{fmt_num(self.mult)}", quiet=True)

    def update(self, dt):
        self.mult_disp = gfx.approach(self.mult_disp, self.mult, dt, 10)
        f = self.flip
        if f:
            f["t"] += dt
            if f["t"] >= 0.32 and f.get("swapped") is None:
                f["swapped"] = True
                self.card = f["new"]
            if f["t"] >= 0.5:
                self.flip = None
                f["cb"](f["new"])

    def draw(self, surf, rect):
        ui = self.ui
        v = self.vis
        felt(surf, v, (34, 82, 96), (150, 200, 220))
        pill = self.hint_pill(surf, v.right - 270, v.bottom - 50, 250)
        if pill and self.hint_ready() and self.tip is None and self.active and not self.flip:
            if ui.button("hint", (pill.x - 130, pill.y - 5, 120, 44), "Mirar", "gold", size=12):
                self.use_hint()
                self.next = rand_card()
                hi = self.next[0] > self.card[0]
                said = hi if random.random() < self.reliable(0.70) else not hi
                self.tip = "MAYOR" if said else "MENOR O IGUAL"
        self.cheat_pill(surf, v.x + 24, v.bottom - 50, 250)
        if self.xray and self.active and self.next is not None:
            img = art.card_sprite(self.next, 44, 62)
            surf.blit(img, (v.right - 80, v.y + 120))
            gfx.text(surf, "SIGUIENTE", (v.right - 58, v.y + 104), 12, "b", (220, 170, 255), anchor="center")
        if self.tip:
            gfx.wavy_text(surf, f"De reojo parece... {self.tip}", (v.centerx, v.y + 316), 14, GOLD_HI, self.t, 2, 5)
        if self.state.lvl("hilo_auto"):
            from .common import toggle_pill
            ax, ay = v.right - 250, v.bottom - 140
            gfx.text(surf, "AUTO-RETIRO x", (ax, ay), 12, "b", MUTED)
            txt, done = ui.text_input(("hilo", "auto"), (ax, ay + 18, 90, 40), self.auto_text, size=14)
            if ui.focus == ("hilo", "auto") or done:
                self.auto_text = txt or self.auto_text
            self.auto_on = toggle_pill(ui, ("hilo", "aon"), surf, (ax + 100, ay + 26, 100, 24), "Activar", self.auto_on)
        cx, cy = v.centerx, v.y + 190
        # carta grande con giro
        f = self.flip
        if f:
            t = f["t"] / 0.5
            lift = math.sin(min(1, t) * math.pi) * 26
            sx = abs(math.cos(min(1, t / 0.64) * math.pi)) if t < 0.64 else 1
            show_face = t >= 0.32
            img = art.card_sprite(self.card, BIG_W, BIG_H) if show_face else art.card_back(BIG_W, BIG_H)
            img = pygame.transform.smoothscale(img, (max(1, int(BIG_W * sx)), BIG_H))
        else:
            lift = 0
            img = art.card_sprite(self.card, BIG_W, BIG_H)
        sh = gfx.shadow_surf(BIG_W, BIG_H, 14, 12, 140)
        surf.blit(sh, (cx - BIG_W / 2 - 24, cy - BIG_H / 2 - 18 + lift * 0.3))
        gfx.blit_center(surf, img, (cx, cy - lift))
        # probabilidades a los lados
        ph, pl = self.p_higher(), self.p_lower()
        for side, (p, lbl, col, arrow) in enumerate(((ph, "MAYOR", (80, 220, 140), "▲"), (pl, "MENOR", (240, 100, 120), "▼"))):
            x = cx + (230 if side == 0 else -230)
            box = pygame.Rect(0, 0, 170, 110)
            box.center = (x, cy)
            dark_panel(surf, box, 16, (24, 40, 52), (14, 24, 32), gfx.mul_col(col, 0.6))
            gfx.text(surf, f"{arrow} {lbl}", (box.centerx, box.y + 22), 16, "bl", col, anchor="center")
            gfx.text(surf, f"{p * 100:.1f}%", (box.centerx, box.y + 52), 24, "num", TEXT, anchor="center")
            gfx.text(surf, f"x{fmt_num(self.factor(p))}" if p else "imposible", (box.centerx, box.y + 84), 14, "b",
                     GOLD if p else MUTED, anchor="center")
        # multiplicador
        mb = pygame.Rect(v.x + 24, v.y + 20, 220, 92)
        dark_panel(surf, mb, 16, (24, 40, 52), (14, 24, 32))
        gfx.text(surf, "MULTIPLICADOR", (mb.x + 16, mb.y + 12), 12, "b", MUTED)
        gfx.text(surf, f"x{fmt_num(self.mult_disp)}", (mb.x + 16, mb.y + 30), 32, "num",
                 GOLD_HI if self.active else MUTED)
        if self.active:
            gfx.text(surf, f"cobras {fmt_money(self.pbet * self.mult)}", (mb.x + 16, mb.y + 70), 12, "sb", TEXT)
        info = f"Aciertos: {self.correct}"

        gfx.text(surf, info, (v.right - 24, v.y + 24), 13, "b", (200, 230, 240), anchor="topright")
        gfx.text(surf, "Las cartas iguales pierden · As = 1, K = 13", (v.right - 24, v.y + 46), 12, "r",
                 (160, 200, 210), anchor="topright")
        # rastro de cartas
        trail = self.trail[-11:]
        for i, (card, ok) in enumerate(trail):
            x = v.x + 40 + i * 72
            img = art.card_sprite(card, 56, 80)
            y = v.bottom - 110
            surf.blit(img, (x, y))
            if ok is not None:
                gfx.circle(surf, (x + 50, y + 6), 9, GREEN if ok else RED)
                gfx.text(surf, "✓" if ok else "✗", (x + 50, y + 6), 11, "sym", (10, 20, 10), anchor="center")
        # controles
        c = self.controls_rect(rect)
        controls_bg(surf, c)
        self.bet_control(surf, c.x + 16, c.y + 12)
        a = self.active and not self.flip
        keys = ui.keys if not ui.focus else []
        if not self.active:
            if ui.button("start", (c.right - 200, c.y + 18, 180, 64), "APOSTAR", "green", enabled=not self.flip, size=20,
                         sound=None) or (pygame.K_SPACE in keys and not self.flip):
                self.start()
        else:
            if ui.button("hi", (c.x + 372, c.y + 18, 110, 64), "▲ Mayor", "green", enabled=a and ph > 0, size=16,
                         sub=f"x{fmt_num(self.factor(ph))}" if ph else "—", sound=None) or (a and ph > 0 and pygame.K_UP in keys):
                self.guess(True)
            if ui.button("lo", (c.x + 488, c.y + 18, 110, 64), "▼ Menor", "red", enabled=a and pl > 0, size=16,
                         sub=f"x{fmt_num(self.factor(pl))}" if pl else "—", sound=None) or (a and pl > 0 and pygame.K_DOWN in keys):
                self.guess(False)
            if ui.button("skip", (c.x + 604, c.y + 18, 90, 64), "Saltar", "dark", enabled=a, size=12):
                self.skip()
            if ui.button("cash", (c.right - 160, c.y + 18, 140, 64), "RETIRAR", "gold", enabled=a, size=17,
                         sub=fmt_money(self.pbet * self.mult), sound=None) or (a and pygame.K_SPACE in keys):
                self.cashout()
