import random
from collections import Counter

import pygame

from .base import BaseGame
from .common import felt, controls_bg, CardObj
from .. import gfx, art
from ..fmt import fmt_money
from ..gfx import TEXT, MUTED, GOLD, GOLD_HI, GREEN, RED

PAYTABLE = [("royal", "Escalera real", 800), ("sflush", "Escalera de color", 50), ("quads", "Póker", 25),
            ("full", "Full", 9), ("flush", "Color", 6), ("straight", "Escalera", 4), ("trips", "Trío", 3),
            ("twopair", "Doble pareja", 2), ("jacks", "Pareja de J o más", 1)]
PAY_BY_ID = {k: (n, m) for k, n, m in PAYTABLE}
CW, CH = 128, 180


def evaluate(hand):
    ranks = sorted((r for r, _ in hand), reverse=True)
    suits = [s for _, s in hand]
    counts = Counter(ranks)
    flush = len(set(suits)) == 1
    uniq = sorted(set(ranks))
    straight = high = False
    if len(uniq) == 5:
        if uniq[-1] - uniq[0] == 4:
            straight = True
        if uniq == [1, 10, 11, 12, 13]:
            straight = high = True
    if straight and flush:
        return "royal" if high else "sflush"
    shape = sorted(counts.values(), reverse=True)
    if shape[0] == 4:
        return "quads"
    if shape == [3, 2]:
        return "full"
    if flush:
        return "flush"
    if straight:
        return "straight"
    if shape[0] == 3:
        return "trips"
    if shape == [2, 2, 1]:
        return "twopair"
    if shape[0] == 2:
        pair = [r for r, c in counts.items() if c == 2][0]
        if pair == 1 or pair >= 11:
            return "jacks"
    return None


class VideoPoker(BaseGame):
    gid = "videopoker"

    def setup(self):
        self.phase = "idle"
        self.objs = []
        self.held = [False] * 5
        self.deck = []
        self.pbet = 0.0
        self.pending = 0.0
        self.last_eval = None
        self.dbl = None

    def slot(self, i):
        v = self.vis
        return (v.centerx + (i - 2) * (CW + 20), v.y + 330)

    def deal(self):
        if self.phase == "idle":
            if not self.take_bet(self.bet):
                return
            self.pbet = self.bet
            self.deck = [(r, s) for s in range(4) for r in range(1, 14)]
            random.shuffle(self.deck)
            src = (self.vis.right + 80, self.vis.y - 40)
            self.objs = [CardObj(self.deck.pop(), src, self.slot(i), i * 0.08, True, CW, CH) for i in range(5)]
            self.held = [False] * 5
            self.last_eval = evaluate([o.card for o in self.objs])
            self.phase = "hold"
            self.banner = None
        elif self.phase == "hold":
            src = (self.vis.right + 80, self.vis.y - 40)
            k = 0
            for i in range(5):
                if not self.held[i]:
                    self.objs[i] = CardObj(self.deck.pop(), src, self.slot(i), k * 0.08, True, CW, CH)
                    k += 1
            self.phase = "drawing"
            self.later(0.45 + k * 0.08, self.resolve)

    def resolve(self):
        self.held = [False] * 5
        res = evaluate([o.card for o in self.objs])
        self.last_eval = res
        if res in ("quads", "sflush", "royal"):
            self.feat("vp_quads")
        if res in ("sflush", "royal"):
            self.feat("vp_sflush")
        if res == "royal":
            self.feat("vp_royal")
        mult = PAY_BY_ID[res][1] if res else 0
        for o in self.objs:
            o.hl = GOLD if res else None
        if res and self.state.lvl("vp_double"):
            self.pending = self.pbet * mult
            self.phase = "double"
            self.dbl = None
            self.audio.play("win1")
            self.show(f"{PAY_BY_ID[res][0]}: {fmt_money(self.pending)}. ¿Doble o nada?", GOLD)
            return
        self.phase = "idle"
        self.pay(self.pbet, self.pbet * mult, label=(PAY_BY_ID[res][0] + "!") if res else "Nada")

    def double(self, red):
        if self.phase != "double" or self.dbl:
            return
        card = (random.randint(1, 13), random.randint(0, 3))
        self.dbl = CardObj(card, (self.vis.centerx, self.vis.y - 60), (self.vis.centerx, self.vis.y + 330), 0, False, CW, CH)
        ok = (card[1] in (1, 2)) == red

        def flip():
            self.dbl.reveal(self.audio)
            self.later(0.45, after)

        def after():
            if ok:
                self.pending *= 2
                self.audio.play("win2")
                self.show(f"¡Acierto! Premio: {fmt_money(self.pending)}", GREEN)
                self.later(0.9, lambda: setattr(self, "dbl", None))
            else:
                self.phase = "idle"
                self.pending = 0
                self.pay(self.pbet, 0, label="Fallaste el doble o nada")
                self.later(1.2, lambda: setattr(self, "dbl", None))
        self.later(0.45, flip)

    def collect(self):
        if self.phase != "double" or self.dbl:
            return
        self.phase = "idle"
        self.audio.play("cashout")
        self.pay(self.pbet, self.pending, label="Cobras", quiet=True)
        self.pending = 0

    def update(self, dt):
        for o in self.objs:
            o.update(dt, self.audio)
            o.lift = gfx.approach(o.lift, 0, dt, 12)
        if self.dbl:
            self.dbl.update(dt, self.audio)

    def draw(self, surf, rect):
        ui = self.ui
        v = self.vis
        felt(surf, v, (18, 34, 110), (200, 180, 90))
        # tabla de pagos
        pt = pygame.Rect(v.x + 24, v.y + 18, v.w - 48, 150)
        gfx.rrect(surf, pt, (8, 14, 50, 230), 14, border=(200, 170, 80), bw=2)
        for i, (k, name, m) in enumerate(PAYTABLE):
            col, row = divmod(i, 5)
            x = pt.x + 20 + col * (pt.w // 2)
            y = pt.y + 14 + row * 26
            hl = self.last_eval == k and self.phase in ("hold", "idle", "double", "drawing")
            if hl:
                gfx.rrect(surf, (x - 8, y - 2, pt.w // 2 - 24, 24), (255, 210, 70, 255), 6)
            c = (30, 20, 6) if hl else (255, 226, 130)
            gfx.text(surf, name.upper(), (x, y), 14, "bl", c)
            gfx.text(surf, f"x{m}", (x + pt.w // 2 - 40, y), 14, "bl", c, anchor="topright")
        if self.phase == "hold":
            gfx.text(surf, "Clic en las cartas para GUARDARLAS y pulsa CAMBIAR", (v.centerx, v.y + 196), 14, "b",
                     (200, 210, 255), anchor="center")
        # cartas
        for i, o in enumerate(self.objs if self.phase != "double" or not self.dbl else []):
            x, y = self.slot(i)
            r = pygame.Rect(x - CW / 2, y - CH / 2, CW, CH)
            if self.phase == "hold":
                wid = ("vp", i)
                h = ui.hover(r)
                if h:
                    ui.hot_any = True
                    o.lift = max(o.lift, 6)
                    if ui.pressed:
                        ui.active = wid
                    if ui.released and ui.active == wid:
                        self.held[i] = not self.held[i]
                        self.audio.play(f"chip{i % 3}", 0.7)
            if self.held[i]:
                o.lift = max(o.lift, 16)
                o.hl = GOLD
            elif self.phase == "hold":
                o.hl = None
            o.draw(surf)
            if self.held[i]:
                tag = pygame.Rect(0, 0, 100, 26)
                tag.center = (x, y + CH / 2 + 22)
                gfx.rrect(surf, tag, (255, 210, 70, 255), 13)
                gfx.text(surf, "GUARDADA", tag.center, 12, "bl", (40, 26, 6), anchor="center")
        if not self.objs:
            for i in range(5):
                x, y = self.slot(i)
                surf.blit(art.card_back(CW, CH), (x - CW / 2, y - CH / 2))
        if self.phase == "double" or self.dbl:
            box = pygame.Rect(0, 0, 420, 70)
            box.center = (v.centerx, v.y + 200)
            gfx.rrect(surf, box, (10, 14, 50, 240), 16, border=GOLD, bw=2)
            gfx.text(surf, "DOBLE O NADA", (box.centerx, box.y + 18), 18, "bl", GOLD_HI, anchor="center")
            gfx.text(surf, f"En juego: {fmt_money(self.pending)}  ·  ¿roja o negra?", (box.centerx, box.y + 46), 13, "b",
                     TEXT, anchor="center")
            if self.dbl:
                self.dbl.draw(surf)
            else:
                surf.blit(art.card_back(CW, CH), (v.centerx - CW / 2, v.y + 330 - CH / 2))
        # controles
        c = self.controls_rect(rect)
        controls_bg(surf, c)
        self.bet_control(surf, c.x + 16, c.y + 12)
        keys = ui.keys if not ui.focus else []
        if self.phase == "double":
            free = self.dbl is None
            if ui.button("red", (c.x + 380, c.y + 18, 110, 64), "Roja", "red", enabled=free, size=17, sound=None):
                self.double(True)
            if ui.button("black", (c.x + 498, c.y + 18, 110, 64), "Negra", "dark", enabled=free, size=17, sound=None):
                self.double(False)
            if ui.button("collect", (c.right - 200, c.y + 18, 180, 64), "COBRAR", "gold", enabled=free, size=19,
                         sub=fmt_money(self.pending), sound=None):
                self.collect()
        else:
            lbl = "CAMBIAR" if self.phase == "hold" else "REPARTIR"
            can = self.phase in ("idle", "hold")
            if ui.button("deal", (c.right - 200, c.y + 18, 180, 64), lbl, "green", enabled=can, size=20, sound=None) or \
                    (can and pygame.K_SPACE in keys):
                self.deal()
