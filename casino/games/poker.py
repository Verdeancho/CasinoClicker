"""Póker contra jugadores virtuales (límite fijo) y Caribbean Stud contra la banca.

Modalidades: Texas Hold'em, Omaha, Seven-Card Stud, Five-Card Draw y Caribbean Stud.
La casa se lleva un 5% de cada bote (rake): ganar exige jugar mejor que los bots."""
import math
import random

import pygame

from .base import BaseGame
from .common import felt, controls_bg
from . import poker_engine as PE
from .. import gfx, art
from ..icons import Pen, C
from ..fmt import fmt_money, fmt_num
from ..gfx import TEXT, MUTED, DIM, GOLD, GOLD_HI, GREEN, RED, ORANGE, BLUE, PURPLE, PANEL_LO, LINE

RAKE = 0.05
BOTS = [("Paco", "cauto", (90, 160, 255)), ("Lola", "agresivo", (255, 110, 150)),
        ("Manolo", "pasivo", (120, 210, 140)), ("Rosi", "loco", (255, 190, 70))]
SIMS = {"holdem": 90, "omaha": 36, "stud7": 70, "draw5": 110}
CARIB_PAY = {0: 1, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 7, 7: 20, 8: 50}

_avatars = {}


def avatar(name, col, size=60):
    key = (name, col, size)
    if key not in _avatars:
        p = Pen()
        hair = {"Paco": (70, 50, 40), "Lola": (200, 60, 90), "Manolo": (180, 180, 180), "Rosi": (240, 170, 60),
                "Tú": (60, 40, 30), "Banca": (30, 30, 40)}.get(name, (80, 60, 40))
        p.circle((C, C + 20), 110, col)
        p.circle((C, C - 10), 66, hair)
        p.circle((C, C + 6), 58, (255, 214, 180))
        p.rect((C - 60, C - 66, 120, 40), hair, 18)
        for dx in (-22, 22):
            p.circle((C + dx, C + 4), 8, (40, 40, 50))
        p.arc((C - 20, C + 18, 40, 24), math.pi * 1.1, math.pi * 1.9, (150, 60, 60), 5)
        if name == "Banca":
            p.rect((C - 70, C - 92, 140, 30), (30, 30, 40), 8)
            p.rect((C - 46, C - 130, 92, 46), (30, 30, 40), 8)
        _avatars[key] = gfx.pixelize(p.s, (size, size), 2)
    return _avatars[key]


class Poker(BaseGame):
    gid = "poker"

    def setup(self):
        self.dealer = 0
        self.seats = []
        self.phase = "idle"
        self.board = []
        self.pot = 0.0
        self.unit = 0.0
        self.msg = ""
        self.tell_seat = None
        self.turn = 0
        self.cur_bet = 0.0
        self.raises = 0
        self.street = 0
        self.on_variant()

    def reset_table(self):
        self.seats = [{"name": "Tú", "style": None, "col": (240, 240, 240)}] + \
                     [{"name": n, "style": s, "col": c} for n, s, c in BOTS]
        for s in self.seats:
            s.update(cards=[], folded=False, in_round=0.0, total=0.0, acted=False, last="", tell=None, show=False,
                     discard=set(), hand=None)
        self.board = []
        self.pot = 0.0
        self.phase = "idle"

    def on_variant(self):
        self.reset_table()
        if self.variant == "caribbean":
            self.seats = []

    def can_change_variant(self):
        return self.phase in ("idle", "done")

    # ----------------------------------------------------------------- reglas
    def max_commit(self):
        u = self.bet
        return {"holdem": 25 * u, "omaha": 25 * u, "stud7": 33 * u, "draw5": 13 * u, "caribbean": 3 * u}[self.variant]

    def round_size(self):
        u = self.unit
        if self.variant in ("holdem", "omaha"):
            return u if self.street <= 1 else 2 * u
        if self.variant == "stud7":
            return u if self.street <= 1 else 2 * u
        return u if self.street == 0 else 2 * u

    def active(self):
        return [i for i, s in enumerate(self.seats) if not s["folded"]]

    def next_seat(self, i):
        for k in range(1, 6):
            j = (i + k) % 5
            if not self.seats[j]["folded"]:
                return j
        return i

    def deal(self):
        return self.deck.pop()

    def contribute(self, i, amount):
        s = self.seats[i]
        if amount <= 0:
            return True
        if i == 0:
            if not self.state.wager(self.gid, amount):
                return False
            self.audio.play(f"chip{random.randint(0, 2)}", 0.6)
        s["in_round"] += amount
        s["total"] += amount
        self.pot += amount
        return True

    # ------------------------------------------------------------------ manos
    def start_hand(self):
        if self.phase not in ("idle", "done"):
            return
        if self.bet > self.state.max_bet() + 1e-9:
            self.show("La apuesta supera tu límite", RED)
            return
        if self.state.money < self.max_commit():
            self.show(f"Necesitas {fmt_money(self.max_commit())} para sentarte con esta apuesta", RED)
            return
        if self.variant == "caribbean":
            self.start_caribbean()
            return
        self.reset_table()
        self.unit = self.bet
        self.deck = PE.full_deck()
        random.shuffle(self.deck)
        self.dealer = (self.dealer + 1) % 5
        self.street = 0
        self.tell_seat = None
        self.banner = None
        v = self.variant
        if v in ("holdem", "omaha"):
            n = 2 if v == "holdem" else 4
            for _ in range(n):
                for i in range(5):
                    self.seats[i]["cards"].append((self.deal(), i == 0))
            sb, bb = (self.dealer + 1) % 5, (self.dealer + 2) % 5
            self.contribute(sb, self.unit / 2)
            self.contribute(bb, self.unit)
            self.seats[sb]["last"] = "ciega peq."
            self.seats[bb]["last"] = "ciega gr."
            self.begin_round((self.dealer + 3) % 5, keep=True)
        elif v == "stud7":
            for i in range(5):
                self.contribute(i, self.unit / 5)
                self.seats[i]["cards"] += [(self.deal(), i == 0), (self.deal(), i == 0), (self.deal(), True)]
                self.seats[i]["up"] = [False, False, True]
            self.begin_round(self.stud_first())
        else:  # draw5
            for i in range(5):
                self.contribute(i, self.unit / 4)
                self.seats[i]["cards"] = [(self.deal(), i == 0) for _ in range(5)]
            self.begin_round((self.dealer + 1) % 5)
        self.audio.play("card0")
        self.phase = "betting"

    def stud_first(self):
        """En Stud empieza a hablar quien enseña las cartas visibles más altas."""
        best, who = None, 0
        for i in self.active():
            st = self.seats[i]
            ups = [c for k, (c, _vis) in enumerate(st["cards"]) if st["up"][k]]
            val = tuple(sorted((PE.hi(r) for r, _ in ups), reverse=True))
            if best is None or val > best:
                best, who = val, i
        return who

    def begin_round(self, first, keep=False):
        for s in self.seats:
            if not keep:
                s["in_round"] = 0.0
            s["acted"] = False
        self.cur_bet = max(s["in_round"] for s in self.seats)
        self.raises = 1 if self.cur_bet > 0 else 0
        self.turn = first if not self.seats[first]["folded"] else self.next_seat(first)
        self.schedule_turn()

    def schedule_turn(self):
        if len(self.active()) == 1:
            self.later(0.4, self.win_by_fold)
            return
        if self.round_done():
            self.later(0.45, self.end_round)
            return
        s = self.seats[self.turn]
        if s["folded"]:
            self.turn = self.next_seat(self.turn)
            self.schedule_turn()
            return
        if self.turn == 0:
            self.phase = "betting"
            return
        self.phase = "bots"
        self.later(random.uniform(0.45, 0.9), self.bot_act)

    def round_done(self):
        act = self.active()
        return all(self.seats[i]["acted"] and abs(self.seats[i]["in_round"] - self.cur_bet) < 1e-9 for i in act)

    def act(self, i, action):
        s = self.seats[i]
        to_call = self.cur_bet - s["in_round"]
        size = self.round_size()
        if action == "fold":
            s["folded"] = True
            s["last"] = "se retira"
            self.audio.play("card1", 0.5)
        elif action == "call" or (action == "raise" and self.raises >= 4):
            if not self.contribute(i, to_call):
                s["folded"] = True
                s["last"] = "se retira"
            else:
                s["last"] = "pasa" if to_call <= 0 else f"iguala {fmt_money(to_call)}"
        else:
            amt = to_call + size
            self.contribute(i, amt)
            self.cur_bet += size
            self.raises += 1
            s["last"] = "apuesta" if to_call <= 0 and self.raises == 1 else "sube"
            for j in self.active():
                if j != i:
                    self.seats[j]["acted"] = False
        s["acted"] = True
        self.turn = self.next_seat(i)
        self.schedule_turn()

    def bot_act(self):
        i = self.turn
        s = self.seats[i]
        if s["folded"] or i == 0:
            return
        to_call = self.cur_bet - s["in_round"]
        act = self.active()
        n_opp = len(act) - 1
        hole = [c for c, _ in s["cards"]]
        known = []
        if self.variant == "stud7":
            for j in act:
                if j != i:
                    known.append([c for k, (c, vis) in enumerate(self.seats[j]["cards"]) if self.seats[j]["up"][k]])
        eq = PE.equity(self.variant, hole, self.board, known, n_opp, SIMS[self.variant])
        decision = PE.bot_decide(s["style"], eq, to_call, self.pot, n_opp, self.raises < 4)
        self.act(i, decision)

    def human(self, action):
        if self.phase != "betting" or self.turn != 0:
            return
        self.act(0, action)

    def end_round(self):
        v = self.variant
        self.street += 1
        for s in self.seats:
            s["last"] = "" if not s["folded"] else s["last"]
        if v in ("holdem", "omaha"):
            if self.street > 3:
                self.showdown()
                return
            n = 3 if self.street == 1 else 1
            for _ in range(n):
                self.board.append(self.deal())
            self.audio.play("card2", 0.8)
            self.begin_round(self.next_seat(self.dealer))
        elif v == "stud7":
            if self.street > 4:
                self.showdown()
                return
            up = self.street < 4
            for i in self.active():
                self.seats[i]["cards"].append((self.deal(), up or i == 0))
                self.seats[i]["up"].append(up)
            self.audio.play("card2", 0.8)
            self.begin_round(self.stud_first())
        else:
            if self.street == 1:
                for i in self.active():
                    if i != 0:
                        disc = PE.draw5_discards([c for c, _ in self.seats[i]["cards"]])
                        for k in disc:
                            self.seats[i]["cards"][k] = (self.deal(), False)
                        self.seats[i]["last"] = f"cambia {len(disc)}" if disc else "se planta"
                self.seats[0]["discard"] = set()
                if self.seats[0]["folded"]:
                    self.begin_round(self.next_seat(self.dealer))
                else:
                    self.phase = "draw"
            else:
                self.showdown()

    def human_draw(self):
        if self.phase != "draw":
            return
        s = self.seats[0]
        for k in sorted(s["discard"]):
            s["cards"][k] = (self.deal(), True)
        s["last"] = f"cambia {len(s['discard'])}" if s["discard"] else "se planta"
        s["discard"] = set()
        self.audio.play("card1")
        self.begin_round(self.next_seat(self.dealer))

    def value(self, i):
        cards = [c for c, _ in self.seats[i]["cards"]]
        if self.variant == "holdem":
            return PE.evaluate(cards + self.board)
        if self.variant == "omaha":
            return PE.evaluate_omaha(cards, self.board)
        return PE.evaluate(cards)

    def showdown(self):
        act = self.active()
        vals = {i: self.value(i) for i in act}
        best = max(vals.values())
        winners = [i for i in act if vals[i] == best]
        for i in act:
            self.seats[i]["show"] = True
            self.seats[i]["hand"] = PE.hand_name(vals[i])
        self.finish_hand(winners, showdown=True)

    def win_by_fold(self):
        winners = self.active()
        self.finish_hand(winners, showdown=False)

    def finish_hand(self, winners, showdown):
        self.phase = "done"
        prize = self.pot * (1 - RAKE)
        me = self.seats[0]
        gross = prize / len(winners) if 0 in winners else 0.0
        names = ", ".join(self.seats[i]["name"] for i in winners)
        hand = self.seats[winners[0]].get("hand")
        label = f"Gana {names}" + (f" con {hand}" if hand and showdown else "")
        if 0 in winners:
            self.feat("poker_win" if showdown else "poker_bluff")
        if me["total"] > 0:
            self.pay(me["total"], gross, label=label, pos=(self.vis.centerx, self.vis.y + 200))
        else:
            self.show(label, MUTED)

    # ------------------------------------------------------------- caribbean
    def start_caribbean(self):
        if not self.take_bet(self.bet):
            return
        self.reset_table()
        self.seats = [{"name": "Tú", "style": None, "col": (240, 240, 240)},
                      {"name": "Banca", "style": None, "col": (60, 60, 70)}]
        for s in self.seats:
            s.update(cards=[], folded=False, in_round=0.0, total=0.0, acted=False, last="", tell=None, show=False,
                     discard=set(), hand=None)
        self.deck = PE.full_deck()
        random.shuffle(self.deck)
        self.ante = self.bet
        self.seats[0]["cards"] = [(self.deal(), True) for _ in range(5)]
        self.seats[1]["cards"] = [(self.deal(), k == 0) for k in range(5)]
        self.seats[0]["hand"] = PE.hand_name(PE.evaluate([c for c, _ in self.seats[0]["cards"]]))
        self.phase = "carib"
        self.banner = None
        self.audio.play("card0")

    def carib_fold(self):
        if self.phase != "carib":
            return
        self.phase = "done"
        self.seats[1]["show"] = True
        self.pay(self.ante, 0, label="Te retiras")

    def carib_raise(self):
        if self.phase != "carib":
            return
        raise_amt = self.ante * 2
        if not self.state.wager(self.gid, raise_amt):
            self.show("No tienes dinero para subir", RED)
            return
        self.phase = "done"
        self.seats[1]["show"] = True
        me = PE.evaluate([c for c, _ in self.seats[0]["cards"]])
        dv = PE.evaluate([c for c, _ in self.seats[1]["cards"]])
        self.seats[1]["hand"] = PE.hand_name(dv)
        ranks = [PE.hi(r) for r, _ in (c for c, _ in self.seats[1]["cards"])]
        qualifies = dv[0] >= 1 or (14 in ranks and 13 in ranks)
        stake = self.ante + raise_amt
        if not qualifies:
            self.pay(stake, self.ante * 2 + raise_amt, label="La banca no califica: cobras el ante")
            return
        if me > dv:
            mult = 100 if (me[0] == 8 and me[1] == 14) else CARIB_PAY[me[0]]
            self.pay(stake, self.ante * 2 + raise_amt * (1 + mult), label=f"¡Ganas con {PE.hand_name(me)}!")
        elif me == dv:
            self.pay(stake, stake, label="Empate")
        else:
            self.pay(stake, 0, label=f"Gana la banca con {PE.hand_name(dv)}")

    # ------------------------------------------------------------------ dibujo
    def seat_layout(self, i):
        """Devuelve (centro del grupo de cartas, centro del avatar o None, lado de la etiqueta)."""
        v = self.vis
        if self.variant == "caribbean":
            return [((v.centerx, v.bottom - 96), None), ((v.centerx, v.y + 92), (v.centerx - 230, v.y + 86))][i]
        return [((v.centerx, v.bottom - 88), None),
                ((v.x + 200, v.centery + 26), (v.x + 64, v.centery + 10)),
                ((v.x + 330, v.y + 78), (v.x + 190, v.y + 66)),
                ((v.right - 230, v.y + 78), (v.right - 370, v.y + 66)),
                ((v.right - 210, v.centery + 26), (v.right - 64, v.centery + 10))][i]

    def seat_pos(self, i):
        return self.seat_layout(i)[0]

    def draw_seat(self, surf, i):
        s = self.seats[i]
        (x, y), av_pos = self.seat_layout(i)
        me = i == 0
        cw, chh = (80, 112) if me else (44, 62)
        if self.variant == "caribbean" and i == 1:
            cw, chh = (64, 90)
        cards = s["cards"]
        n = len(cards)
        if me:
            gap = cw + 8 if n <= 5 else int(cw * 0.7)
        else:
            gap = cw + 4 if n <= 2 else max(18, int((150 if n > 4 else 120) / max(1, n - 1)))
        x0 = x - (gap * (n - 1)) / 2
        cy = y - (14 if me else 0)
        for k, (card, vis) in enumerate(cards):
            show = vis or s["show"] or me
            if self.variant == "stud7" and not me:
                show = self.seats[i]["up"][k] or s["show"]
            img = art.card_sprite(card, cw, chh) if show else art.card_back(cw, chh)
            yy = cy
            if me and k in s.get("discard", set()):
                yy -= 18
            r = img.get_rect(center=(int(x0 + k * gap), int(yy)))
            if s["folded"]:
                img = img.copy()
                img.set_alpha(90)
            surf.blit(img, r)
            if me and self.phase == "draw" and not s["folded"]:
                wid = ("disc", k)
                if self.ui.hover(r):
                    self.ui.hot_any = True
                    if self.ui.pressed:
                        self.ui.active = wid
                    if self.ui.released and self.ui.active == wid:
                        d = s["discard"]
                        has_ace = any(c[0] == 1 for kk, (c, _) in enumerate(cards) if kk not in d and kk != k)
                        limit = 4 if has_ace else 3
                        if k in d:
                            d.discard(k)
                        elif len(d) < limit:
                            d.add(k)
                        self.audio.play("card1", 0.5)
                if k in s["discard"]:
                    gfx.text(surf, "CAMBIAR", (r.centerx, r.y - 12), 12, "b", ORANGE, anchor="center")
        if av_pos:
            ax, ay = av_pos
            av = avatar(s["name"], s["col"], 52)
            surf.blit(av, av.get_rect(center=(int(ax), int(ay))))
            turn = self.turn == i and self.phase in ("bots", "betting") and not s["folded"]
            nr = pygame.Rect(0, 0, 100, 24)
            nr.midtop = (int(ax), int(ay + 28))
            gfx.rrect(surf, nr, (*((253, 162, 0) if turn else PANEL_LO), 240), 6, border=LINE, bw=2)
            gfx.text(surf, s["name"], nr.center, 12, "b", TEXT, anchor="center")
            if s["last"]:
                gfx.text(surf, s["last"], (ax, nr.bottom + 10), 12, "r", GOLD_HI if not s["folded"] else DIM,
                         anchor="center")
            if s.get("tell"):
                tr = pygame.Rect(0, 0, 116, 28)
                tr.midbottom = (int(ax), int(ay - 30))
                gfx.box(surf, tr, (*((60, 140, 90) if s["tell"] == "fuerte" else (150, 60, 60)), 245), 8, ow=4,
                        shadow_off=3)
                gfx.text(surf, f"parece {s['tell']}", tr.center, 10, "b", TEXT, anchor="center")
        if s["show"] and s.get("hand"):
            hr = pygame.Rect(0, 0, 150 if not me else 180, 24)
            if me:
                hr.midleft = (int(x0 + gap * (n - 1) + cw / 2 + 14), int(cy))
            else:
                hr.midtop = (int(x), int(cy + chh / 2 + 4))
            gfx.rrect(surf, hr, (*PANEL_LO, 235), 6, border=LINE, bw=2)
            gfx.text(surf, s["hand"], hr.center, 12 if me else 10, "b", GOLD_HI, anchor="center", max_w=hr.w - 6)
        if s["in_round"] > 0 and self.variant != "caribbean":
            chip = art.chip_with_text(32, s["in_round"])
            px = x + (self.vis.centerx - x) * 0.35
            py = y + (self.vis.centery + 10 - y) * 0.5
            surf.blit(chip, chip.get_rect(center=(int(px), int(py))))

    def draw(self, surf, rect):
        ui = self.ui
        v = self.vis
        felt(surf, v, (34, 100, 72))
        pygame.draw.ellipse(surf, (28, 84, 60), v.inflate(-60, -60), 6)
        names = {g.id: g.name for g in self.gdef.variants}
        gfx.text(surf, names.get(self.variant, ""), (v.x + 26, v.y + 22), 14, "bl", (220, 240, 225))
        if self.variant != "caribbean":
            gfx.text(surf, f"Bote: {fmt_money(self.pot)}", (v.centerx, v.centery - 66), 16, "bl", GOLD_HI,
                     anchor="center")
            gfx.text(surf, f"límite fijo · comisión {int(RAKE * 100)}%", (v.right - 26, v.y + 22), 12, "r",
                     (190, 220, 200), anchor="topright")
            for k in range(5):
                x = v.centerx - 2 * 70 + k * 70
                r = pygame.Rect(0, 0, 64, 90)
                r.center = (x, v.centery + 10)
                if k < len(self.board):
                    surf.blit(art.card_sprite(self.board[k], 64, 90), r)
                elif self.variant in ("holdem", "omaha"):
                    gfx.rrect(surf, r, (24, 76, 54, 255), 6, border=(60, 130, 96), bw=2)
        else:
            rules = gfx.wrap("Pon el ante y recibe 5 cartas. Sube 2x o retírate. La banca califica con A-K o "
                             "mejor.", 12, "r", 400)
            for k, ln in enumerate(rules):
                gfx.text(surf, ln, (v.centerx, v.y + 166 + k * 22), 12, "r", (200, 230, 210), anchor="midtop")
            for k, (h, m) in enumerate([("Pareja", 1), ("Doble pareja", 2), ("Trío", 3), ("Escalera", 4),
                                        ("Color", 5), ("Full", 7), ("Póker", 20), ("Esc. color", 50),
                                        ("Esc. real", 100)]):
                gfx.text(surf, f"{h} {m}:1", (v.right - 26, v.y + 26 + k * 20), 12, "r", (220, 240, 225),
                         anchor="topright")
        for i in range(len(self.seats)):
            self.draw_seat(surf, i)
        pill = self.hint_pill(surf, v.x + 20, v.bottom - 50, 250) if self.variant != "caribbean" else None
        if pill and self.hint_ready() and self.phase in ("betting", "bots") and self.tell_seat is None:
            if ui.button("hint", (pill.x, pill.y - 52, 150, 44), "Leer rival", "gold", size=12):
                self.read_rival()
        # controles
        c = self.controls_rect(rect)
        controls_bg(surf, c)
        idle = self.phase in ("idle", "done")
        if idle:
            self.bet_control(surf, c.x + 16, c.y + 10, "ANTE" if self.variant == "caribbean" else "APUESTA (ciega)")
            gfx.text(surf, f"necesitas {fmt_money(self.max_commit())}", (c.x + 372, c.y + 40), 12, "r", MUTED)
            keys = ui.keys if not ui.focus else []
            if ui.button("deal", (c.right - 200, c.y + 18, 184, 70), "REPARTIR", "green", size=16, sound=None) or \
                    pygame.K_SPACE in keys:
                self.start_hand()
            return
        if self.phase == "carib":
            gfx.text(surf, f"Tienes: {self.seats[0]['hand']}", (c.x + 20, c.y + 44), 16, "b", GOLD_HI)
            if ui.button("cfold", (c.right - 420, c.y + 18, 190, 70), "RETIRARSE", "dark", size=14,
                         sub=f"pierdes {fmt_money(self.ante)}"):
                self.carib_fold()
            if ui.button("craise", (c.right - 220, c.y + 18, 204, 70), "SUBIR", "gold", size=14,
                         sub=f"+{fmt_money(self.ante * 2)}", sound=None):
                self.carib_raise()
            return
        if self.phase == "draw":
            gfx.text(surf, "Pulsa las cartas que quieras cambiar", (c.x + 20, c.y + 28), 14, "b", TEXT)
            gfx.text(surf, "Hasta 3, o 4 si te quedas un As", (c.x + 20, c.y + 60), 12, "r", MUTED)
            if ui.button("draw", (c.right - 220, c.y + 18, 204, 70), "CAMBIAR", "gold", size=16):
                self.human_draw()
            return
        me = self.seats[0]
        my_turn = self.phase == "betting" and self.turn == 0 and not me["folded"]
        to_call = self.cur_bet - me["in_round"] if self.phase in ("betting", "bots") else 0
        size = self.round_size() if self.phase in ("betting", "bots") else 0
        gfx.text(surf, f"Puesto: {fmt_money(me['total'])}", (c.x + 20, c.y + 22), 12, "r", MUTED, max_w=230)
        if me["folded"]:
            gfx.text(surf, "Te has retirado...", (c.x + 20, c.y + 52), 12, "b", DIM)
            return
        if not my_turn:
            gfx.text(surf, "Turno de los rivales", (c.x + 20, c.y + 52), 12, "b", DIM)
        bx = c.right - 600
        if ui.button("fold", (bx, c.y + 18, 180, 70), "RETIRARSE", "dark", enabled=my_turn, size=13):
            self.human("fold")
        if ui.button("call", (bx + 192, c.y + 18, 196, 70), "PASAR" if to_call <= 0 else "IGUALAR", "blue",
                     enabled=my_turn, size=13, sub=fmt_money(to_call) if to_call > 0 else None, sound=None):
            self.human("call")
        can_raise = self.raises < 4 if hasattr(self, "raises") else False
        if ui.button("raise", (bx + 400, c.y + 18, 196, 70), "APOSTAR" if self.cur_bet - me["in_round"] <= 0 and
                     self.raises == 0 else "SUBIR", "gold", enabled=my_turn and can_raise, size=13,
                     sub=fmt_money(to_call + size), sound=None):
            self.human("raise")

    def read_rival(self):
        bots = [i for i in self.active() if i != 0]
        if not bots:
            return
        self.use_hint()
        i = random.choice(bots)
        s = self.seats[i]
        n_opp = len(self.active()) - 1
        hole = [c for c, _ in s["cards"]]
        eq = PE.equity(self.variant, hole, self.board, [], n_opp, 120)
        strong = eq > 1.2 / (n_opp + 1)
        said = strong if random.random() < self.reliable(0.75) else not strong
        s["tell"] = "fuerte" if said else "débil"
        self.tell_seat = i
