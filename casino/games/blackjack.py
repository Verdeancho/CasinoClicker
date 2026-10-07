import math
import random

import pygame

from .base import BaseGame
from .common import felt, controls_bg, CardObj
from .. import gfx, art
from ..fmt import fmt_money
from ..gfx import TEXT, MUTED, GOLD, GOLD_HI, GREEN, RED

N_DECKS = 6
CW, CH = 92, 130


def card_value(card):
    r = card[0]
    return 11 if r == 1 else min(r, 10)


def hand_value(cards):
    total = sum(card_value(c) for c in cards)
    aces = sum(1 for c in cards if c[0] == 1)
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total, aces > 0 and total <= 21


def is_blackjack(cards):
    return len(cards) == 2 and hand_value(cards)[0] == 21


def hilo_value(card):
    v = card_value(card)
    return 1 if 2 <= v <= 6 else (-1 if v >= 10 else 0)


def basic_strategy(cards, up, can_double, can_split):
    d = card_value(up)
    total, soft = hand_value(cards)
    if can_split and len(cards) == 2 and card_value(cards[0]) == card_value(cards[1]):
        v = card_value(cards[0])
        if v in (11, 8) or (v == 9 and d not in (7, 10, 11)) or (v in (2, 3, 7) and d <= 7) or \
                (v == 6 and d <= 6) or (v == 4 and d in (5, 6)):
            return "P"
    if soft:
        if total >= 20:
            return "S"
        if total == 19:
            return "D" if d == 6 and can_double else "S"
        if total == 18:
            if 2 <= d <= 6:
                return "D" if can_double else "S"
            return "S" if d in (7, 8) else "H"
        if total == 17:
            return "D" if 3 <= d <= 6 and can_double else "H"
        if total in (15, 16):
            return "D" if 4 <= d <= 6 and can_double else "H"
        return "D" if d in (5, 6) and can_double else "H"
    if total >= 17:
        return "S"
    if total >= 13:
        return "S" if d <= 6 else "H"
    if total == 12:
        return "S" if 4 <= d <= 6 else "H"
    if total == 11:
        return "D" if can_double else "H"
    if total == 10:
        return "D" if d <= 9 and can_double else "H"
    if total == 9:
        return "D" if 3 <= d <= 6 and can_double else "H"
    return "H"


ACTIONS = {"H": "Pedir", "S": "Plantarse", "D": "Doblar", "P": "Dividir"}


class Blackjack(BaseGame):
    gid = "blackjack"

    def setup(self):
        self.shoe = []
        self.running = 0
        self.dealer = []      # lista de CardObj
        self.hands = []       # dicts: objs, bet, done, doubled, result
        self.active = 0
        self.phase = "idle"   # idle, dealing, insurance, player, dealer, done
        self.hole_hidden = True
        self.rig = []         # cartas preparadas (as en la manga)
        self.insurance = 0.0
        self.peek_hole = False

    # ------------------------------------------------------------- baraja
    def shoe_pos(self):
        return (self.vis.right - 70, self.vis.y + 80)

    def draw_card(self, count=True):
        if len(self.shoe) < 52 * 3:   # penetración del 50%: contar cartas ayuda, pero poco
            self.shoe = [(r, s) for _ in range(N_DECKS) for s in range(4) for r in range(1, 14)]
            random.shuffle(self.shoe)
            self.running = 0
            self.app.log("Blackjack: se baraja el zapato de 6 mazos.", MUTED)
        c = self.shoe.pop()
        if count:
            self.running += hilo_value(c)
        return c

    def true_count(self):
        return self.running / max(0.5, len(self.shoe) / 52)

    @staticmethod
    def cards_of(objs):
        return [o.card for o in objs]

    # ------------------------------------------------------------ layout
    def dealer_slots(self, n):
        cx, y = self.vis.centerx, self.vis.y + 104
        sp = 76
        return [(cx - (n - 1) * sp / 2 + i * sp, y) for i in range(n)]

    def hand_slots(self, hi, n_cards):
        n = len(self.hands)
        slot = self.vis.w / n
        cx = self.vis.x + slot * (hi + 0.5)
        y = self.vis.y + 340
        sp = 30 if n_cards > 2 or n > 2 else 40
        return [(cx - (n_cards - 1) * sp / 2 + i * sp, y - i * 3) for i in range(n_cards)]

    def relayout(self):
        for objs, slots in [(self.dealer, self.dealer_slots(len(self.dealer)))] + \
                [(h["objs"], self.hand_slots(i, len(h["objs"]))) for i, h in enumerate(self.hands)]:
            for o, p in zip(objs, slots):
                if o.dst != p:
                    if o.done:
                        o.src = o.pos()
                        o.age = 0
                        o.dur = 0.25
                    o.dst = p

    def add_card(self, objs, face_up=True, count=True, delay=0.0):
        if self.rig and self.hands and objs is self.hands[0]["objs"]:
            c = self.rig.pop(0)
            if count:
                self.running += hilo_value(c)
        else:
            c = self.draw_card(count)
        o = CardObj(c, self.shoe_pos(), (0, 0), delay, face_up, CW, CH)
        objs.append(o)
        self.relayout()
        return o

    # ------------------------------------------------------------- juego
    def deal(self):
        if self.phase not in ("idle", "done"):
            return
        if not self.take_bet(self.bet):
            return
        self.phase = "dealing"
        self.hole_hidden = True
        self.insurance = 0.0
        self.peek_hole = False
        self.rig = [(1, random.randrange(4)), (13, random.randrange(4))] if self.use_cheat() else []
        self.rigged = bool(self.rig)
        self.dealer = []
        self.hands = [{"objs": [], "bet": self.bet, "done": False}]
        self.active = 0
        self.banner = None
        seq = [("p", True), ("d", True), ("p", True), ("d", False)]
        for i, (who, up) in enumerate(seq):
            self.later(i * 0.28, lambda who=who, up=up: self.add_card(self.hands[0]["objs"] if who == "p" else self.dealer,
                                                                      up, up))
        self.later(len(seq) * 0.28 + 0.25, self.after_deal)

    def after_deal(self):
        pc = self.cards_of(self.hands[0]["objs"])
        dc = self.cards_of(self.dealer)
        if self.rigged and is_blackjack(dc):
            self.dealer[1].card = (5, self.dealer[1].card[1])
            dc = self.cards_of(self.dealer)
        if dc[0][0] == 1 and self.state.lvl("bj_insurance") and not is_blackjack(pc) and \
                self.state.money >= self.hands[0]["bet"] / 2:
            self.phase = "insurance"
            return
        self.peek_dealer()

    def take_insurance(self, yes):
        if self.phase != "insurance":
            return
        if yes:
            amt = self.hands[0]["bet"] / 2
            if self.state.wager(self.gid, amt):
                self.insurance = amt
                self.audio.play("chip1")
        self.peek_dealer()

    def peek_dealer(self):
        pc = self.cards_of(self.hands[0]["objs"])
        dc = self.cards_of(self.dealer)
        if self.insurance > 0:
            won = is_blackjack(dc)
            self.state.settle(self.gid, self.insurance, self.insurance * 3 if won else 0.0, count_streak=False)
            self.show("¡El seguro paga 2:1!" if won else "El crupier no tiene blackjack: pierdes el seguro",
                      GREEN if won else MUTED)
        if (card_value(dc[0]) >= 10 and is_blackjack(dc)) or is_blackjack(pc):
            self.reveal_hole()
            self.later(0.45, self.resolve)
            return
        self.phase = "player"

    def reveal_hole(self):
        if self.hole_hidden and len(self.dealer) > 1:
            self.hole_hidden = False
            self.dealer[1].reveal(self.audio)
            self.running += hilo_value(self.dealer[1].card)

    def cur(self):
        return self.hands[self.active]

    def can_double(self):
        if self.phase != "player":
            return False
        h = self.cur()
        return len(h["objs"]) == 2 and self.state.money >= h["bet"] - 1e-9

    def can_split(self):
        if self.phase != "player":
            return False
        h = self.cur()
        cs = self.cards_of(h["objs"])
        return (len(cs) == 2 and card_value(cs[0]) == card_value(cs[1]) and len(self.hands) < 4
                and self.state.money >= h["bet"] - 1e-9)

    def hit(self):
        if self.phase != "player":
            return
        h = self.cur()
        self.add_card(h["objs"])
        if hand_value(self.cards_of(h["objs"]))[0] >= 21:
            h["done"] = True
            self.later(0.35, self.next_hand)

    def stand(self):
        if self.phase != "player":
            return
        self.cur()["done"] = True
        self.next_hand()

    def double(self):
        if not self.can_double() or not self.take_bet(self.cur()["bet"]):
            return
        h = self.cur()
        h["bet"] *= 2
        h["doubled"] = True
        self.add_card(h["objs"])
        h["done"] = True
        self.later(0.4, self.next_hand)

    def split(self):
        if not self.can_split():
            return
        h = self.cur()
        if not self.take_bet(h["bet"]):
            return
        second = h["objs"].pop()
        new = {"objs": [second], "bet": h["bet"], "done": False}
        self.hands.insert(self.active + 1, new)
        self.relayout()
        aces = h["objs"][0].card[0] == 1
        self.later(0.25, lambda: self.add_card(h["objs"]))
        self.later(0.5, lambda: self.add_card(new["objs"]))

        def after():
            if aces:
                h["done"] = new["done"] = True
            elif hand_value(self.cards_of(h["objs"]))[0] == 21:
                h["done"] = True
            self.next_hand()
        self.phase = "dealing"
        self.later(0.8, after)

    def next_hand(self):
        self.phase = "player"
        while self.active < len(self.hands) and self.hands[self.active]["done"]:
            self.active += 1
        if self.active < len(self.hands):
            if hand_value(self.cards_of(self.cur()["objs"]))[0] >= 21:
                self.cur()["done"] = True
                self.next_hand()
            return
        self.active = len(self.hands) - 1
        self.phase = "dealer"
        self.reveal_hole()
        all_bust = all(hand_value(self.cards_of(h["objs"]))[0] > 21 for h in self.hands)

        def step():
            total, _ = hand_value(self.cards_of(self.dealer))
            if not all_bust and total < 17:
                self.add_card(self.dealer)
                self.later(0.55, step)
            else:
                self.later(0.3, self.resolve)
        self.later(0.55, step)

    def resolve(self):
        self.reveal_hole()
        dc = self.cards_of(self.dealer)
        dt, _ = hand_value(dc)
        dbj = is_blackjack(dc)
        total_bet = sum(h["bet"] for h in self.hands)
        gross = 0.0
        single = len(self.hands) == 1
        for h in self.hands:
            pc = self.cards_of(h["objs"])
            pt, _ = hand_value(pc)
            pbj = single and is_blackjack(pc)
            if pbj and not dbj:
                gross += h["bet"] * 2.5
                h["result"] = ("BLACKJACK", GOLD)
                self.feat("bj_natural")
            elif pbj and dbj:
                gross += h["bet"]
                h["result"] = ("EMPATE", MUTED)
            elif dbj:
                h["result"] = ("PIERDES", RED)
            elif pt > 21:
                h["result"] = ("TE PASAS", RED)
            elif dt > 21 or pt > dt:
                gross += h["bet"] * 2
                h["result"] = ("GANAS", GREEN)
                if len(pc) >= 5:
                    self.feat("bj_five")
            elif pt == dt:
                gross += h["bet"]
                h["result"] = ("EMPATE", MUTED)
            else:
                h["result"] = ("PIERDES", RED)
        self.phase = "done"
        if len(self.hands) == 2 and all(h.get("result", ("",))[0] in ("GANAS", "BLACKJACK") for h in self.hands):
            self.feat("bj_split2")
        if gross > total_bet + 1e-9:
            if self.state.count("bj_streak", add=1) >= 8:
                self.feat("bj_streak8")
        elif gross < total_bet - 1e-9:
            self.state.count("bj_streak", 0)
        self.pay(total_bet, gross, pos=(self.vis.centerx, self.vis.y + 260))

    # ------------------------------------------------------------ update
    def update(self, dt):
        for o in self.dealer:
            o.update(dt, self.audio)
        for h in self.hands:
            for o in h["objs"]:
                o.update(dt, self.audio)

    # ------------------------------------------------------------ dibujo
    def draw(self, surf, rect):
        ui = self.ui
        v = self.vis
        felt(surf, v, (36, 92, 70))
        # decoración del tapete
        arc = pygame.Rect(v.centerx - 300, v.y - 160, 600, 520)
        pygame.draw.arc(surf, (200, 170, 90), arc, math.pi * 1.12, math.pi * 1.88, 2)
        pays = "3:2"
        gfx.text(surf, f"BLACKJACK PAGA {pays}", (v.centerx, v.y + 206), 18, "bl", (230, 200, 120), anchor="center")
        gfx.text(surf, "El crupier se planta en 17", (v.centerx, v.y + 232), 12, "r", (190, 225, 200),
                 anchor="center")
        # zapato
        sx, sy = self.shoe_pos()
        sr = pygame.Rect(sx - 46, sy - 60, 92, 120)
        gfx.rrect(surf, sr.move(4, 6), (0, 0, 0, 100), 10)
        for k in range(4):
            surf.blit(art.card_back(CW - 20, CH - 30), (sr.x + 4 + k * 2, sr.y + 6 - k * 2))
        gfx.rrect(surf, (sr.x - 6, sr.y + 56, sr.w + 12, 52), None, 10, border=(200, 160, 80), bw=2,
                  grad=((90, 54, 24, 255), (60, 34, 14, 255)))
        gfx.text(surf, f"{len(self.shoe)}", (sr.centerx, sr.y + 82), 12, "b", (240, 220, 190), anchor="center")
        # cartas
        for o in self.dealer:
            o.draw(surf)
        if self.peek_hole and self.hole_hidden and len(self.dealer) > 1:
            x, y = self.dealer[1].pos()
            img = art.card_sprite(self.dealer[1].card, 44, 62)
            surf.blit(img, img.get_rect(center=(int(x) + 30, int(y) - 34)))
            gfx.text(surf, "TAPADA", (int(x) + 30, int(y) - 74), 12, "b", GOLD, anchor="center")
        for hi, h in enumerate(self.hands):
            active = self.phase == "player" and hi == self.active
            for o in h["objs"]:
                o.hl = GOLD if active and len(self.hands) > 1 else None
                o.draw(surf)
        # totales
        if self.dealer:
            dc = self.cards_of(self.dealer)
            if self.hole_hidden:
                txt = str(card_value(dc[0]))
            else:
                val, soft = hand_value(dc)
                txt = f"{val}" + (" (blando)" if soft and val < 21 else "") + (" · SE PASA" if val > 21 else "")
            p = self.dealer_slots(len(self.dealer))[0]
            self.pill(surf, (p[0] - CW / 2 - 16, p[1]), txt, anchor="midright")
            gfx.text(surf, "CRUPIER", (v.x + 26, v.y + 22), 13, "b", (190, 230, 200))
        for hi, h in enumerate(self.hands):
            if not h["objs"]:
                continue
            cs = self.cards_of(h["objs"])
            val, soft = hand_value(cs)
            slots = self.hand_slots(hi, len(cs))
            cx = (slots[0][0] + slots[-1][0]) / 2
            txt = "BLACKJACK" if is_blackjack(cs) and len(self.hands) == 1 else \
                f"{val}" + (" blando" if soft and val < 21 else "") + (" · TE PASAS" if val > 21 else "")
            active = self.phase == "player" and hi == self.active
            self.pill(surf, (cx, slots[0][1] - CH / 2 - 22), txt, GOLD if active else None)
            chip = art.chip_with_text(44, h["bet"])
            surf.blit(chip, chip.get_rect(center=(cx, slots[0][1] + CH / 2 + 34)))
            if h.get("doubled"):
                surf.blit(chip, chip.get_rect(center=(cx + 10, slots[0][1] + CH / 2 + 28)))
            if h.get("result"):
                txt, col = h["result"]
                self.pill(surf, (cx, slots[0][1]), txt, col, big=True)
        if not self.hands:
            gfx.text(surf, "Haz tu apuesta y pulsa REPARTIR", (v.centerx, v.y + 340), 20, "b", (200, 230, 210),
                     anchor="center")
        if self.state.lvl("bj_counter"):
            tc = self.true_count()
            txt = f"Cuenta Hi-Lo {self.running:+d} · real {tc:+.1f}"
            if self.phase == "player" and self.hands:
                a = basic_strategy(self.cards_of(self.cur()["objs"]), self.dealer[0].card, len(self.cur()["objs"]) == 2,
                                   self.can_split())
                txt += f"   →   jugada óptima: {ACTIONS[a]}"
            col = GREEN if tc >= 2 else (RED if tc <= -2 else (220, 230, 220))
            gfx.rrect(surf, (v.x + 16, v.bottom - 44, gfx.text_w(txt, 13, "b") + 28, 30), (0, 0, 0, 120), 10)
            gfx.text(surf, txt, (v.x + 30, v.bottom - 29), 13, "b", col, anchor="midleft")
        pill = self.hint_pill(surf, v.x + 24, v.y + 52, 250, key="bj_peek", name="Ojo del crupier")
        if pill and self.hint_ready("bj_peek") and self.phase == "player" and self.hole_hidden and not self.peek_hole:
            if ui.button("peek", (pill.x, pill.bottom + 8, 150, 44), "Mirar tapada", "gold", size=12):
                self.use_hint("bj_peek")
                self.peek_hole = True
        self.cheat_pill(surf, v.right - 290, v.y + 160, 266)
        # controles
        c = self.controls_rect(rect)
        controls_bg(surf, c)
        self.bet_control(surf, c.x + 16, c.y + 12)
        keys = ui.keys if not ui.focus else []
        idle = self.phase in ("idle", "done")
        bx = c.x + 372
        bw = 86
        if self.phase == "insurance":
            amt = self.hands[0]["bet"] / 2
            gfx.text(surf, "El crupier enseña un As. ¿Seguro?", (bx, c.y + 14), 14, "b", GOLD)
            if ui.button("ins_y", (bx, c.y + 44, 200, 50), f"Asegurar {fmt_money(amt)}", "gold", size=12):
                self.take_insurance(True)
            if ui.button("ins_n", (bx + 210, c.y + 44, 150, 50), "No, gracias", "dark", size=12):
                self.take_insurance(False)
            return
        if ui.button("deal", (bx, c.y + 18, 114, 64), "REPARTIR", "green", enabled=idle, size=15, sound=None) or \
                (idle and pygame.K_SPACE in keys):
            self.deal()
        bx += 120
        p = self.phase == "player"
        if ui.button("hit", (bx, c.y + 18, bw, 64), "Pedir", "blue", enabled=p, size=15, sub="H") or \
                (p and pygame.K_h in keys):
            self.hit()
        if ui.button("stand", (bx + bw + 6, c.y + 18, bw, 64), "Plantar", "red", enabled=p, size=13, sub="S") or \
                (p and pygame.K_s in keys):
            self.stand()
        if ui.button("double", (bx + 2 * (bw + 6), c.y + 18, bw, 64), "Doblar", "gold", enabled=self.can_double(),
                     size=15, sub="D", sound=None) or (self.can_double() and pygame.K_d in keys):
            self.double()
        if ui.button("split", (bx + 3 * (bw + 6), c.y + 18, bw, 64), "Dividir", "primary", enabled=self.can_split(),
                     size=15, sub="P", sound=None) or (self.can_split() and pygame.K_p in keys):
            self.split()

    def pill(self, surf, pos, text, col=None, anchor="center", big=False):
        size = 18 if big else 14
        w = gfx.text_w(text, size, "bl") + 24
        h = size + 14
        r = pygame.Rect(0, 0, w, h)
        setattr(r, anchor, (int(pos[0]), int(pos[1])))
        bg = (14, 14, 24, 220) if not big else (*gfx.mul_col(col or (60, 60, 60), 0.45), 240)
        gfx.rrect(surf, r, bg, h // 2, border=col or (90, 120, 100), bw=2 if (col or big) else 1)
        gfx.text(surf, text, r.center, size, "bl", col if (col and not big) else TEXT, anchor="center")
