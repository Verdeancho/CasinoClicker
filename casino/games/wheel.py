import math
import random

import pygame

from .base import BaseGame
from .common import dark_panel, controls_bg
from .. import gfx, art
from ..fmt import fmt_money, fmt_num
from ..gfx import TEXT, MUTED, DIM, GOLD, GOLD_HI, RED

TYPES = [("a", 2.15, 24, (255, 200, 60)), ("b", 3.45, 15, (70, 150, 255)), ("c", 7.4, 7, (170, 100, 255)),
         ("d", 13, 4, (255, 140, 50)), ("e", 26, 2, (255, 80, 100)), ("f", 50, 1, (40, 220, 190))]
TYPE_BY_ID = {t[0]: t for t in TYPES}
N_SEG = sum(t[2] for t in TYPES)
SEG = 360 / N_SEG
R = 178


def build_layout():
    slots = [None] * N_SEG
    for idx, (tid, _p, cnt, _c) in enumerate(sorted(TYPES, key=lambda t: t[2])):
        offset = idx * 3.7
        for j in range(cnt):
            target = int(j * N_SEG / cnt + offset) % N_SEG
            d = 0
            placed = False
            while not placed:
                for cand in (target + d, target - d):
                    cand %= N_SEG
                    if slots[cand] is None:
                        slots[cand] = tid
                        placed = True
                        break
                d += 1
    return slots


LAYOUT = build_layout()
_sprite = {}


def wheel_sprite():
    if "w" in _sprite:
        return _sprite["w"]
    k = 3
    Rb = R * k
    D = Rb * 2 + 12
    s = pygame.Surface((D, D), pygame.SRCALPHA)
    c = D / 2

    def P(ang, r):
        a = math.radians(ang)
        return (c + r * math.cos(a), c - r * math.sin(a))

    pygame.draw.circle(s, (70, 30, 90), (c, c), Rb + 4)
    pygame.draw.circle(s, (255, 210, 110), (c, c), Rb + 4, k * 3)
    for i, tid in enumerate(LAYOUT):
        col = TYPE_BY_ID[tid][3]
        th = 90 - (i + 0.5) * SEG
        pts = [(c, c)] + [P(th - SEG / 2 + SEG * j / 4, Rb * 0.97) for j in range(5)]
        pygame.draw.polygon(s, col, pts)
        inner = [(c, c)] + [P(th - SEG / 2 + SEG * j / 4, Rb * 0.55) for j in range(5)]
        pygame.draw.polygon(s, gfx.mul_col(col, 0.82), inner)
        pygame.draw.line(s, (60, 24, 80), (c, c), P(th - SEG / 2, Rb * 0.97), k)
    f = gfx.font(int(R * 0.075 * k), "bl")
    for i, tid in enumerate(LAYOUT):
        th = 90 - (i + 0.5) * SEG
        t = f.render(fmt_num(TYPE_BY_ID[tid][1], 2 if TYPE_BY_ID[tid][1] < 10 else 0), True, (30, 16, 40))
        t = pygame.transform.rotate(t, th)
        s.blit(t, t.get_rect(center=P(th, Rb * 0.78)))
    for i in range(N_SEG):
        th = 90 - i * SEG
        pygame.draw.circle(s, (255, 230, 160), P(th, Rb * 0.985), k * 3)
    pygame.draw.circle(s, (50, 20, 70), (c, c), Rb * 0.2)
    pygame.draw.circle(s, (255, 210, 110), (c, c), Rb * 0.2, k * 3)
    img = pygame.transform.smoothscale(s, (int(D / k), int(D / k)))
    _sprite["w"] = img
    return img


class Wheel(BaseGame):
    gid = "wheel"

    def setup(self):
        self.rot = 0.0
        self.bets = {}
        self.last_bets = {}
        self.golden = None
        self.result = None
        self.hist = []
        self.spin_st = None
        self.flap = 0.0
        self.last_seg = 0
        self.win_t = 0.0

    def center(self):
        return (self.vis.x + 210, self.vis.y + self.vis.h // 2 + 14)

    def add_bet(self, tid):
        if self.spin_st:
            return
        chip = self.bet
        total = sum(self.bets.values()) + chip
        if total > self.state.money + 1e-9:
            self.show("Límite de apuesta o fondos insuficientes", RED)
            self.audio.play("error")
            return
        self.bets[tid] = self.bets.get(tid, 0) + chip
        self.result = None
        self.audio.play(f"chip{random.randint(0, 2)}")

    def spin(self):
        if self.spin_st:
            return
        if not self.bets:
            self.show("Pon fichas en algún color", MUTED)
            return
        total = sum(self.bets.values())
        if not self.take_bet(total):
            return
        self.last_bets = dict(self.bets)
        self.result = None
        self.golden = random.randrange(N_SEG) if self.state.lvl("wheel_bonus") else None
        target = random.randrange(N_SEG)
        want = ((target + 0.5) * SEG + random.uniform(-0.38, 0.38) * SEG) % 360
        delta = (want - self.rot) % 360 + 360 * 5
        self.spin_st = {"t": 0.0, "dur": 5.5, "r0": self.rot, "delta": delta, "target": target, "total": total}
        self.audio.play("whoosh")

    def update(self, dt):
        self.win_t += dt
        self.flap = gfx.approach(self.flap, 0, dt, 9)
        st = self.spin_st
        if not st:
            return
        st["t"] += dt
        u = min(1.0, st["t"] / st["dur"])
        self.rot = st["r0"] + st["delta"] * gfx.ease_out_quart(u)
        seg = int(self.rot / SEG)
        if seg != self.last_seg:
            self.last_seg = seg
            self.flap = 1.0
            self.audio.play(f"tick{random.randint(0, 3)}", 0.9, throttle=0.02)
        if u >= 1:
            self.spin_st = None
            self.rot %= 360
            self.finish(st["target"], st["total"])

    def finish(self, idx, total):
        self.result = idx
        self.win_t = 0.0
        self.hist.append(idx)
        tid = LAYOUT[idx]
        pay = TYPE_BY_ID[tid][1]
        golden = self.golden == idx
        gross = self.bets.get(tid, 0) * pay * (2 if golden else 1)
        if tid == "f" and self.bets.get(tid):
            self.feat("wheel_top")
        cx, cy = self.center()
        self.pay(total, gross, label=f"x{fmt_num(pay)}" + ("  ¡DORADO x2!" if golden else ""), pos=(cx, cy - R - 20))
        if sum(self.bets.values()) > min(self.state.money, self.state.max_bet()) + 1e-9:
            self.bets = {}

    def draw(self, surf, rect):
        ui = self.ui
        v = self.vis
        dark_panel(surf, v, 20, (40, 18, 56), (16, 8, 26))
        cx, cy = self.center()
        gfx.glow(surf, (cx, cy), R + 80, (150, 70, 200), 0.4)
        sh = gfx.shadow_surf(R * 2, R * 2, R, 18, 170)
        surf.blit(sh, (cx - R - 36, cy - R - 26))
        img = pygame.transform.rotozoom(wheel_sprite(), self.rot, 1.0)
        surf.blit(img, img.get_rect(center=(cx, cy)))
        if self.golden is not None:
            th = 90 - (self.golden + 0.5) * SEG + self.rot
            pts = [(cx, cy)] + [(cx + R * 0.97 * math.cos(math.radians(th - SEG / 2 + SEG * j / 4)),
                                 cy - R * 0.97 * math.sin(math.radians(th - SEG / 2 + SEG * j / 4))) for j in range(5)]
            gfx.aa_poly(surf, (255, 240, 140, 150), pts)
        # luces
        for i in range(24):
            a = i * math.tau / 24
            p = (cx + (R + 14) * math.cos(a), cy + (R + 14) * math.sin(a))
            lit = (int(ui.t * (12 if self.spin_st else 3)) + i) % 3 == 0
            if lit:
                gfx.glow(surf, p, 12, (255, 220, 120), 0.8)
            gfx.circle(surf, p, 4, (255, 240, 190) if lit else (120, 80, 60))
        # centro
        gfx.circle(surf, (cx, cy), 40, (40, 16, 56), border=(255, 210, 110), bw=3)
        if self.result is not None and not self.spin_st:
            pay = TYPE_BY_ID[LAYOUT[self.result]][1]
            k = gfx.ease_out_back(min(1, self.win_t / 0.4))
            gfx.blit_center(surf, gfx.scaled(gfx.text_surf(f"x{fmt_num(pay)}", 20, "bl", GOLD_HI), max(0.05, k)), (cx, cy))
        else:
            gfx.aa_poly(surf, GOLD, gfx.star_points(cx, cy, 20, 8))
        # puntero con aleta
        ang = -self.flap * 22
        base = (cx, cy - R - 26)
        tip = (cx + math.sin(math.radians(ang)) * 40, cy - R + 14)
        left = (base[0] - 18, base[1])
        right = (base[0] + 18, base[1])
        gfx.aa_poly(surf, (0, 0, 0, 120), [(left[0] + 3, left[1] + 4), (right[0] + 3, right[1] + 4), (tip[0] + 3, tip[1] + 4)])
        gfx.aa_poly(surf, (250, 250, 255), [left, right, tip])
        gfx.circle(surf, base, 10, (255, 210, 110))
        # tablero de apuestas
        bx = v.x + 440
        gfx.text(surf, "Clic: ficha · clic der.: quitar", (bx, v.y + 18), 10, "r", MUTED)
        cw = (v.right - 20 - bx - 12) // 2
        for j, (tid, pay, cnt, col) in enumerate(TYPES):
            r = pygame.Rect(bx + (j % 2) * (cw + 12), v.y + 44 + (j // 2) * 104, cw, 94)
            wid = ("wb", tid)
            h = ui.hover(r) and not self.spin_st
            hv = ui.anim(wid, 1.0 if h else 0.0)
            win = self.result is not None and LAYOUT[self.result] == tid and not self.spin_st
            gfx.shadow(surf, r, 14, 10, 100, (0, 5))
            gfx.rrect(surf, r.move(0, -int(3 * hv)), None, 14, border=(255, 255, 255) if win else gfx.mul_col(col, 1.3),
                      bw=3 if win else 1, grad=((*gfx.mul_col(col, 1.05), 255), (*gfx.mul_col(col, 0.6), 255)))
            rr = r.move(0, -int(3 * hv))
            if win:
                gfx.glow(surf, rr.center, 90, col, 0.4 + 0.2 * math.sin(self.win_t * 8))
            gfx.text(surf, f"x{fmt_num(pay)}", (rr.x + 16, rr.y + 12), 22, "bl", (34, 18, 40))
            gfx.text(surf, f"{cnt / N_SEG * 100:.1f}%", (rr.x + 16, rr.y + 54), 12, "b", (44, 24, 50))
            amt = self.bets.get(tid)
            if amt:
                chip = art.chip_with_text(48, amt)
                surf.blit(chip, chip.get_rect(center=(rr.right - 36, rr.centery)))
            if h:
                ui.hot_any = True
                if ui.pressed:
                    ui.active = wid
                if ui.released and ui.active == wid:
                    self.add_bet(tid)
                if ui.rpressed and tid in self.bets:
                    del self.bets[tid]
                    self.audio.play("chip1", 0.6)
        # historial
        hy = v.y + 44 + 3 * 104 + 6
        gfx.text(surf, "ÚLTIMOS", (bx, hy), 12, "b", MUTED)
        for i, idx in enumerate(self.hist[-11:][::-1]):
            tid = LAYOUT[idx]
            p = (bx + 16 + i * 36, hy + 34)
            gfx.circle(surf, p, 15, TYPE_BY_ID[tid][3], border=(255, 255, 255) if i == 0 else None, bw=2)
            gfx.text(surf, fmt_num(TYPE_BY_ID[tid][1], 0), p, 10, "bl", (30, 14, 36), anchor="center")
        if self.state.lvl("wheel_bonus"):
            gfx.aa_poly(surf, (255, 236, 140), gfx.star_points(bx + 7, hy + 78, 7, 3))
            gfx.text(surf, "Segmento dorado: paga x2", (bx + 20, hy + 70), 12, "b", (255, 236, 140))
        # controles
        c = self.controls_rect(rect)
        controls_bg(surf, c)
        self.bet_control(surf, c.x + 16, c.y + 12, "VALOR DE LA FICHA")
        busy = bool(self.spin_st)
        total = sum(self.bets.values())
        gfx.text(surf, f"En juego: {fmt_money(total)}", (c.x + 380, c.y + 14), 13, "b", GOLD_HI)
        if ui.button("clear", (c.x + 380, c.y + 40, 100, 40), "Borrar", "dark", enabled=not busy, size=13):
            self.bets = {}
        if ui.button("repeat", (c.x + 488, c.y + 40, 100, 40), "Repetir", "dark", enabled=not busy and bool(self.last_bets),
                     size=13):
            if sum(self.last_bets.values()) <= min(self.state.money, self.state.max_bet()) + 1e-9:
                self.bets = dict(self.last_bets)
        keys = ui.keys if not ui.focus else []
        if ui.button("spin", (c.right - 200, c.y + 18, 180, 64), "GIRAR", "pink", enabled=not busy and bool(self.bets),
                     size=22, sound=None) or (pygame.K_SPACE in keys and not busy):
            self.spin()
