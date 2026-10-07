"""Baccarat con tres variantes: Punto y Banca, Dragón y Tigre, y Guerra de casino."""
import random

import pygame

from .base import BaseGame
from .common import felt, controls_bg, CardObj, history_pills
from .. import gfx, art
from ..fmt import fmt_money
from ..gfx import TEXT, MUTED, DIM, GOLD, GOLD_HI, GREEN, RED, ORANGE, BLUE, PANEL_LO, LINE

CW, CH = 92, 130


def bac_value(card):
    r = card[0]
    return 0 if r >= 10 else r


def hand_total(cards):
    return sum(bac_value(c) for c in cards) % 10


def war_rank(card):
    return 14 if card[0] == 1 else card[0]


class Baccarat(BaseGame):
    gid = "baccarat"

    def setup(self):
        self.shoe = []
        self.bets = {}
        self.last_bets = {}
        self.hist = []
        self.on_variant()

    def on_variant(self):
        self.player = []
        self.banker = []
        self.phase = "idle"
        self.bets = {}
        self.result = None
        self.war_bet = 0.0
        self.marked = None

    def can_change_variant(self):
        return self.phase == "idle"

    def spots(self):
        if self.variant == "dragon":
            return [("dragon", "DRAGÓN", "1:1", (200, 70, 60)), ("tie", "EMPATE", "8:1", (60, 150, 100)),
                    ("tiger", "TIGRE", "1:1", (230, 150, 40))]
        return [("player", "PUNTO", "1:1", (0, 130, 220)), ("tie", "EMPATE", "8:1", (60, 150, 100)),
                ("banker", "BANCA", "0,95:1", (220, 70, 70))]

    def draw_card(self):
        if len(self.shoe) < 52:
            self.shoe = [(r, s) for _ in range(8) for s in range(4) for r in range(1, 14)]
            random.shuffle(self.shoe)
        return self.shoe.pop()

    def pos(self, side, i):
        v = self.vis
        x = v.centerx + (-220 if side == "p" else 120) + i * 64
        return (x, v.y + 170)

    def deal_to(self, side, delay):
        c = self.draw_card()
        lst = self.player if side == "p" else self.banker
        o = CardObj(c, (self.vis.right - 60, self.vis.y - 30), self.pos(side, len(lst)), delay, True, CW, CH)
        lst.append(o)
        return c

    def add_bet(self, key):
        if self.phase != "idle":
            return
        total = sum(self.bets.values()) + self.bet
        if total > self.state.money + 1e-9:
            self.show("Fondos insuficientes", RED)
            self.audio.play("error")
            return
        self.bets[key] = self.bets.get(key, 0) + self.bet
        self.audio.play(f"chip{random.randint(0, 2)}")

    # ------------------------------------------------------------- ronda
    def deal(self):
        if self.phase != "idle":
            return
        if self.variant == "war":
            if not self.take_bet(self.bet):
                return
            self.total = self.bet
            self.bets = {"war": self.bet}
        else:
            if not self.bets:
                self.show("Pon fichas en Punto, Banca o Empate", MUTED)
                return
            self.total = sum(self.bets.values())
            if not self.take_bet(self.total):
                return
            self.last_bets = dict(self.bets)
        self.player, self.banker = [], []
        self.result = None
        self.banner = None
        self.marked = None
        self.phase = "dealing"
        if self.variant == "punto":
            for i, side in enumerate("pbpb"):
                self.deal_to(side, i * 0.25)
            self.later(1.3, self.third_cards)
        else:
            self.deal_to("p", 0.0)
            self.deal_to("b", 0.25)
            self.later(0.9, self.resolve_simple)

    def third_cards(self):
        p = [o.card for o in self.player]
        b = [o.card for o in self.banker]
        pt, bt = hand_total(p), hand_total(b)
        delay = 0.0
        if pt >= 8 or bt >= 8:
            self.later(0.4, self.resolve_punto)
            return
        p3 = None
        if pt <= 5:
            p3 = self.deal_to("p", 0.0)
            delay = 0.6
        bt = hand_total(b)
        draw_b = False
        if p3 is None:
            draw_b = bt <= 5
        else:
            v3 = bac_value(p3)
            if bt <= 2:
                draw_b = True
            elif bt == 3:
                draw_b = v3 != 8
            elif bt == 4:
                draw_b = 2 <= v3 <= 7
            elif bt == 5:
                draw_b = 4 <= v3 <= 7
            elif bt == 6:
                draw_b = 6 <= v3 <= 7
        if draw_b:
            self.deal_to("b", delay)
            delay += 0.6
        self.later(delay + 0.5, self.resolve_punto)

    def resolve_punto(self):
        pt = hand_total([o.card for o in self.player])
        bt = hand_total([o.card for o in self.banker])
        res = "player" if pt > bt else ("banker" if bt > pt else "tie")
        self.result = res
        gross = 0.0
        for k, amt in self.bets.items():
            if res == "tie":
                gross += amt * 9 if k == "tie" else amt
            elif k == res:
                gross += amt * (2 if k == "player" else 1.95)
        if res == "tie" and self.bets.get("tie"):
            self.feat("baccarat_tie")
            if self.state.count("baccarat_ties", add=1) >= 3:
                self.feat("baccarat_3ties")
        self.hist.append(({"player": "P", "banker": "B", "tie": "E"}[res],
                          {"player": BLUE, "banker": RED, "tie": GREEN}[res]))
        self.phase = "idle"
        name = {"player": "Gana Punto", "banker": "Gana Banca", "tie": "Empate"}[res]
        self.pay(self.total, gross, label=f"{name} ({pt}-{bt})")

    def resolve_simple(self):
        pc, bc = self.player[0].card, self.banker[0].card
        if self.variant == "dragon":
            d, t = pc[0], bc[0]
            res = "dragon" if d > t else ("tiger" if t > d else "tie")
            self.result = res
            gross = 0.0
            for k, amt in self.bets.items():
                if res == "tie":
                    gross += amt * 9 if k == "tie" else amt * 0.5
                elif k == res:
                    gross += amt * 2
            if res == "tie" and self.bets.get("tie"):
                self.feat("baccarat_tie")
                if self.state.count("baccarat_ties", add=1) >= 3:
                    self.feat("baccarat_3ties")
            self.hist.append(({"dragon": "D", "tiger": "T", "tie": "E"}[res],
                              {"dragon": RED, "tiger": ORANGE, "tie": GREEN}[res]))
            self.phase = "idle"
            self.pay(self.total, gross, label={"dragon": "Gana el Dragón", "tiger": "Gana el Tigre", "tie": "Empate"}[res])
            return
        # guerra de casino
        p, b = war_rank(pc), war_rank(bc)
        if p > b:
            self.phase = "idle"
            self.result = "player"
            self.pay(self.total, self.total * 2, label="Tu carta gana")
        elif b > p:
            self.phase = "idle"
            self.result = "banker"
            self.pay(self.total, 0, label="Gana el crupier")
        else:
            self.phase = "war_choice"
            self.show("¡Empate! ¿Vas a la guerra o te rindes?", GOLD_HI)

    def surrender(self):
        if self.phase != "war_choice":
            return
        self.phase = "idle"
        self.pay(self.total, self.total / 2, label="Te rindes: recuperas la mitad")

    def go_war(self):
        if self.phase != "war_choice":
            return
        if not self.state.wager(self.gid, self.total):
            self.show("No tienes dinero para ir a la guerra", RED)
            return
        self.war_bet = self.total
        for _ in range(3):
            self.draw_card()
        self.phase = "dealing"
        self.deal_to("p", 0.2)
        self.deal_to("b", 0.5)
        self.later(1.2, self.resolve_war)

    def resolve_war(self):
        p, b = war_rank(self.player[-1].card), war_rank(self.banker[-1].card)
        self.phase = "idle"
        stake = self.total + self.war_bet
        if p >= b:
            self.pay(stake, self.total + self.war_bet * 2, label="¡Ganas la guerra!")
        else:
            self.pay(stake, 0, label="Pierdes la guerra")
        self.war_bet = 0.0

    def update(self, dt):
        for o in self.player + self.banker:
            o.update(dt, self.audio)

    # ----------------------------------------------------------------- dibujo
    def draw(self, surf, rect):
        ui = self.ui
        v = self.vis
        felt(surf, v, (40, 96, 74))
        names = {"punto": ("PUNTO", "BANCA"), "dragon": ("DRAGÓN", "TIGRE"), "war": ("TÚ", "CRUPIER")}[self.variant]
        for side, label, x in (("p", names[0], v.centerx - 190), ("b", names[1], v.centerx + 150)):
            gfx.text(surf, label, (x, v.y + 50), 18, "bl", TEXT, anchor="center")
            cards = self.player if side == "p" else self.banker
            if cards and self.variant == "punto" and all(o.done for o in cards):
                t = hand_total([o.card for o in cards])
                gfx.rrect(surf, (x - 30, v.y + 250, 60, 40), (*PANEL_LO, 255), 8, border=LINE, bw=4)
                gfx.text(surf, str(t), (x, v.y + 270), 18, "bl", GOLD_HI, anchor="center")
        for o in self.player + self.banker:
            o.draw(surf)
        history_pills(surf, v.right - 16, v.y + 14, self.hist, 12, 34, 26, right_to_left=True)
        # casillas de apuesta
        if self.variant != "war":
            spots = self.spots()
            w = (v.w - 120) // 3
            for i, (key, label, pay, col) in enumerate(spots):
                r = pygame.Rect(v.x + 40 + i * (w + 20), v.bottom - 170, w, 130)
                wid = ("bac", key)
                h = ui.hover(r) and self.phase == "idle"
                hv = ui.anim(wid, 1.0 if h else 0.0, 18)
                win = self.result == key and self.phase == "idle"
                fill = (253, 162, 0) if win else gfx.lerp_col(gfx.mul_col(col, 0.7), col, hv)
                gfx.box(surf, r.move(0, -int(3 * hv)), (*fill, 255), 12, ow=4, shadow_off=5)
                gfx.text(surf, label, (r.centerx, r.y + 30), 18, "bl", TEXT, anchor="center")
                gfx.text(surf, pay, (r.centerx, r.y + 58), 12, "r", (240, 240, 240), anchor="center")
                amt = self.bets.get(key)
                if amt:
                    chip = art.chip_with_text(50, amt)
                    surf.blit(chip, chip.get_rect(center=(r.centerx, r.y + 96)))
                if h:
                    ui.hot_any = True
                    if ui.pressed:
                        ui.active = wid
                    if ui.released and ui.active == wid:
                        self.add_bet(key)
                    if ui.rpressed and key in self.bets:
                        del self.bets[key]
        else:
            gfx.text_wrapped(surf, "Carta más alta gana (el As es la más alta). Si empatas puedes rendirte (recuperas "
                                   "la mitad) o ir a la guerra doblando la apuesta.", (v.x + 40, v.bottom - 120), 12,
                             "r", (220, 236, 226), v.w - 80)
        v = self.vis
        pill = self.hint_pill(surf, v.x + 24, v.bottom - 54, 260)
        if pill and self.hint_ready() and self.marked is None and self.phase == "idle":
            if ui.button("hint", (pill.right + 10, pill.y - 6, 150, 44), "Mirar marca", "gold", size=12):
                self.use_hint()
                if len(self.shoe) < 60:
                    self.shoe = [(r, s) for _ in range(8) for s in range(4) for r in range(1, 14)]
                    random.shuffle(self.shoe)
                real = self.shoe[-1]
                if random.random() < self.reliable(0.75):
                    self.marked = real
                else:
                    self.marked = random.choice([c for c in self.shoe[-20:] if c[0] != real[0]] or [real])
        if self.marked is not None:
            who = {"punto": "Punto", "dragon": "Dragón", "war": "tu carta"}.get(self.variant, "Punto")
            gfx.wavy_text(surf, f"Primera carta de {who}: {art.rank_str(self.marked[0])}", (v.centerx, v.y + 40), 14,
                          GOLD_HI, self.t, 2, 5)
        # controles
        c = self.controls_rect(rect)
        controls_bg(surf, c)
        self.bet_control(surf, c.x + 16, c.y + 10, "APUESTA" if self.variant == "war" else "VALOR DE LA FICHA")
        keys = ui.keys if not ui.focus else []
        if self.phase == "war_choice":
            if ui.button("surr", (c.x + 380, c.y + 18, 200, 70), "RENDIRSE", "dark", size=15,
                         sub=f"recuperas {fmt_money(self.total / 2)}"):
                self.surrender()
            if ui.button("war", (c.right - 250, c.y + 18, 234, 70), "¡GUERRA!", "red", size=16,
                         sub=f"+{fmt_money(self.total)}", sound=None):
                self.go_war()
            return
        if self.variant != "war":
            total = sum(self.bets.values())
            gfx.text(surf, f"En juego: {fmt_money(total)}", (c.x + 372, c.y + 14), 12, "b", GOLD_HI)
            if ui.button("clear", (c.x + 372, c.y + 38, 110, 48), "Borrar", "dark", enabled=self.phase == "idle", size=12):
                self.bets = {}
            if ui.button("repeat", (c.x + 490, c.y + 38, 110, 48), "Repetir", "dark",
                         enabled=self.phase == "idle" and bool(self.last_bets), size=12):
                if sum(self.last_bets.values()) <= self.state.money + 1e-9:
                    self.bets = dict(self.last_bets)
        if ui.button("deal", (c.right - 200, c.y + 18, 184, 70), "REPARTIR", "green", enabled=self.phase == "idle",
                     size=16, sound=None) or (pygame.K_SPACE in keys and self.phase == "idle"):
            self.deal()
