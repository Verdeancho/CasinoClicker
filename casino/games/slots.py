import math
import random

import pygame

from .base import BaseGame
from .common import dark_panel, controls_bg, toggle_pill
from .. import gfx, art
from ..fmt import fmt_money
from ..gfx import TEXT, MUTED, DIM, GOLD, GOLD_HI, GREEN, RED

SYMBOLS = ["cherry", "lemon", "orange", "plum", "bell", "bar", "seven", "star", "wild"]
WEIGHTS = {"cherry": 7, "lemon": 7, "orange": 6, "plum": 5, "bell": 4, "bar": 3, "seven": 2, "star": 1, "wild": 0.25}
PAY3 = {"cherry": 15, "lemon": 20, "orange": 25, "plum": 30, "bell": 60, "bar": 100, "seven": 250, "star": 750}
PAY_CHERRY2 = 3
PAY_CHERRY1 = 1


def _line_rtp(weights, pay3, c2, c1):
    import itertools
    syms = list(weights)
    tw = sum(weights.values())
    total = 0.0
    for a, b, c in itertools.product(syms, repeat=3):
        p = weights[a] * weights[b] * weights[c] / tw ** 3
        real = [x for x in (a, b, c) if x != "wild"]
        if not real:
            m = pay3["star"]
        elif all(x == real[0] or x == "wild" for x in (a, b, c)):
            m = pay3[real[0]]
        elif a == "cherry" and b == "cherry":
            m = c2
        elif a == "cherry":
            m = c1
        else:
            m = 0
        total += p * m
    return total
NAMES = {"cherry": "Cerezas", "lemon": "Limones", "orange": "Naranjas", "plum": "Uvas", "bell": "Campanas",
         "bar": "BAR", "seven": "¡Sietes!", "star": "¡Estrellas!", "wild": "¡WILD!"}
LINES = [(1, 1, 1), (0, 0, 0), (2, 2, 2), (0, 1, 2), (2, 1, 0)]
LINE_COLORS = [(255, 210, 80), (90, 170, 255), (255, 150, 60), (80, 230, 150), (255, 110, 190)]
REEL_W, ROW_H, SYM = 146, 112, 100


# Con el comodín la tabla se reescala para mantener el mismo retorno (el comodín da emoción, no ventaja)
_W_NO = {k: v for k, v in WEIGHTS.items() if k != "wild"}
_BASE_RTP = _line_rtp(_W_NO, PAY3, PAY_CHERRY2, PAY_CHERRY1)
_WILD_SCALE = _BASE_RTP / _line_rtp(WEIGHTS, PAY3, PAY_CHERRY2, PAY_CHERRY1)
PAY3_WILD = {k: round(v * _WILD_SCALE, 1) for k, v in PAY3.items()}


def evaluate_line(a, b, c, wild=False):
    pay3 = PAY3_WILD if wild else PAY3
    k = _WILD_SCALE if wild else 1.0
    syms = [a, b, c]
    real = [s for s in syms if s != "wild"]
    if not real:
        return pay3["star"], "wild"
    s = real[0]
    if all(x == s or x == "wild" for x in syms):
        return pay3[s], s
    if a == "cherry" and b == "cherry":
        return PAY_CHERRY2 * k, "cherry2"
    if a == "cherry":
        return PAY_CHERRY1 * k, "cherry1"
    return 0, None


_blur = {}


def blurred(name):
    if name not in _blur:
        base = art.symbol(name, SYM)
        s = pygame.Surface((SYM, SYM + 40), pygame.SRCALPHA)
        for k in range(7):
            tmp = base.copy()
            tmp.set_alpha(60)
            s.blit(tmp, (0, k * 6))
        _blur[name] = pygame.transform.smoothscale(s, (SYM, SYM))
    return _blur[name]


class Reel:
    def __init__(self, syms):
        self.strip = list(syms)
        self.pos = 0.0
        self.t = 0.0
        self.dur = 1.0
        self.target = 0
        self.spinning = False
        self.last_idx = 0
        self.speed = 0.0

    def visible(self):
        i = int(round(self.pos))
        return [self.strip[(i + k) % len(self.strip)] for k in range(3)]

    def start(self, final, rand, n, dur):
        vis = self.visible()
        self.strip = vis + [rand() for _ in range(n)] + list(final) + [rand(), rand()]
        self.pos = 0.0
        self.target = len(self.strip) - 5
        self.t = 0.0
        self.dur = dur
        self.spinning = True
        self.last_idx = 0

    def update(self, dt):
        """Devuelve (paso_de_símbolo, se_ha_parado)."""
        if not self.spinning:
            return False, False
        self.t += dt
        u = min(1.0, self.t / self.dur)
        old = self.pos
        if u < 0.08:
            self.pos = -0.22 * math.sin(u / 0.08 * math.pi)
        else:
            v = (u - 0.08) / 0.92
            over = 0.32
            if v < 0.88:
                self.pos = (self.target + over) * gfx.ease_out_cubic(v / 0.88)
            else:
                k = (v - 0.88) / 0.12
                self.pos = self.target + over - over * gfx.ease_out_back(k, 2.2)
        self.speed = abs(self.pos - old) / dt if dt else 0
        tick = int(math.floor(self.pos)) != self.last_idx
        self.last_idx = int(math.floor(self.pos))
        if u >= 1.0:
            self.pos = float(self.target)
            self.spinning = False
            return tick, True
        return tick, False


class Slots(BaseGame):
    gid = "slots"

    def setup(self):
        self.lines = 5
        self.auto = False
        self.reels = [Reel([self.rand_symbol() for _ in range(3)]) for _ in range(3)]
        self.spinning = False
        self.pending_bet = 0.0
        self.winning = []
        self.win_cells = set()
        self.win_t = 0.0
        self._overlay = None
        self.last_win = None

    def rand_symbol(self):
        syms = [s for s in SYMBOLS if s != "wild" or self.state.lvl("slots_wild")]
        return random.choices(syms, weights=[WEIGHTS[s] for s in syms])[0]

    def spin(self):
        if self.spinning:
            return
        if not self.take_bet(self.bet):
            self.auto = False
            return
        self.pending_bet = self.bet
        self.spinning = True
        self.winning = []
        self.win_cells = set()
        fast = self.auto
        self.audio.play("spin_start")
        for r, reel in enumerate(self.reels):
            final = [self.rand_symbol() for _ in range(3)]
            dur = (0.75 + r * 0.22) if fast else (1.25 + r * 0.38)
            reel.start(final, self.rand_symbol, 16 + r * 7, dur)

    def update(self, dt):
        self.win_t += dt
        if not self.spinning:
            return
        all_stopped = True
        for r, reel in enumerate(self.reels):
            was = reel.spinning
            tick, stopped = reel.update(dt)
            if tick and reel.spinning:
                self.audio.play("reel_tick", 0.7, pan=(r - 1) * 0.4, throttle=0.035)
            if stopped and was:
                self.audio.play("reel_stop", pan=(r - 1) * 0.5, throttle=0.0)
            if reel.spinning:
                all_stopped = False
        if all_stopped:
            self.spinning = False
            self.finish()

    def finish(self):
        bet = self.pending_bet
        per_line = bet / self.lines
        grid = [reel.visible() for reel in self.reels]
        total = 0.0
        best = None
        jackpot = False
        for i in range(self.lines):
            rows = LINES[i]
            a, b, c = (grid[r][rows[r]] for r in range(3))
            m, sym = evaluate_line(a, b, c, bool(self.state.lvl("slots_wild")))
            if m > 0:
                total += m * per_line
                self.winning.append(i)
                cells = [(r, rows[r]) for r in range(3)] if sym not in ("cherry1", "cherry2") else \
                    [(r, rows[r]) for r in range(1 if sym == "cherry1" else 2)]
                self.win_cells.update(cells)
                if best is None or m > best[0]:
                    best = (m, sym)
                if sym == "seven":
                    self.feat("slots_777")
                if i == 0 and a == b == c == "star" and self.state.lvl("slots_jackpot"):
                    jackpot = True
        self.win_t = 0.0
        label = None
        if best:
            label = NAMES.get(best[1], "Cerezas")
        mr = self.machine_rect()
        self.last_win = total
        self.pay(bet, total, label=label, pos=(mr.centerx, mr.y + 90))
        if total > bet * 5:
            self.fx.coins(mr.centerx, mr.y + 120, 24, 1.4, 22)
        if jackpot and self.state.jackpot > 0:
            pot = self.state.jackpot
            self.state.jackpot = 0
            self.state.earn(pot, "jackpot")
            self.state.set_flag("slots_jackpot")
            self.show(f"¡¡¡BOTE!!!  +{fmt_money(pot)}", GOLD, big=True)
            self.audio.play("win3")
            self.fx.confetti(mr.centerx, mr.y, 200, w=mr.w)
            self.fx.coins(mr.centerx, mr.y + 100, 50, 1.8, 24)
            self.app.log(f"¡BOTE PROGRESIVO! Ganas {fmt_money(pot)}", GOLD)
        if self.auto:
            self.later(0.55 if self.winning else 0.25, lambda: self.auto and self.spin())

    # ---------------------------------------------------------------- dibujo
    def machine_rect(self):
        v = self.vis
        return pygame.Rect(v.x, v.y, 540, v.h)

    def reel_origin(self):
        mr = self.machine_rect()
        total_w = 3 * REEL_W + 2 * 10
        return mr.x + (mr.w - total_w) // 2, mr.y + 100

    def overlay(self):
        if self._overlay is None:
            h = ROW_H * 3
            s = pygame.Surface((REEL_W, h), pygame.SRCALPHA)
            for y in range(h):
                d = abs(y - h / 2) / (h / 2)
                a = int(min(200, (d ** 3) * 230))
                pygame.draw.line(s, (0, 0, 0, a), (0, y), (REEL_W, y))
            self._overlay = s
        return self._overlay

    def draw(self, surf, rect):
        ui = self.ui
        mr = self.machine_rect()
        t = self.ui.t
        gfx.shadow(surf, mr, 26, 16, 140, (0, 10))
        gfx.rrect(surf, mr, None, 26, border=(255, 200, 90), bw=3, grad=((120, 32, 80, 255), (48, 10, 36, 255)))
        # luces que recorren el marco
        pts = []
        per = 2 * (mr.w + mr.h)
        n = 40
        for i in range(n):
            d = i / n * per
            if d < mr.w:
                p = (mr.x + d, mr.y + 8)
            elif d < mr.w + mr.h:
                p = (mr.right - 8, mr.y + d - mr.w)
            elif d < 2 * mr.w + mr.h:
                p = (mr.right - (d - mr.w - mr.h), mr.bottom - 8)
            else:
                p = (mr.x + 8, mr.bottom - (d - 2 * mr.w - mr.h))
            pts.append(p)
        speed = 14 if self.spinning else 5
        for i, p in enumerate(pts):
            lit = (int(t * speed) - i) % 4 == 0 or (self.winning and self.win_t < 3 and int(t * 8) % 2 == 0)
            col = (255, 240, 170) if lit else (120, 70, 40)
            if lit:
                gfx.glow(surf, p, 14, (255, 200, 90), 0.8)
            gfx.circle(surf, p, 4, col)
        # marquesina
        mq = pygame.Rect(mr.x + 30, mr.y + 22, mr.w - 60, 62)
        gfx.rrect(surf, mq, None, 16, border=(255, 210, 100), bw=2, grad=((60, 10, 30, 255), (30, 4, 16, 255)))
        gfx.text(surf, "MEGA  SLOTS", (mq.centerx, mq.y + 22), 26, "bl", GOLD_HI, anchor="center", shadow=2)
        if self.state.lvl("slots_jackpot"):
            gfx.text(surf, f"BOTE  {fmt_money(self.state.jackpot)}", (mq.centerx, mq.y + 48), 14, "b",
                     (255, 236, 120), anchor="center")
        else:
            gfx.text(surf, "3 iguales en una línea = premio", (mq.centerx, mq.y + 48), 12, "sb", (230, 180, 200),
                     anchor="center")
        # rodillos
        x0, y0 = self.reel_origin()
        win_rect = pygame.Rect(x0 - 12, y0 - 12, 3 * REEL_W + 20 + 24, ROW_H * 3 + 24)
        gfx.rrect(surf, win_rect, (14, 6, 18, 255), 16, border=(200, 150, 80), bw=2)
        self.ui.push_clip(pygame.Rect(x0, y0, 3 * REEL_W + 20, ROW_H * 3))
        pulse = 1 + 0.07 * math.sin(self.win_t * 9) if self.win_cells and self.win_t < 4 else 1
        for r, reel in enumerate(self.reels):
            rx = x0 + r * (REEL_W + 10)
            col_rect = pygame.Rect(rx, y0, REEL_W, ROW_H * 3)
            surf.blit(gfx.vgradient(REEL_W, ROW_H * 3, (250, 246, 232, 255), (226, 218, 196, 255)), col_rect.topleft)
            base = math.floor(reel.pos)
            frac = reel.pos - base
            fast = reel.speed > 9
            for k in range(-1, 4):
                idx = base + k
                sym = reel.strip[idx % len(reel.strip)]
                cy = y0 + (k - frac) * ROW_H + ROW_H / 2
                row = k if frac < 1e-6 else None
                img = blurred(sym) if fast else art.symbol(sym, SYM)
                if not reel.spinning and row is not None and (r, row) in self.win_cells:
                    gfx.glow(surf, (rx + REEL_W / 2, cy), 70, LINE_COLORS[0], 0.35)
                    img = gfx.scaled(img, pulse)
                gfx.blit_center(surf, img, (rx + REEL_W / 2, cy))
            surf.blit(self.overlay(), col_rect.topleft)
        self.ui.pop_clip()
        # líneas ganadoras
        if not self.spinning and self.winning:
            prog = min(1.0, self.win_t / 0.35)
            for li in self.winning:
                rows = LINES[li]
                pts = [(x0 - 6, y0 + rows[0] * ROW_H + ROW_H / 2)]
                for r in range(3):
                    pts.append((x0 + r * (REEL_W + 10) + REEL_W / 2, y0 + rows[r] * ROW_H + ROW_H / 2))
                pts.append((x0 + 3 * REEL_W + 26, y0 + rows[2] * ROW_H + ROW_H / 2))
                total = sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
                want = total * prog
                out = [pts[0]]
                acc = 0
                for a, b in zip(pts, pts[1:]):
                    d = math.dist(a, b)
                    if acc + d <= want:
                        out.append(b)
                        acc += d
                    else:
                        k = (want - acc) / d
                        out.append((a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k))
                        break
                col = LINE_COLORS[li]
                gfx.thick_aaline(surf, (*col, 90), out, 12)
                gfx.thick_aaline(surf, col, out, 5)
        # pantalla LED inferior
        led = pygame.Rect(mr.x + 70, y0 + ROW_H * 3 + 30, mr.w - 140, 50)
        gfx.rrect(surf, led, (6, 10, 8, 255), 12, border=(200, 150, 80), bw=2)
        if self.spinning:
            msg, col = "· · · GIRANDO · · ·", (120, 255, 160)
        elif self.last_win:
            msg, col = f"PREMIO  {fmt_money(self.last_win)}", (255, 220, 90)
        elif self.last_win == 0:
            msg, col = "¡SUERTE EN LA PRÓXIMA!", (120, 200, 255)
        else:
            msg, col = "PULSA GIRAR O ESPACIO", (120, 255, 160)
        blink = 1.0 if not (self.last_win and self.win_t < 2.5) else (0.6 + 0.4 * abs(math.sin(self.win_t * 6)))
        gfx.glow(surf, led.center, 120, gfx.mul_col(col, 0.3), 0.3 * blink)
        gfx.text(surf, msg, led.center, 14, "b", gfx.mul_col(col, blink), anchor="center", max_w=led.w - 16)
        # indicadores de línea
        for i, rows in enumerate(LINES):
            active = i < self.lines
            col = LINE_COLORS[i] if active else (70, 50, 70)
            if i < 3:
                p = (x0 - 26, y0 + rows[0] * ROW_H + ROW_H / 2)
            else:
                p = (x0 + 3 * REEL_W + 46, y0 + rows[2] * ROW_H + ROW_H / 2 + (-14 if i == 3 else 14))
            gfx.circle(surf, p, 11, col)
            gfx.text(surf, str(i + 1), p, 12, "bl", (30, 10, 20), anchor="center")
        # panel de premios
        pr = pygame.Rect(mr.right + 12, self.vis.y, self.vis.right - mr.right - 12, self.vis.h)
        dark_panel(surf, pr, 18)
        gfx.text(surf, "PREMIOS", (pr.x + 18, pr.y + 14), 15, "bl", GOLD)
        gfx.text(surf, "x apuesta/línea", (pr.right - 16, pr.y + 18), 10, "r", MUTED, anchor="topright")
        y = pr.y + 46
        table = PAY3_WILD if self.state.lvl("slots_wild") else PAY3
        for sym, m in sorted(table.items(), key=lambda kv: -kv[1]):
            for k in range(3):
                surf.blit(art.symbol(sym, 34), (pr.x + 14 + k * 36, y))
            gfx.text(surf, f"x{m}", (pr.right - 18, y + 17), 17, "num", GOLD_HI if m >= 250 else TEXT,
                     anchor="midright")
            if sym == "star" and self.state.lvl("slots_jackpot"):
                gfx.text(surf, "+BOTE", (pr.x + 128, y + 17), 12, "b", (255, 236, 120), anchor="midleft")
            y += 40
        for n, m in ((2, PAY_CHERRY2), (1, PAY_CHERRY1)):
            for k in range(n):
                surf.blit(art.symbol("cherry", 34), (pr.x + 14 + k * 36, y))
            gfx.text(surf, f"x{m}", (pr.right - 18, y + 17), 17, "num", TEXT, anchor="midright")
            y += 40
        if self.state.lvl("slots_wild"):
            surf.blit(art.symbol("wild", 40), (pr.x + 12, y - 2))
            gfx.text(surf, "sustituye a cualquiera", (pr.x + 60, y + 18), 12, "sb", MUTED, anchor="midleft")
        # controles
        c = self.controls_rect(rect)
        controls_bg(surf, c)
        self.bet_control(surf, c.x + 16, c.y + 12, "APUESTA TOTAL")
        gfx.text(surf, "LÍNEAS", (c.x + 380, c.y + 12), 12, "b", MUTED)
        sel = ui.segmented("slot_lines", (c.x + 380, c.y + 32, 150, 40), ["1", "3", "5"], [1, 3, 5].index(self.lines),
                           15)
        if not self.spinning:
            self.lines = [1, 3, 5][sel]
        self.auto = toggle_pill(ui, ("slots", "auto"), surf, (c.x + 550, c.y + 37, 110, 30), "Auto", self.auto)
        if ui.button("spin", (c.right - 200, c.y + 18, 180, 64), "GIRAR", "red", enabled=not self.spinning, size=22,
                     sound=None) or (pygame.K_SPACE in ui.keys and not ui.focus and not self.spinning):
            self.spin()

    def on_hide(self):
        self.auto = False
