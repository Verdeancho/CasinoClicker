import math
import random
import time

import pygame

from .base import BaseGame
from .common import dark_panel, controls_bg, history_pills, toggle_pill
from .. import gfx, art
from ..fmt import fmt_money, fmt_num, parse_amount
from ..gfx import TEXT, MUTED, DIM, GOLD, GOLD_HI, GREEN, RED, ORANGE

EDGE = 0.97
GROWTH = 0.12
MILESTONES = [1.5, 2, 3, 5, 10, 20, 50, 100, 250, 500, 1000, 5000]


def crash_point():
    cp = EDGE / (1 - random.random())
    return 1.0 if cp < 1.0 else min(math.floor(cp * 100) / 100, 10_000.0)


class Crash(BaseGame):
    gid = "crash"

    def setup(self):
        self.running = False
        self.cashed = False
        self.crashed = False
        self.pbet = 0.0
        self.cp = 1.0
        self.t = 0.0
        self.rt = 0.0
        self.mult = 1.0
        self.cash_mult = None
        self.hist = []
        self.points = []
        self.auto_on = False
        self.auto_text = "2.00"
        self.repeat = False
        self.next_ms = 0
        self.stars = [(random.uniform(0, 1), random.uniform(0, 1), random.uniform(0.3, 1.0)) for _ in range(90)]
        self.star_off = 0.0
        self.crash_t = 0.0
        self.forced = None
        self.tip = None

    def start(self):
        if self.running:
            return
        if not self.take_bet(self.bet):
            self.repeat = False
            return
        self.pbet = self.bet
        self.hack = self.use_cheat()
        if self.hack:
            cp = crash_point()
            while cp < 1.5:
                cp = crash_point()
            self.cp = cp
        else:
            self.cp = self.forced if self.forced is not None else crash_point()
        self.forced = None
        self.tip = None
        self.running = True
        self.cashed = False
        self.crashed = False
        self.cash_mult = None
        self.mult = 1.0
        self.rt = 0.0
        self.points = [(0.0, 1.0)]
        self.next_ms = 0
        self.banner = None
        self.audio.play("spin_start")
        self.audio.play_loop("crash_sweep")

    def auto_target(self):
        if not (self.auto_on and self.state.lvl("crash_auto")):
            return None
        v = parse_amount(self.auto_text)
        return v if v and v >= 1.01 else None

    def update(self, dt):
        self.star_off += dt * (0.02 + (math.log(self.mult) * 0.05 if self.running else 0.005))
        if self.crashed:
            self.crash_t += dt
        if not self.running:
            return
        self.rt += dt
        m = math.exp(GROWTH * self.rt)
        target = self.auto_target()
        if getattr(self, "hack", False) and not self.cashed and m >= self.cp - 0.1:
            self.mult = max(1.01, self.cp - 0.1)
            self.hack = False
            self.cashout()
        if target and not self.cashed and m >= target and target <= self.cp:
            self.mult = target
            self.cashout()
        if m >= self.cp:
            self.mult = self.cp
            self.points.append((math.log(max(self.cp, 1.0)) / GROWTH, self.cp))
            self.explode()
            return
        self.mult = m
        self.points.append((self.rt, m))
        while self.next_ms < len(MILESTONES) and m >= MILESTONES[self.next_ms]:
            self.audio.play(f"blip{min(11, self.next_ms)}", 0.9)
            self.next_ms += 1
        # llama del cohete
        tip = self.tip_pos()
        if tip and random.random() < 0.9:
            ang = self.tip_angle()
            bx = tip[0] - math.cos(ang) * 26
            by = tip[1] + math.sin(ang) * 26
            self.fx.p.append({"k": "spark", "x": bx, "y": by, "vx": -math.cos(ang) * 120 + random.uniform(-30, 30),
                              "vy": math.sin(ang) * 120 + random.uniform(-30, 30), "life": 0.35, "age": 0, "g": 0,
                              "size": 8, "col": random.choice([(255, 170, 60), (255, 120, 40), (255, 220, 120)]),
                              "drag": 3})

    def cashout(self):
        if not self.running or self.cashed:
            return
        self.cashed = True
        self.cash_mult = self.mult
        self.audio.play("cashout")
        tip = self.tip_pos() or self.vis.center
        self.pay(self.pbet, self.pbet * self.mult, label=f"Retirado en x{self.mult:.2f}", quiet=True, pos=tip)
        if self.mult >= 10:
            self.feat("crash_10")
        if self.mult >= 50:
            self.feat("crash_50")
        if self.mult >= 100:
            self.feat("crash_100")

    def explode(self):
        self.running = False
        self.crashed = True
        self.crash_t = 0.0
        self.audio.stop_loop(80)
        self.audio.play("explode")
        tip = self.tip_pos()
        if tip:
            self.fx.flash(tip[0], tip[1], 140, (255, 150, 60))
            self.fx.sparks(tip[0], tip[1], 60, (255, 150, 60), 2.0, 12, 0.9)
            self.fx.add_shake(7)
        self.hist.append((f"x{fmt_num(self.cp)}", RED if self.cp < 2 else (GREEN if self.cp < 10 else GOLD)))
        if not self.cashed:
            self.pay(self.pbet, 0, label=f"Explota en x{self.cp:.2f}", quiet=True)
        if self.repeat and self.state.lvl("crash_auto"):
            self.later(2.0, lambda: (not self.running) and self.repeat and self.start())

    # ------------------------------------------------------------- gráfico
    def graph_rect(self):
        v = self.vis
        return pygame.Rect(v.x + 70, v.y + 70, v.w - 100, v.h - 110)

    def scales(self):
        t = self.points[-1][0] if self.points else 0
        return max(8.0, t * 1.12), max(2.0, self.mult * 1.18)

    def to_xy(self, t, m):
        g = self.graph_rect()
        tmax, mmax = self.scales()
        return g.x + g.w * t / tmax, g.bottom - g.h * (m - 1) / (mmax - 1)

    def tip_pos(self):
        if len(self.points) < 1:
            return None
        return self.to_xy(*self.points[-1])

    def tip_angle(self):
        if len(self.points) < 3:
            return 0.3
        a = self.to_xy(*self.points[-3])
        b = self.to_xy(*self.points[-1])
        return math.atan2(a[1] - b[1], b[0] - a[0])

    def draw(self, surf, rect):
        ui = self.ui
        v = self.vis
        dark_panel(surf, v, 20, (14, 12, 34), (6, 6, 16), (50, 46, 90))
        # estrellas con paralaje
        ui.push_clip(v.inflate(-4, -4))
        for (sx, sy, d) in self.stars:
            x = v.x + ((sx - self.star_off * d) % 1.0) * v.w
            y = v.y + ((sy + self.star_off * d * 0.6) % 1.0) * v.h
            b = int(90 + 140 * d)
            surf.fill((b, b, min(255, b + 30)), (int(x), int(y), 2 if d > 0.7 else 1, 2 if d > 0.7 else 1))
        g = self.graph_rect()
        tmax, mmax = self.scales()
        # rejilla
        span = mmax - 1
        raw = span / 5
        mag = 10 ** math.floor(math.log10(raw)) if raw > 0 else 0.1
        step = min((s * mag for s in (1, 2, 5, 10) if s * mag >= raw), default=mag)
        val = 1.0
        while val <= mmax:
            _, y = self.to_xy(0, val)
            pygame.draw.line(surf, (30, 30, 56), (g.x, y), (g.right, y))
            gfx.text(surf, f"x{fmt_num(val, 1)}", (g.x - 10, y), 11, "sb", DIM, anchor="midright")
            val += step
        ss = max(1, int(tmax / 8))
        for sec in range(0, int(tmax) + 1, ss):
            x, _ = self.to_xy(sec, 1)
            gfx.text(surf, f"{sec}s", (x, g.bottom + 8), 11, "sb", DIM, anchor="midtop")
        pygame.draw.line(surf, (70, 66, 110), (g.x, g.bottom), (g.right, g.bottom), 2)
        # curva
        if len(self.points) >= 2:
            stride = max(1, len(self.points) // 160)
            pts = [self.to_xy(t, m) for t, m in self.points[::stride]] + [self.to_xy(*self.points[-1])]
            col = RED if self.crashed and not self.cashed else (GREEN if self.cashed else ORANGE)
            poly = [(g.x, g.bottom)] + pts + [(pts[-1][0], g.bottom)]
            fill = pygame.Surface(v.size, pygame.SRCALPHA)
            gfx.aa_poly(fill, (*col, 50), [(x - v.x, y - v.y) for x, y in poly])
            surf.blit(fill, v.topleft)
            gfx.thick_aaline(surf, (*col, 70), pts, 12)
            gfx.thick_aaline(surf, col, pts, 5)
            if self.cash_mult:
                cx_, cy_ = self.to_xy(math.log(self.cash_mult) / GROWTH, self.cash_mult)
                gfx.circle(surf, (cx_, cy_), 8, GREEN, border=(255, 255, 255), bw=2)
                gfx.text(surf, f"x{self.cash_mult:.2f}", (cx_ + 10, cy_ - 22), 13, "b", GREEN)
            tip = pts[-1]
            if not self.crashed:
                ang = math.degrees(self.tip_angle())
                rk = pygame.transform.rotozoom(art.rocket(60), ang - 90, 1.0)
                gfx.glow(surf, tip, 50, (255, 160, 60), 0.5)
                surf.blit(rk, rk.get_rect(center=(int(tip[0]), int(tip[1]))))
        ui.pop_clip()
        # multiplicador
        cxm, cym = v.centerx, v.y + 130
        if self.crashed:
            k = gfx.ease_out_back(min(1, self.crash_t / 0.4))
            img = gfx.text_surf(f"x{self.mult:.2f}", 60, "num", RED)
            gfx.blit_center(surf, gfx.scaled(img, max(0.05, k)), (cxm, cym))
            gfx.text(surf, "¡CRASH!", (cxm, cym - 56), 22, "bl", RED, anchor="center")
        elif self.running or self.points:
            col = GREEN if self.cashed else gfx.lerp_col(TEXT, GOLD_HI, min(1, math.log(self.mult) / 2.3))
            pulse = 1 + 0.05 * math.sin(ui.t * 10) if self.running else 1
            gfx.blit_center(surf, gfx.scaled(gfx.text_surf(f"x{self.mult:.2f}", 64, "num", col), pulse), (cxm, cym))
            if self.cashed:
                gfx.text(surf, f"Retirado en x{self.cash_mult:.2f}", (cxm, cym + 50), 15, "b", GREEN, anchor="center")
        else:
            gfx.text(surf, "Pulsa APOSTAR para despegar", (cxm, cym), 22, "b", MUTED, anchor="center")
        history_pills(surf, v.right - 16, v.y + 14, self.hist, 10, 62, 24, right_to_left=True)
        pill = self.hint_pill(surf, v.x + 16, v.y + 14, 280)
        if pill and self.hint_ready() and self.tip is None and not self.running:
            if ui.button("hint", (pill.right + 10, pill.y - 6, 150, 44), "Intuir", "gold", size=12):
                self.use_hint()
                self.forced = crash_point()
                over = self.forced >= 2
                said = over if random.random() < self.reliable(0.70) else not over
                self.tip = "pasará de x2" if said else "explotará antes de x2"
        self.cheat_pill(surf, v.x + 16, v.y + 54, 280)
        if self.tip:
            gfx.wavy_text(surf, f"Intuyes que el cohete {self.tip}", (v.centerx, v.y + 70), 14, GOLD_HI, self.t, 2, 5)
        # controles
        c = self.controls_rect(rect)
        controls_bg(surf, c)
        self.bet_control(surf, c.x + 16, c.y + 12)
        has_auto = bool(self.state.lvl("crash_auto"))
        ax = c.x + 380
        gfx.text(surf, "AUTO-RETIRO" if has_auto else "AUTO-RETIRO (mejora)", (ax, c.y + 12), 12, "b",
                 MUTED if has_auto else DIM)
        if has_auto:
            focused = ui.focus == ("crash", "auto")
            txt, done = ui.text_input(("crash", "auto"), (ax, c.y + 30, 90, 40), self.auto_text, size=18)
            if focused or done:
                self.auto_text = txt
            if done and parse_amount(self.auto_text) is None:
                self.auto_text = "2.00"
            self.auto_on = toggle_pill(ui, ("crash", "aon"), surf, (ax + 104, c.y + 26, 100, 24), "Activar",
                                       self.auto_on)
            self.repeat = toggle_pill(ui, ("crash", "rep"), surf, (ax + 104, c.y + 56, 100, 24), "Repetir",
                                      self.repeat)
        keys = ui.keys if not ui.focus else []
        if self.running and not self.cashed:
            if ui.button("cash", (c.right - 220, c.y + 18, 200, 64), "RETIRAR", "gold", size=20,
                         sub=fmt_money(self.pbet * self.mult), sound=None) or pygame.K_SPACE in keys:
                self.cashout()
        else:
            if ui.button("start", (c.right - 220, c.y + 18, 200, 64), "APOSTAR", "green", enabled=not self.running,
                         size=20, sound=None) or (pygame.K_SPACE in keys and not self.running):
                self.start()

    def on_hide(self):
        self.repeat = False
