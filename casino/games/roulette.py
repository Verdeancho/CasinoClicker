import math
import random

import pygame

from .base import BaseGame
from .common import felt, controls_bg, dark_panel
from .. import gfx, art
from ..fmt import fmt_money
from ..gfx import TEXT, MUTED, DIM, GOLD, GOLD_HI, GREEN, RED

WHEEL = [0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10, 5, 24, 16, 33, 1, 20, 14, 31,
         9, 22, 18, 29, 7, 28, 12, 35, 3, 26]
REDS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
C_RED, C_BLACK, C_GREEN = (200, 36, 48), (26, 26, 32), (20, 150, 76)
SEG = 360 / 37
R = 168
CW, CH = 34, 54


def num_color(n):
    return C_GREEN if n == 0 else (C_RED if n in REDS else C_BLACK)


def bet_wins(key, n):
    kind = key[0]
    if kind == "n":
        return n == key[1]
    if n == 0:
        return False
    return {"red": n in REDS, "black": n not in REDS, "even": n % 2 == 0, "odd": n % 2 == 1, "low": n <= 18,
            "high": n >= 19, "dozen": (n - 1) // 12 + 1 == key[-1], "col": (n - 1) % 3 + 1 == key[-1]}[kind]


def payout_mult(key):
    return 36 if key[0] == "n" else 3 if key[0] in ("dozen", "col") else 2


_wheel_cache = {}


def wheel_sprite(radius):
    if radius in _wheel_cache:
        return _wheel_cache[radius]
    k = 3
    Rb = radius * k
    D = Rb * 2 + 8
    s = pygame.Surface((D, D), pygame.SRCALPHA)
    c = D / 2

    def P(ang, r):
        a = math.radians(ang)
        return (c + r * math.cos(a), c - r * math.sin(a))

    for i in range(40):
        t = i / 39
        pygame.draw.circle(s, gfx.lerp_col((70, 36, 14), (150, 90, 40), math.sin(t * math.pi)), (c, c), Rb * (1 - t * 0.12))
    pygame.draw.circle(s, (200, 160, 80), (c, c), Rb * 0.88, k * 2)
    pygame.draw.circle(s, (30, 18, 10), (c, c), Rb * 0.86)
    r_out, r_in = Rb * 0.85, Rb * 0.62
    for i, n in enumerate(WHEEL):
        th = 90 - i * SEG
        pts = [P(th - SEG / 2 + SEG * j / 6, r_out) for j in range(7)] + \
              [P(th + SEG / 2 - SEG * j / 6, r_in) for j in range(7)]
        pygame.draw.polygon(s, num_color(n), pts)
        pygame.draw.line(s, (220, 180, 90), P(th - SEG / 2, r_in), P(th - SEG / 2, r_out), k)
    f = gfx.font(int(radius * 0.085 * k), "b")
    for i, n in enumerate(WHEEL):
        th = 90 - i * SEG
        t = f.render(str(n), True, (255, 255, 255))
        t = pygame.transform.rotate(t, th - 90)
        s.blit(t, t.get_rect(center=P(th, r_out - Rb * 0.075)))
    # fondo de los bolsillos
    pygame.draw.circle(s, (220, 180, 90), (c, c), r_in, k * 2)
    for i in range(30):
        t = i / 29
        pygame.draw.circle(s, gfx.lerp_col((90, 56, 24), (170, 110, 50), t), (c, c), r_in * 0.97 * (1 - t * 0.55))
    # torreta central
    for i in range(20):
        t = i / 19
        pygame.draw.circle(s, gfx.lerp_col((150, 110, 40), (255, 230, 150), t), (c - t * Rb * 0.03, c - t * Rb * 0.03),
                           Rb * 0.22 * (1 - t * 0.7))
    for j in range(4):
        a = j * 90 + 45
        p1, p2 = P(a, Rb * 0.08), P(a, Rb * 0.4)
        pygame.draw.line(s, (230, 190, 100), p1, p2, k * 5)
        pygame.draw.circle(s, (255, 230, 150), p2, k * 6)
    pygame.draw.circle(s, (255, 240, 190), (c, c), Rb * 0.06)
    img = pygame.transform.smoothscale(s, (int(D / k), int(D / k)))
    _wheel_cache[radius] = img
    return img


class Roulette(BaseGame):
    gid = "roulette"

    def setup(self):
        self.bets = {}
        self.last_bets = {}
        self.hist = []
        self.w = 0.0
        self.ball = None
        self.spin_st = None
        self.result = None
        self.win_t = 0.0
        self.last_seg = None
        self.forced_n = None      # número decidido por la rueda trucada (legendaria)

    # --------------------------------------------------------- geometría
    def wheel_center(self):
        return (self.vis.x + 186, self.vis.y + self.vis.h // 2 + 4)

    def board_origin(self):
        return self.vis.x + 360, self.vis.y + 92

    def cell_rect(self, key):
        bx, by = self.board_origin()
        kind = key[0]
        if kind == "n":
            n = key[1]
            if n == 0:
                return pygame.Rect(bx, by, CW, CH * 3)
            col, row = (n - 1) // 3, 2 - (n - 1) % 3
            return pygame.Rect(bx + CW + col * CW, by + row * CH, CW, CH)
        if kind == "col":
            return pygame.Rect(bx + 13 * CW, by + (3 - key[1]) * CH, CW + 10, CH)
        if kind == "dozen":
            return pygame.Rect(bx + CW + (key[1] - 1) * 4 * CW, by + 3 * CH, 4 * CW, 40)
        outs = ["low", "even", "red", "black", "odd", "high"]
        i = outs.index(kind)
        return pygame.Rect(bx + CW + i * 2 * CW, by + 3 * CH + 40, 2 * CW, 40)

    def all_keys(self):
        return ([("n", n) for n in range(37)] + [("col", i) for i in (1, 2, 3)] + [("dozen", i) for i in (1, 2, 3)]
                + [(k,) for k in ("low", "even", "red", "black", "odd", "high")])

    # --------------------------------------------------------- apuestas
    def add_bet(self, key):
        if self.spin_st:
            return
        chip = self.bet
        total = sum(self.bets.values()) + chip
        if total > self.state.money + 1e-9:
            self.show("No tienes suficiente dinero", RED)
            self.audio.play("error")
            return
        self.bets[key] = self.bets.get(key, 0) + chip
        self.result = None
        self.audio.play(f"chip{random.randint(0, 2)}")

    def spin(self):
        if self.spin_st or not self.bets:
            if not self.bets:
                self.show("Pon fichas en el tapete", MUTED)
            return
        total = sum(self.bets.values())
        if not self.take_bet(total):
            return
        self.last_bets = dict(self.bets)
        self.result = None
        if self.use_cheat():
            target = max(range(37), key=lambda n: sum(a * payout_mult(k) for k, a in self.bets.items() if bet_wins(k, n)))
        elif self.forced_n is not None:
            target = self.forced_n
        else:
            target = random.randrange(37)
        self.forced_n = None
        self.spin_st = {"t": 0.0, "dur": 5.2, "w0": self.w, "wt": 360 * 2 + random.uniform(0, 360), "idx": WHEEL.index(target),
                        "num": target, "total": total}
        self.audio.play("whoosh")

    def update(self, dt):
        self.win_t += dt
        st = self.spin_st
        if not st:
            return
        st["t"] += dt
        u = min(1.0, st["t"] / st["dur"])
        e = gfx.ease_out_cubic(u)
        self.w = st["w0"] - st["wt"] * e
        tb = min(1.0, u / 0.8)
        off = -360 * 4 * (1 - gfx.ease_out_cubic(tb))
        beta = 90 - st["idx"] * SEG + self.w + off
        r_track, r_pocket = 0.93, 0.735
        if u < 0.5:
            rr = r_track
        else:
            k = min(1.0, (u - 0.5) / 0.3)
            rr = r_track - (r_track - r_pocket) * k + abs(math.sin(k * math.pi * 3)) * 0.04 * (1 - k)
        self.ball = (beta, rr)
        rel = (beta - self.w) % 360
        seg = int(rel / SEG)
        if self.last_seg is not None and seg != self.last_seg and 0.45 < u < 0.86:
            self.audio.play(f"tick{random.randint(0, 3)}", 1.0 - (u - 0.45), throttle=0.03)
        self.last_seg = seg
        if u >= 1.0:
            self.spin_st = None
            self.audio.play("ball_land")
            self.later(0.25, lambda: self.finish(st["num"], st["total"]))

    def finish(self, n, total):
        self.result = n
        self.win_t = 0.0
        self.hist.append(n)
        gross = 0.0
        for key, amt in self.bets.items():
            if bet_wins(key, n):
                gross += amt * payout_mult(key)
                if key[0] == "n":
                    self.feat("roulette_straight")
            elif n == 0 and key[0] in ("red", "black", "even", "odd", "low", "high") and \
                    self.state.lvl("roulette_partage"):
                gross += amt / 2
        col = "VERDE" if n == 0 else ("ROJO" if n in REDS else "NEGRO")
        wc = self.wheel_center()
        self.pay(total, gross, label=f"{n} {col}", pos=(wc[0], wc[1] - 60))
        if sum(self.bets.values()) > self.state.money + 1e-9:
            self.bets = {}

    # ------------------------------------------------------------ dibujo
    def draw(self, surf, rect):
        ui = self.ui
        v = self.vis
        felt(surf, v)
        cx, cy = self.wheel_center()
        # rueda
        sh = gfx.shadow_surf(R * 2, R * 2, R, 18, 160)
        surf.blit(sh, (cx - R - 36, cy - R - 28))
        img = wheel_sprite(R)
        rot = pygame.transform.rotozoom(img, self.w, 1.0)
        surf.blit(rot, rot.get_rect(center=(cx, cy)))
        # brillo fijo encima (la luz no gira)
        gfx.glow(surf, (cx - R * 0.35, cy - R * 0.45), int(R * 0.7), (90, 80, 60), 0.25)
        if self.ball:
            beta, rr = self.ball
            a = math.radians(beta)
            bx, by = cx + R * rr * math.cos(a), cy - R * rr * math.sin(a)
            gfx.circle(surf, (bx + 2, by + 3), 7, (0, 0, 0, 120))
            gfx.circle(surf, (bx, by), 7, (246, 246, 250))
            gfx.circle(surf, (bx - 2, by - 2), 3, (255, 255, 255))
        if self.result is not None and not self.spin_st:
            k = gfx.ease_out_back(min(1, self.win_t / 0.4))
            rad = max(1, int(30 * k))
            gfx.glow(surf, (cx, cy), 70, (255, 220, 120), 0.4)
            gfx.circle(surf, (cx, cy), rad + 3, (255, 220, 120))
            gfx.circle(surf, (cx, cy), rad, num_color(self.result))
            if k > 0.6:
                gfx.text(surf, str(self.result), (cx, cy), 24, "bl", TEXT, anchor="center")
        # historial
        bx, by = self.board_origin()
        gfx.text(surf, "ÚLTIMOS", (bx, v.y + 26), 12, "b", (200, 230, 210))
        for i, n in enumerate(self.hist[-13:][::-1]):
            p = (bx + gfx.text_w("ÚLTIMOS", 12, "b") + 24 + i * 30, v.y + 34)
            gfx.circle(surf, p, 12 if i else 14, num_color(n), border=(255, 230, 150) if i == 0 else None, bw=2)
            gfx.text(surf, str(n), p, 11, "b", TEXT, anchor="center")
        # tapete
        labels = {"low": "1-18", "even": "PAR", "odd": "IMPAR", "high": "19-36"}
        win_keys = set()
        if self.result is not None:
            win_keys = {k for k in self.all_keys() if bet_wins(k, self.result)}
        for key in self.all_keys():
            r = self.cell_rect(key)
            kind = key[0]
            if kind == "n":
                fill = num_color(key[1])
            else:
                fill = (16, 100, 62)
            pygame.draw.rect(surf, fill, r)
            pygame.draw.rect(surf, (220, 236, 224), r, 1)
            if kind == "n":
                gfx.text(surf, str(key[1]), r.center, 15, "b", TEXT, anchor="center")
            elif kind == "col":
                gfx.text(surf, "2:1", r.center, 12, "b", TEXT, anchor="center")
            elif kind == "dozen":
                gfx.text(surf, ["1ª 12", "2ª 12", "3ª 12"][key[1] - 1], r.center, 13, "b", TEXT, anchor="center")
            elif kind in ("red", "black"):
                c2 = r.center
                gfx.aa_poly(surf, C_RED if kind == "red" else C_BLACK,
                            [(c2[0] - 22, c2[1]), (c2[0], c2[1] - 13), (c2[0] + 22, c2[1]), (c2[0], c2[1] + 13)])
            else:
                gfx.text(surf, labels[kind], r.center, 13, "b", TEXT, anchor="center")
            wid = ("rb", key)
            h = ui.hover(r) and not self.spin_st
            hv = ui.anim(wid, 1.0 if h else 0.0, 20)
            if hv > 0.02:
                gfx.rrect(surf, r, (255, 255, 255, 255), 2, alpha=int(60 * hv))
            if key in win_keys and not self.spin_st and self.win_t < 6:
                a = int(120 + 100 * math.sin(self.win_t * 8))
                pygame.draw.rect(surf, (255, 230, 120), r, 3)
                gfx.rrect(surf, r, (255, 230, 120, 255), 2, alpha=max(0, a // 3))
            if h:
                ui.hot_any = True
                if ui.pressed:
                    ui.active = wid
                if ui.released and ui.active == wid:
                    self.add_bet(key)
                if ui.rpressed and key in self.bets:
                    del self.bets[key]
                    self.audio.play("chip1", 0.6)
        for key, amt in self.bets.items():
            r = self.cell_rect(key)
            chip = art.chip_with_text(36, amt)
            surf.blit(chip, chip.get_rect(center=r.center))
        total = sum(self.bets.values())
        gfx.text(surf, "Clic: ficha · clic der.: quitar", (bx, by + 3 * CH + 96), 10, "r", (190, 220, 200))
        gfx.text(surf, f"En mesa: {fmt_money(total)}", (bx + 484, by + 3 * CH + 92), 12, "b", GOLD_HI,
                 anchor="topright")
        # controles
        c = self.controls_rect(rect)
        controls_bg(surf, c)
        self.bet_control(surf, c.x + 16, c.y + 12, "VALOR DE LA FICHA")
        busy = bool(self.spin_st)
        if ui.button("clear", (c.x + 380, c.y + 18, 110, 30), "Borrar", "dark", enabled=not busy, size=13):
            self.bets = {}
        if ui.button("repeat", (c.x + 380, c.y + 54, 110, 30), "Repetir", "dark", enabled=not busy and bool(self.last_bets),
                     size=13):
            if sum(self.last_bets.values()) <= self.state.money + 1e-9:
                self.bets = dict(self.last_bets)
        if ui.button("double", (c.x + 500, c.y + 18, 110, 30), "Doblar", "dark", enabled=not busy and bool(self.bets),
                     size=13):
            if total * 2 <= self.state.money + 1e-9:
                self.bets = {k: x * 2 for k, x in self.bets.items()}
            else:
                self.show("No tienes fondos para doblar", RED)
        pill = self.hint_pill(surf, v.x + 24, v.bottom - 54, 250, key="roulette_dozen", name="Rueda trucada")
        if pill and self.hint_ready("roulette_dozen") and self.forced_n is None and not busy:
            if ui.button("dozen", (pill.right + 10, pill.y - 6, 150, 44), "Escuchar", "gold", size=12):
                self.use_hint("roulette_dozen")
                self.forced_n = random.randrange(37)
        if self.forced_n is not None:
            fn = self.forced_n
            msg = "¡Va a salir el CERO!" if fn == 0 else f"Caerá en la {('1ª', '2ª', '3ª')[(fn - 1) // 12]} docena"
            gfx.wavy_text(surf, msg, (v.centerx + 140, v.y + 64), 14, GOLD_HI, self.t, 2, 5)
        self.cheat_pill(surf, v.right - 280, v.bottom - 54, 256)
        if ui.button("spin", (c.right - 200, c.y + 18, 180, 64), "GIRAR", "red", enabled=not busy and bool(self.bets),
                     size=22, sound=None) or (pygame.K_SPACE in ui.keys and not ui.focus and not busy):
            self.spin()
