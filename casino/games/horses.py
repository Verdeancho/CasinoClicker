import math
import random

import pygame

from .base import BaseGame
from .common import controls_bg, dark_panel
from .. import gfx, art
from ..fmt import fmt_money
from ..gfx import TEXT, MUTED, DIM, GOLD, GOLD_HI, GREEN, RED

NAMES = ["Relámpago", "Tornado", "Pegaso", "Canela", "Bucéfalo", "Rocinante", "Babieca", "Centella", "Trueno",
         "Azabache", "Lucero", "Furia", "Galerna", "Cometa", "Sultán", "Mistral", "Zafiro", "Duende"]
SILKS = [(230, 60, 80), (60, 130, 240), (250, 200, 50), (50, 200, 110), (170, 90, 230), (240, 240, 245)]
COATS = [(120, 72, 40), (70, 44, 30), (150, 100, 60), (60, 60, 64), (170, 130, 90), (40, 30, 26)]
EDGE = 0.95
N = 6
TRACK_LEN = 3200
LEAD_AT = 0.4                # el líder corre al 40% del ancho: se ve venir la meta
POSTS = (800, 400, 200)      # postes de distancia antes de la meta


class Horses(BaseGame):
    gid = "horses"

    def setup(self):
        self.pick = None
        self.racing = False
        self.cam = 0.0
        self.rt = 0.0
        self.pbet = 0.0
        self.order = None
        self.done_t = None
        self.gallop_t = 0.0
        self.new_race()

    def new_race(self):
        names = random.sample(NAMES, N)
        raw = [random.gammavariate(2.2, 1.0) for _ in range(N)]
        probs = [max(0.03, r / sum(raw)) for r in raw]
        probs = [p / sum(probs) for p in probs]
        coats = random.sample(COATS, N)
        self.horses = [{"name": names[i], "odds": max(1.2, round(EDGE / probs[i], 1)), "silk": SILKS[i],
                        "coat": coats[i], "x": 0.0, "fin": None} for i in range(N)]
        self.true_p = list(probs)
        self.tip = None
        self.pre_order = None
        # probabilidad de quedar entre los dos primeros (Plackett-Luce) → cuota a colocado
        for i, h in enumerate(self.horses):
            p2 = probs[i] + sum(probs[j] * probs[i] / (1 - probs[j]) for j in range(N) if j != i)
            h["place"] = max(1.05, round(EDGE / p2, 2))
        self.pick = None
        self.order = None
        self.cam = 0.0
        self.done_t = None

    def start(self):
        if self.racing or self.order:
            return
        if self.pick is None:
            self.show("Elige primero un caballo", MUTED)
            return
        if not self.take_bet(self.bet):
            return
        self.pbet = self.bet
        self.bet_kind = "place" if (getattr(self, "kind", 0) == 1 and self.state.lvl("horses_place")) else "win"
        if self.use_cheat():
            rest = [i for i in range(N) if i != self.pick]
            random.shuffle(rest)
            self.pre_order = [self.pick] + rest
        self.order = order = self.pre_order or self.draw_order()
        t = 9.0
        self.finish_t = {}
        for hidx in order:
            self.finish_t[hidx] = t
            t += random.uniform(0.08, 0.5)
        self.wob = [(random.uniform(0.1, 0.22), random.uniform(1.5, 3.5), random.uniform(0, 6.28)) for _ in range(N)]
        self.rt = 0.0
        self.racing = True
        self.banner = None
        self.audio.play("race_start")

    def draw_order(self):
        remaining = list(range(N))
        order = []
        while remaining:
            k = random.choices(range(len(remaining)), weights=[self.true_p[r] for r in remaining])[0]
            order.append(remaining.pop(k))
        return order

    def ask_tip(self):
        """Soplo: el caballo señalado suele ganar (la fiabilidad no se muestra)."""
        self.use_hint()
        self.pre_order = self.draw_order()
        if random.random() < self.reliable(0.45):
            self.tip = self.pre_order[0]
        else:
            self.tip = random.choice(self.pre_order[1:])

    def update(self, dt):
        if not self.racing:
            if self.done_t is not None:
                self.done_t += dt
                if self.done_t > 3.5:
                    self.new_race()
            return
        self.rt += dt
        all_done = True
        for i, h in enumerate(self.horses):
            T = self.finish_t[i]
            u = min(1.0, self.rt / T)
            a, f, ph = self.wob[i]
            pos = u + a * math.sin(f * u * math.pi + ph) * u * (1 - u)
            h["x"] = (pos if u < 1 else 1.0 + (self.rt - T) * 0.04) * TRACK_LEN
            if u < 1:
                all_done = False
        lead = max(h["x"] for h in self.horses)
        w = self.vis.w
        target_cam = min(max(0.0, lead + 60 - w * LEAD_AT), TRACK_LEN + 60 - w * 0.72)
        self.cam = gfx.approach(self.cam, target_cam, dt, 4)
        self.gallop_t += dt
        if self.gallop_t > 0.19:
            self.gallop_t = 0
            self.audio.play("gallop", random.uniform(0.6, 1.0), pan=random.uniform(-0.4, 0.4), throttle=0.05)
        if self.rt > self.finish_t[self.order[0]] and not getattr(self, "_announced", False):
            self._announced = True
        if all_done:
            self._announced = False
            self.racing = False
            self.finish()

    def finish(self):
        winner = self.order[0]
        if self.bet_kind == "place":
            won = self.pick in self.order[:2]
            odds = self.horses[self.pick]["place"]
        else:
            won = winner == self.pick
            odds = self.horses[self.pick]["odds"]
        if won and odds >= 10:
            self.feat("horses_long")
        if won and self.bet_kind == "win" and self.pick == min(range(N), key=lambda i: self.true_p[i]):
            self.feat("horses_underdog")
        if won:
            self.audio.play("fanfare")
        self.pay(self.pbet, self.pbet * odds if won else 0, label=f"Gana {winner + 1} · {self.horses[winner]['name']}",
                 quiet=won)
        self.done_t = 0.0

    def shadow(self):
        if not hasattr(self, "_shadow"):
            s = pygame.Surface((72, 16), pygame.SRCALPHA)
            for k in range(6):
                pygame.draw.ellipse(s, (0, 0, 0, 22), (k * 3, k, 72 - k * 6, 16 - k * 2))
            self._shadow = s
        return self._shadow

    def draw(self, surf, rect):
        ui = self.ui
        v = self.vis
        track = pygame.Rect(v.x, v.y, v.w, 360)
        ui.push_clip(track)
        surf.blit(gfx.vgradient(track.w, 110, (80, 150, 230, 255), (170, 210, 245, 255)), track.topleft)
        # gradas (paralaje)
        off = -(self.cam * 0.35) % 64
        for k in range(-1, track.w // 64 + 2):
            x = track.x + k * 64 + off
            gfx.rrect(surf, (x, track.y + 40, 60, 60), (70, 60, 90, 255), 6)
            for row in range(3):
                for col in range(6):
                    c = [(230, 80, 90), (250, 210, 80), (90, 160, 240), (240, 240, 240)][(k + row + col) % 4]
                    pygame.draw.circle(surf, c, (int(x + 6 + col * 9), int(track.y + 52 + row * 16)), 3)
        surf.fill((50, 120, 60), (track.x, track.y + 100, track.w, 14))
        # valla
        off2 = -(self.cam * 1.0) % 90
        surf.fill((240, 240, 240), (track.x, track.y + 112, track.w, 5))
        for k in range(-1, track.w // 90 + 2):
            x = track.x + k * 90 + off2
            surf.fill((230, 230, 230), (int(x), track.y + 106, 6, 22))
        # pista
        lane_h = 38
        ty = track.y + 128
        surf.blit(gfx.vgradient(track.w, N * lane_h + 12, (186, 124, 74, 255), (150, 96, 56, 255)), (track.x, ty))
        for i in range(N + 1):
            y = ty + 6 + i * lane_h
            for k in range(-1, track.w // 40 + 2):
                x = track.x + k * 40 + (-(self.cam) % 40)
                pygame.draw.line(surf, (215, 170, 120), (x, y), (x + 20, y), 2)
        # postes de distancia sobre la valla
        for d in POSTS:
            x = track.x + 60 + TRACK_LEN - d - self.cam
            if track.x - 60 < x < track.right + 40:
                surf.fill((240, 240, 240), (int(x) - 2, track.y + 84, 4, 44))
                b = pygame.Rect(0, 0, 40, 20)
                b.midbottom = (int(x), track.y + 88)
                gfx.rrect(surf, b, (250, 250, 250, 255), 4, border=(40, 40, 40), bw=2)
                gfx.text(surf, str(d), b.center, 10, "b", (30, 30, 30), anchor="center", shadow=False)
        # poste de meta (asoma por encima de la valla)
        x = track.x + 60 + TRACK_LEN - self.cam
        if track.x - 60 < x < track.right + 40:
            for k in range(8):
                pygame.draw.rect(surf, (255, 255, 255) if k % 2 == 0 else (20, 20, 20),
                                 (int(x), track.y + 64 + k * 8, 16, 8))
            b = pygame.Rect(0, 0, 54, 22)
            b.midbottom = (int(x) + 8, track.y + 66)
            gfx.rrect(surf, b, (220, 40, 50, 255), 4, border=(40, 20, 20), bw=2)
            gfx.text(surf, "META", b.center, 10, "b", (255, 255, 255), anchor="center", shadow=False)
        # meta y salida
        for xw, chk in ((60, False), (TRACK_LEN + 60, True)):
            x = track.x + xw - self.cam
            if track.x - 60 < x < track.right + 40:
                if chk:
                    for k in range(N * 4):
                        y = ty + 6 + k * lane_h / 4
                        pygame.draw.rect(surf, (255, 255, 255) if k % 2 == 0 else (20, 20, 20), (x, y, 8, lane_h / 4))
                        pygame.draw.rect(surf, (20, 20, 20) if k % 2 == 0 else (255, 255, 255), (x + 8, y, 8, lane_h / 4))
                else:
                    pygame.draw.rect(surf, (255, 255, 255), (x, ty + 6, 4, N * lane_h))
        # caballos
        for i, h in enumerate(self.horses):
            y = ty + 6 + i * lane_h + lane_h / 2
            x = track.x + 60 + h["x"] - self.cam
            frames = art.horse_frames(h["coat"], h["silk"], i + 1, 92)
            speed_k = 14 if self.racing else 0
            fi = int(ui.t * speed_k + i * 1.7) % len(frames) if self.racing else 1
            img = frames[fi]
            surf.blit(self.shadow(), (x - 44, y + 12))
            surf.blit(img, (x - 70, y - 64))
            if self.pick == i:
                gfx.aa_poly(surf, GOLD, [(x - 26, y - 60), (x - 14, y - 60), (x - 20, y - 50)])
        # progreso de la carrera: cuánto falta para la meta
        bar = pygame.Rect(track.x + 16, track.y + 14, track.w - 270, 6)   # termina antes del panel de posiciones
        gfx.rrect(surf, bar.inflate(4, 4), (30, 34, 50, 200), 4)
        for k in range(6):
            pygame.draw.rect(surf, (255, 255, 255) if k % 2 == 0 else (20, 20, 20),
                             (bar.right + 6 + (k % 2) * 6, bar.y - 4 + (k // 2) * 5, 6, 5))
        for i in sorted(range(N), key=lambda i: self.horses[i]["x"]):
            u = min(1.0, self.horses[i]["x"] / TRACK_LEN)
            cx = int(bar.x + u * bar.w)
            pygame.draw.circle(surf, (20, 20, 20), (cx, bar.centery), 6)
            pygame.draw.circle(surf, self.horses[i]["silk"], (cx, bar.centery), 4 if self.pick != i else 5)
        ui.pop_clip()
        pygame.draw.rect(surf, (60, 56, 90), track, 1, border_radius=4)
        # posiciones en directo
        if self.racing or self.order:
            rank = sorted(range(N), key=lambda i: -self.horses[i]["x"])
            if not self.racing and self.order:
                rank = self.order
            pr = pygame.Rect(track.right - 210, track.y + 10, 196, 30 + N * 18)
            gfx.rrect(surf, pr, (10, 10, 20, 200), 10)
            for k, i in enumerate(rank):
                col = self.horses[i]["silk"]
                gfx.circle(surf, (pr.x + 18, pr.y + 18 + k * 18), 6, col)
                gfx.text(surf, f"{k + 1}º  {i + 1} · {self.horses[i]['name']}", (pr.x + 30, pr.y + 10 + k * 18), 12,
                         "b" if i == self.pick else "r", GOLD_HI if i == self.pick else TEXT)
        # tarjetas de caballos
        cy = track.bottom + 14
        cw = (v.w - 5 * 8) // N
        for i, h in enumerate(self.horses):
            r = pygame.Rect(v.x + i * (cw + 8), cy, cw, v.bottom - cy)
            wid = ("horse", i)
            sel = self.pick == i
            hov = ui.hover(r) and not self.racing and not self.order
            hv = ui.anim(wid, 1.0 if (hov or sel) else 0.0)
            gfx.rrect(surf, r, None, 14, border=GOLD if sel else gfx.lerp_col((60, 56, 90), h["silk"], hv), bw=2 if sel else 1,
                      grad=((*gfx.lerp_col((34, 33, 54), gfx.mul_col(h["silk"], 0.45), hv), 255), (22, 22, 36, 255)))
            surf.blit(art.horse_frames(h["coat"], h["silk"], i + 1, 56)[1], (r.x + 2, r.y + 2))
            gfx.text(surf, h["name"], (r.x + 12, r.y + 62), 12, "b", TEXT, max_w=r.w - 20)
            gfx.text(surf, f"x{h['odds']:.1f}", (r.right - 10, r.y + 14), 16, "bl", GOLD_HI, anchor="topright")
            if self.state.lvl("horses_place"):
                gfx.text(surf, f"col x{h['place']:.2f}", (r.x + 12, r.y + 86), 12, "r", MUTED)
            if self.tip == i:
                gfx.text(surf, "soplo", (r.right - 12, r.y + 40), 11, "b", (130, 255, 120), anchor="topright")
                gfx.aa_poly(surf, (130, 255, 120), gfx.star_points(r.right - 52, r.y + 48, 6, 2.5))
            if hov:
                ui.hot_any = True
                if ui.pressed:
                    ui.active = wid
                if ui.released and ui.active == wid and not sel:
                    self.pick = i
                    self.audio.play("ui")
        # controles
        c = self.controls_rect(rect)
        controls_bg(surf, c)
        self.bet_control(surf, c.x + 16, c.y + 12)
        keys = ui.keys if not ui.focus else []
        free = not self.racing and not self.order
        place = bool(self.state.lvl("horses_place"))
        ix, iw = c.x + 372, c.right - 220 - (c.x + 372)
        if place:
            self.kind = ui.segmented("hkind", (ix, c.y + 14, iw, 36), ["Ganador", "Colocado"],
                                     getattr(self, "kind", 0), 12) if free else getattr(self, "kind", 0)
        ty = c.y + 58 if place else c.y + 16
        if self.pick is not None:
            h = self.horses[self.pick]
            odds = h['place'] if (getattr(self, "kind", 0) == 1 and place) else h['odds']
            if not place:
                gfx.text(surf, "TU CABALLO", (ix, ty), 12, "b", MUTED)
                ty += 22
            gfx.text(surf, f"{self.pick + 1} · {h['name']}", (ix, ty), 14, "bl", h["silk"], max_w=iw)
            gfx.text(surf, f"paga x{odds:.2f} → {fmt_money(self.bet * odds)}", (ix, ty + 24), 12, "b", GOLD_HI,
                     max_w=iw)
        else:
            gfx.text(surf, "Elige un caballo", (ix, ty + (10 if place else 28)), 14, "b", MUTED, max_w=iw)
        pill = self.hint_pill(surf, v.x + 16, v.y + 16, 280)
        if pill and self.hint_ready() and self.tip is None and free:
            if ui.button("hint", (pill.right + 10, pill.y - 6, 150, 44), "Pedir soplo", "gold", size=12):
                self.ask_tip()
        if self.tip is not None and free:
            gfx.wavy_text(surf, f"Soplo: «el {self.tip + 1} está en forma»", (v.centerx, v.y + 40), 14, GOLD_HI,
                          self.t, 2, 5)
        can = not self.racing and not self.order and self.pick is not None
        if ui.button("go", (c.right - 200, c.y + 18, 180, 64), "¡A CORRER!", "green", enabled=can, size=19,
                     sound=None) or (can and pygame.K_SPACE in keys):
            self.start()
