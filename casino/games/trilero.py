"""El Trilero: sigue la bolita. Cada ronda más vasos, más rápido y más trucos bajo el pañuelo.

Los cambios a la vista se pueden seguir. El pañuelo tapa SIEMPRE dos vasos vecinos, y debajo se cruzan o no
(50%): quien sigue bien la bola sabe que está en uno de esos dos y tiene que seguir a ambos "por si acaso".
Con la mancha (ventaja) se sabe siempre dónde está. El multiplicador de cada ronda se calcula para que, siguiendo
la bola a la perfección, el retorno sea del 97%.
"""
import math
import random

import pygame

from .base import BaseGame
from .common import felt, controls_bg
from .. import gfx
from ..icons import Pen, _cup
from ..fmt import fmt_money, fmt_num
from ..gfx import TEXT, MUTED, GOLD_HI, GREEN, PANEL_LO, LINE

EDGE = 0.97
LEVELS = [  # vasos, cambios visibles, pañuelos, segundos por cambio
    (3, 6, 1, 0.55), (3, 9, 2, 0.42), (4, 10, 3, 0.38), (5, 12, 3, 0.34), (6, 14, 4, 0.30),
    (7, 15, 5, 0.27), (8, 16, 6, 0.24), (9, 18, 7, 0.21), (10, 20, 8, 0.18),
]


def p_track(n, cloths, samples=6000, seed=12345):
    """Probabilidad de acertar siguiendo la bola perfectamente: cada pañuelo tapa dos vasos al azar y los
    cruza o no al 50%, así que la creencia sobre esos dos se promedia. Se elige el vaso más probable."""
    rng = random.Random(seed + n * 31 + cloths)
    total = 0.0
    for _ in range(samples):
        b = [0.0] * n
        b[0] = 1.0
        for _ in range(cloths):
            i, j = rng.sample(range(n), 2)
            m = (b[i] + b[j]) / 2
            b[i] = b[j] = m
        total += max(b)
    return total / samples


MULTS = [round(EDGE / p_track(n, c), 2) for (n, s, c, d) in LEVELS]

_sprites = {}


def cup_sprite(w, h):
    key = (w, h)
    if key not in _sprites:
        p = Pen()
        _cup(p, 120, 220, 210, 200, (214, 64, 52))
        _sprites[key] = gfx.pixelize(p.s, (w, h + 30), 2)
    return _sprites[key]


class Trilero(BaseGame):
    gid = "trilero"

    def setup(self):
        self.level = 0
        self.bank = 0.0
        self.pbet = 0.0
        self.phase = "idle"
        self.timer = 0.0
        self.cups = []        # cada vaso: {"slot": int, "lift": 0..1}
        self.ball = 0         # índice del vaso con la bola
        self.stain = None
        self.queue = []
        self.anim = None
        self.choice = None
        self.won = None
        self.cloth = 0.0
        self.cloth_slots = (0, 1)
        self.xray = False
        self.mode = None      # "monty" o "peek" mientras se elige un vaso para la ventaja
        self.marked = None    # vaso señalado en el truco del trilero
        self.shown_empty = None
        self.peek_cup = None

    # --------------------------------------------------------------- geometría
    def n(self):
        return LEVELS[self.level][0]

    def slot_x(self, slot):
        n = self.n()
        v = self.vis
        span = min(v.w - 160, n * 120)
        return v.centerx - span / 2 + (slot + 0.5) * span / n

    def cup_size(self):
        n = self.n()
        w = int(min(110, (min(self.vis.w - 160, n * 120) / n) * 0.82))
        return w, int(w * 1.15)

    def base_y(self):
        return self.vis.y + self.vis.h * 0.64

    def cup_pos(self, i):
        cup = self.cups[i]
        x = self.slot_x(cup["slot"])
        y = self.base_y()
        a = self.anim
        if a and i in a["cups"]:
            k = gfx.ease_in_out(min(1.0, a["t"] / a["dur"]))
            j = a["cups"].index(i)
            s0, s1 = a["from"][j], a["to"][j]
            x = self.slot_x(s0) + (self.slot_x(s1) - self.slot_x(s0)) * k
            y += math.sin(k * math.pi) * 38 * (1 if j == 0 else -1)
        return x, y

    def cup_at(self, slot):
        return next(i for i, c in enumerate(self.cups) if c["slot"] == slot)

    # ----------------------------------------------------------------- flujo
    def speed_mult(self):
        return 1 + 0.15 * self.state.lvl("trilero_slow")

    def start_round(self):
        n, vis_sw, cloths, dur = LEVELS[self.level]
        self.cups = [{"slot": i, "lift": 1.0} for i in range(n)]
        self.ball = random.randrange(n)
        self.stain = None
        if self.hint_ready():
            self.use_hint()
            self.stain = self.ball
        self.xray = self.use_cheat() or self.xray
        dur *= self.speed_mult()
        seq = [("swap", dur)] * vis_sw
        for _ in range(cloths):
            seq.insert(random.randint(1, len(seq)), ("cloth", 0.0))
        self.queue = seq
        self.choice = None
        self.won = None
        self.mode = None
        self.marked = None
        self.shown_empty = None
        self.peek_cup = None
        self.phase = "show"
        self.timer = 0.0
        self.audio.play("cup", 0.8)

    def bet_and_start(self):
        if self.phase != "idle":
            return
        if not self.take_bet(self.bet):
            return
        self.pbet = self.bet
        self.bank = self.bet
        self.level = 0
        self.banner = None
        self.xray = False
        self.start_round()

    def next_action(self):
        if not self.queue:
            self.phase = "choose"
            self.show("¿Dónde está la bolita?", TEXT)
            return
        kind, dur = self.queue.pop(0)
        n = self.n()
        if kind == "swap":
            a, b = random.sample(range(n), 2)
            ia, ib = self.cup_at(a), self.cup_at(b)
            self.anim = {"cups": [ia, ib], "from": [a, b], "to": [b, a], "t": 0.0, "dur": dur}
            self.audio.play("slide", 0.7, pan=(self.slot_x(a) - self.vis.centerx) / 500, throttle=0.02)
            self.phase = "swap"
        else:
            s = random.randrange(n - 1)
            self.cloth_slots = (s, s + 1)
            self.phase = "cloth_in"
            self.timer = 0.0
            self.audio.play("whoosh", 0.8)

    def cloth_swap(self):
        if random.random() < 0.5:
            a, b = self.cloth_slots
            ia, ib = self.cup_at(a), self.cup_at(b)
            self.cups[ia]["slot"], self.cups[ib]["slot"] = b, a

    def pick(self, i):
        if self.phase != "choose":
            return
        if self.mode == "monty":
            self.marked = i
            empties = [k for k in range(len(self.cups)) if k != i and k != self.ball]
            self.shown_empty = random.choice(empties)
            self.mode = None
            self.audio.play("cup")
            self.show("El trilero levanta un vaso vacío. ¿Cambias o te quedas?", GOLD_HI)
            return
        if self.mode == "peek":
            self.peek_cup = i
            self.mode = None
            self.audio.play("cup")
            return
        self.choice = i
        self.phase = "reveal"
        self.timer = 0.0
        self.banner = None
        self.audio.play("cup")

    def resolve(self):
        won = self.choice == self.ball
        self.won = won
        if won:
            self.bank *= MULTS[self.level]
            self.audio.play("win2" if self.level >= 3 else "win1")
            x, y = self.cup_pos(self.choice)
            self.fx.sparks(x, y, 24, (255, 230, 140), 1.2)
            if self.level >= 4:
                self.feat("trilero_5")
            if self.level == len(LEVELS) - 1:
                self.feat("trilero_9")
                self.phase = "decide"
                self.collect()
                return
            self.phase = "decide"
            self.show(f"¡Bien visto! Llevas {fmt_money(self.bank)} (x{fmt_num(self.bank / self.pbet)})", GREEN)
        else:
            self.phase = "idle"
            self.fx.add_shake(3)
            self.pay(self.pbet, 0, label=f"Ronda {self.level + 1}: la bola estaba en otro vaso")

    def collect(self):
        if self.phase not in ("decide", "reveal_all"):
            return
        self.phase = "idle"
        self.pay(self.pbet, self.bank, label=f"Te retiras en la ronda {self.level + 1}", pos=(self.vis.centerx,
                                                                                            self.vis.y + 130))

    def continue_next(self):
        if self.phase != "decide":
            return
        self.level += 1
        self.start_round()

    def can_change_variant(self):
        return self.phase == "idle"

    # ---------------------------------------------------------------- update
    def update(self, dt):
        self.timer += dt
        ph = self.phase
        if ph == "show":
            for c in self.cups:
                c["lift"] = 1.0 if self.timer < 1.0 else max(0.0, 1 - (self.timer - 1.0) / 0.3)
            if self.timer > 1.35:
                self.audio.play("cup", 0.7)
                for c in self.cups:
                    c["lift"] = 0.0
                self.next_action()
        elif ph == "swap":
            a = self.anim
            a["t"] += dt
            if a["t"] >= a["dur"]:
                for j, ci in enumerate(a["cups"]):
                    self.cups[ci]["slot"] = a["to"][j]
                self.anim = None
                self.next_action()
        elif ph == "cloth_in":
            self.cloth = min(1.0, self.timer / 0.25)
            if self.timer > 0.25:
                self.cloth_swap()
                self.phase = "cloth_hold"
                self.timer = 0.0
                self.audio.play("slide", 0.5)
        elif ph == "cloth_hold":
            if self.timer > 0.55:
                self.phase = "cloth_out"
                self.timer = 0.0
        elif ph == "cloth_out":
            self.cloth = max(0.0, 1 - self.timer / 0.25)
            if self.timer > 0.25:
                self.cloth = 0.0
                self.next_action()
        elif ph == "reveal":
            self.cups[self.choice]["lift"] = min(1.0, self.timer / 0.25)
            if self.timer > 0.55:
                for c in self.cups:
                    c["lift"] = 1.0
                self.resolve()
        if ph == "choose":
            for i, c in enumerate(self.cups):
                target = 0.7 if i in (self.shown_empty, self.peek_cup) else 0.0
                c["lift"] += (target - c["lift"]) * min(1.0, dt * 10)

    # ----------------------------------------------------------------- dibujo
    def draw(self, surf, rect):
        ui = self.ui
        v = self.vis
        felt(surf, v, (150, 102, 62), (240, 210, 150))
        # escalera de rondas
        lx = v.x + 28
        gfx.text(surf, "RONDAS", (lx, v.y + 24), 12, "b", (255, 236, 210))
        for i, (n, s, h, d) in enumerate(LEVELS):
            r = pygame.Rect(lx + i * 64, v.y + 46, 58, 52)
            active = self.phase != "idle" and i == self.level
            done = self.phase != "idle" and i < self.level
            fill = (253, 162, 0) if active else ((60, 150, 100) if done else (90, 60, 40))
            gfx.box(surf, r, (*fill, 255), 8, ow=4, shadow_off=3)
            gfx.text(surf, f"x{fmt_num(MULTS[i])}", (r.centerx, r.y + 18), 12, "b", TEXT, anchor="center")
            gfx.text(surf, f"{n} vasos", (r.centerx, r.y + 38), 10, "r", (255, 236, 210), anchor="center")
        info = pygame.Rect(v.right - 260, v.y + 22, 232, 80)
        if self.phase != "idle":
            gfx.box(surf, info, (*PANEL_LO, 235), 8, ow=4, shadow_off=4)
            gfx.text(surf, "EN JUEGO", (info.x + 14, info.y + 18), 12, "b", MUTED, anchor="midleft")
            gfx.text(surf, fmt_money(self.bank), (info.x + 14, info.y + 50), 16, "bl", GOLD_HI, anchor="midleft",
                     max_w=info.w - 24)
        pill = self.hint_pill(surf, v.x + 28, v.bottom - 54, 250)
        self.cheat_pill(surf, v.x + 28 + (260 if pill else 0), v.bottom - 54, 250)
        # sombras y bola
        if not self.cups:
            self.cups = [{"slot": i, "lift": 0.0} for i in range(self.n())]
        cw, ch = self.cup_size()
        by = self.base_y()
        for i, cup in enumerate(self.cups):
            x, y = self.cup_pos(i)
            gfx.rrect(surf, (x - cw * 0.5, by + 6, cw, 14), (0, 0, 0, 90), 6)
        if self.cups and self.ball < len(self.cups):
            bx, _ = self.cup_pos(self.ball)
            if self.cups[self.ball]["lift"] > 0.05:
                gfx.circle(surf, (bx, by - 10), 14, (250, 250, 250), border=LINE, bw=2)
        # vasos
        img = cup_sprite(cw, ch)
        order = sorted(range(len(self.cups)), key=lambda i: self.cup_pos(i)[1])
        for i in order:
            x, y = self.cup_pos(i)
            lift = self.cups[i]["lift"]
            yy = y - lift * ch * 0.8
            r = img.get_rect(midbottom=(int(x), int(yy + 12)))
            wid = ("cup", i)
            hov = self.phase == "choose" and ui.hover(r) and i != self.shown_empty
            hv = ui.anim(wid, 1.0 if hov else 0.0, 18)
            if hv > 0.01:
                r = r.move(0, -int(8 * hv))
                gfx.glow(surf, r.center, cw, (255, 220, 120), 0.4 * hv)
            surf.blit(img, r)
            if self.stain == i:
                cx, cy = r.centerx + cw * 0.12, r.y + r.h * 0.45
                for dx, dy, rr in ((0, 0, 9), (8, 5, 6), (-6, 7, 5), (4, -8, 4)):
                    gfx.circle(surf, (cx + dx, cy + dy), rr, (96, 60, 30))
            if self.xray and i == self.ball and self.phase != "idle":
                gfx.circle(surf, (r.centerx, r.bottom - 26), 13, (240, 230, 255), border=(200, 90, 255), bw=3)
            if self.marked == i and self.phase == "choose":
                gfx.text(surf, "TU VASO", (r.centerx, r.y - 14), 12, "b", GOLD_HI, anchor="center")
            if hov:
                ui.hot_any = True
                if ui.pressed:
                    ui.active = wid
                if ui.released and ui.active == wid:
                    self.pick(i)
        # pañuelo: tapa solo los dos vasos vecinos
        if self.cloth > 0:
            a, b = self.cloth_slots
            x0 = self.slot_x(a) - cw * 0.75
            x1 = self.slot_x(b) + cw * 0.75
            top = by - ch - 30
            hgt = int((ch + 70) * self.cloth)
            cr = pygame.Rect(int(x0), int(top), int(x1 - x0), max(4, hgt))
            gfx.box(surf, cr, (170, 40, 60, 255), 6, ow=4, shadow_off=6)
            for k in range(0, cr.w - 8, 20):
                for j in range(0, cr.h - 8, 20):
                    if (k // 20 + j // 20) % 2 == 0:
                        surf.fill((200, 70, 80), (cr.x + k + 4, cr.y + j + 4, 10, 10))
        # controles
        c = self.controls_rect(rect)
        controls_bg(surf, c)
        self.bet_control(surf, c.x + 16, c.y + 10)
        keys = ui.keys if not ui.focus else []
        if self.phase == "idle":
            gfx.text_wrapped(surf, "Sigue la bola. El pañuelo tapa dos vasos y los cruza... o no. Puedes retirarte "
                                   "después de cada ronda.", (c.x + 372, c.y + 20), 12, "r", MUTED, 420)
            if ui.button("go", (c.right - 200, c.y + 18, 184, 70), "APOSTAR", "green", size=18, sound=None) or \
                    pygame.K_SPACE in keys:
                self.bet_and_start()
        elif self.phase == "decide":
            nxt = MULTS[self.level + 1]
            if ui.button("cash", (c.x + 380, c.y + 18, 230, 70), "RETIRARSE", "gold", size=16,
                         sub=fmt_money(self.bank), sound=None):
                self.collect()
            if ui.button("more", (c.right - 250, c.y + 18, 234, 70), "SEGUIR", "red", size=16,
                         sub=f"ronda {self.level + 2}: x{fmt_num(nxt)}", sound=None):
                self.continue_next()
        elif self.phase == "choose":
            gfx.text(surf, f"Ronda {self.level + 1} · elige un vaso", (c.x + 380, c.y + 20), 14, "b", TEXT)
            bx = c.x + 380
            if self.has_hint("trilero_monty") and self.marked is None:
                ready = self.hint_ready("trilero_monty")
                lbl = "Que enseñe uno" if ready else "Enseña uno: recargando"
                if ui.button("monty", (bx, c.y + 50, 200, 44), lbl, "primary" if self.mode != "monty" else "gold",
                             enabled=ready, size=12, tooltip="Señala un vaso y el trilero levantará otro vacío."):
                    self.use_hint("trilero_monty")
                    self.mode = "monty"
                    self.show("Señala tu vaso...", GOLD_HI)
                bx += 210
            if self.has_hint("trilero_peek") and self.peek_cup is None:
                ready = self.hint_ready("trilero_peek")
                if ui.button("peek", (bx, c.y + 50, 200, 44), "Levantar uno" if ready else "Mano rápida: recargando",
                             "gold" if self.mode == "peek" else "primary", enabled=ready, size=12,
                             tooltip="Levanta un vaso para mirar antes de elegir."):
                    self.use_hint("trilero_peek")
                    self.mode = "peek"
                    self.show("Elige el vaso que quieres levantar", GOLD_HI)
        else:
            gfx.text(surf, f"Ronda {self.level + 1} · {self.n()} vasos", (c.x + 380, c.y + 40), 16, "b", TEXT)
