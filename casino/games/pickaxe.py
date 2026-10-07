"""Pico Minero: un rodillo decide si cae pico (y de qué material); el pico baja por un pozo de bloques, pica menas y
mejora hasta romperse. La física y las reglas están en pickaxe_logic."""
import math
import os
import random

import pygame

from .base import BaseGame
from .common import controls_bg, felt
from . import pickaxe_logic as L
from .. import gfx
from ..fmt import fmt_money, fmt_num, fmt_time
from ..gfx import TEXT, MUTED, DIM, GOLD, GOLD_HI, GREEN, RED, INK

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "pickaxe")
SPEEDS = (1, 2, 4)
PACKS = (10, 25, 50, 100)     # las tiradas se compran por paquetes
REEL_TIME = 1.3
ORE_COL = {"coal": (90, 90, 96), "redstone": (255, 40, 40), "gold": (255, 214, 60), "diamond": (90, 240, 236),
           "emerald": (60, 230, 110), "diamond_block": (90, 240, 236), "emerald_block": (60, 230, 110)}
TEX = {"grass": "grass", "dirt": "dirt", "tnt": "tnt", "arrow": "arrow", "bench": "bench", "slime": "slime",
       "diamond_block": "diamond_block", "emerald_block": "emerald_block"}
_raw = {}
_cache = {}


def tex(name, size):
    """Textura 16x16 de casino/assets/pickaxe escalada sin suavizado."""
    key = (name, size)
    s = _cache.get(key)
    if s is None:
        raw = _raw.get(name)
        if raw is None:
            raw = pygame.image.load(os.path.join(ASSETS, name + ".png")).convert_alpha()
            _raw[name] = raw
        s = pygame.transform.scale(raw, (size, size))
        _cache[key] = s
    return s


def block_tex(kind, row):
    deep = row >= L.DEEP_ROW
    if kind == "stone":
        return "deep_stone" if deep else "stone"
    if kind in ("coal", "redstone", "gold", "diamond", "emerald"):
        return ("deep_" if deep else "") + kind + "_ore"
    return TEX[kind]


def well_color(y):
    """Fondo del pozo: cielo arriba que se oscurece al bajar."""
    stops = [(-6, (120, 186, 236)), (0, (98, 160, 220)), (20, (44, 72, 132)), (90, (16, 22, 46)), (300, (6, 8, 16))]
    for (y0, c0), (y1, c1) in zip(stops, stops[1:]):
        if y <= y1:
            t = max(0.0, (y - y0) / (y1 - y0))
            return gfx.lerp_col(c0, c1, t)
    return stops[-1][1]


def nothing_icon(size):
    key = ("nothing", size)
    s = _cache.get(key)
    if s is None:
        s = tex("deep_stone", size).copy()
        k = max(2, size // 8)
        pygame.draw.line(s, (230, 60, 60), (k * 2, k * 2), (size - k * 2, size - k * 2), k)
        pygame.draw.line(s, (230, 60, 60), (size - k * 2, k * 2), (k * 2, size - k * 2), k)
        _cache[key] = s
    return s


class Pickaxe(BaseGame):
    gid = "pickaxe"

    def setup(self):
        self.run = None
        self.run_bet = 0.0
        self.speed = 2
        self.pack_n = PACKS[0]        # tamaño del paquete que se va a comprar
        self.paused = False
        self.recent = []
        self.cam = -6.0
        self.use_netherite = False
        self.floaters = []
        self.reel = None
        if self.pack:                 # paquete a medias de otra sesión: se reanuda con SEGUIR
            self.bet = self.pack["bet"]
            self.paused = True

    # ------------------------------------------------------------- ronda
    def busy_now(self):
        return bool(self.reel or (self.run and not self.run.done))

    @property
    def crosses(self):
        """Cruces seguidas (a la 8.ª tirada, pico seguro). Se guarda en la partida para que la garantía no se pierda."""
        return self.state.flags.get("pick_crosses", 0)

    @crosses.setter
    def crosses(self, n):
        self.state.flags["pick_crosses"] = n

    @property
    def pack(self):
        """Paquete de tiradas en curso (ya pagado; se guarda en la partida): left, total, bet, won."""
        pk = self.state.flags.get("pick_pack")
        return pk if pk and pk.get("left", 0) > 0 else None

    def buy_pack(self):
        if self.pack or self.busy_now():
            return
        n = self.pack_n
        if not self.take_bet(self.bet * n):
            return
        self.state.flags["pick_pack"] = {"left": n, "total": n, "bet": self.bet, "won": 0.0}
        self.paused = False
        self.start()

    def start(self):
        pk = self.pack
        if self.busy_now() or not pk or self.paused:
            return
        pk["left"] -= 1
        self.run_bet = pk["bet"]
        self.busy = True
        res = L.spin_reel(random, L.PITY if self.cheat_armed() else self.crosses)   # la trampa asegura pico
        self.crosses = self.crosses + 1 if res == "nothing" else 0
        options = ["nothing", 0, 0, 0, 1, 1, 2, 3]
        strip = [random.choice(options) for _ in range(14)] + [res]
        self.reel = {"t": 0.0, "strip": strip, "res": res}
        self.audio.play("spin_start", 0.7)

    def launch(self, tier):
        if self.use_netherite and self.hint_ready("pick_netherite"):
            self.use_hint("pick_netherite")                # el próximo pico que sale es de netherita
            self.use_netherite = False
            tier = 4
            self.show("¡Pico de netherita!", GOLD)
        enchanted = self.use_cheat()
        self.run = L.Run(random.Random(), tier, mending=self.state.has_special("pick_mending"), enchanted=enchanted)
        self.cam = -6.0
        self.floaters = []
        self.audio.play("whoosh", 0.6)

    def finish(self):
        r = self.run
        win = r.win * self.run_bet                   # las menas pagan sobre la apuesta de la tirada
        if r.tnt_broken >= TNT_FEAT:
            self.feat("pick_tnt")
        if r.max_row >= DEEP_FEAT:
            self.feat("pick_deep")
        self.recent.append(r.win)
        del self.recent[:-14]
        self.done_round(self.pay(self.run_bet, win, label=f"x{fmt_num(r.win, 2)} · {r.hits} golpes"))

    def done_round(self, payout):
        self.busy = False
        pk = self.state.flags.get("pick_pack")
        if not pk:
            return
        pk["won"] += payout
        if pk["left"] > 0:
            if not self.paused:
                self.later(0.7, self.start)
            return
        del self.state.flags["pick_pack"]
        cost = pk["bet"] * pk["total"]
        net = pk["won"] - cost
        txt = f"Paquete de {pk['total']} tiradas: {fmt_money(pk['won'])} ({'+' if net >= 0 else '-'}{fmt_money(abs(net))})"
        self.later(1.4, lambda: self.show(txt, GOLD if net > 0 else MUTED))

    # ----------------------------------------------------------- update
    def update(self, dt):
        rl = self.reel
        if rl:
            old = int(rl["t"] / REEL_TIME * 14)
            rl["t"] += dt * (1.6 if self.speed >= 4 else 1.0)
            if int(rl["t"] / REEL_TIME * 14) != old:
                self.audio.play("reel_tick", 0.5, throttle=0.03)
            if rl["t"] >= REEL_TIME:
                self.reel = None
                self.audio.play("reel_stop", 0.8)
                if rl["res"] == "nothing":
                    self.recent.append(0.0)
                    del self.recent[:-14]
                    self.done_round(self.pay(self.run_bet, 0.0, label="¡Nada!"))
                else:
                    self.launch(rl["res"])
            return
        r = self.run
        if not r or r.done:
            return
        steps = self.speed * 2
        for _ in range(steps):
            r.step(dt * self.speed / steps)
            if r.done:
                break
        self.handle_events()
        target = r.y - self.rows_visible() * 0.38
        self.cam += (target - self.cam) * min(1.0, dt * 6)
        for f in self.floaters:
            f["t"] += dt
        self.floaters = [f for f in self.floaters if f["t"] < 1.2]
        if r.done:
            self.finish()

    @staticmethod
    def sound_kind(b):
        if b in ("dirt", "grass", "slime"):
            return "dirt"
        if b in ("diamond", "emerald", "diamond_block", "emerald_block"):
            return "gem"
        if b in ("coal", "redstone", "gold"):
            return "ore"
        return "stone"

    def handle_events(self):
        r = self.run
        hit_kind = None
        valued = [d for k, d in r.events if k == "break" and d[3]]
        if len(valued) > 2:                       # explosión: un solo texto con la suma
            tot = sum(d[3] for d in valued)
            cx = sum(d[1] for d in valued) / len(valued)
            cy = sum(d[2] for d in valued) / len(valued)
            self.floaters.append({"x": cx, "y": cy, "txt": f"+x{fmt_num(tot, 2)}", "col": GOLD_HI, "t": 0.0,
                                  "big": True})
        for kind, data in r.events:
            if kind == "hit":
                hit_kind = self.sound_kind(data[0])
            elif kind == "break":
                b, c, row, v = data
                x, y = self.world_screen(c + 0.5, row + 0.5)
                col = ORE_COL.get(b, (134, 96, 67) if b in ("dirt", "grass") else (130, 130, 136))
                self.fx.sparks(x, y, 6 if not v else 16, col, 0.8)
                sk = self.sound_kind(b)
                n = 3 if sk != "gem" else 3
                self.audio.play(f"break_{sk}{random.randrange(n)}", 0.9, throttle=0.04)
                if v and len(valued) <= 2:
                    self.floaters.append({"x": c, "y": row, "txt": f"+x{fmt_num(v, 2)}", "col": col, "t": 0.0})
            elif kind == "boom":
                cx, cy, rad = data
                x, y = self.world_screen(cx, cy)
                self.fx.sparks(x, y, 60, (255, 160, 60), 1.8)
                self.fx.add_shake(7)
                self.audio.play("explode", 0.8)
            elif kind == "bench":
                self.audio.play("unlock", 0.8)
                self.show(f"¡Mesa de trabajo! Pico de {L.TIERS[data][0].lower()}", GOLD)
            elif kind == "anvil":
                self.audio.play("unlock", 0.8)
                self.show("¡Yunque! Pico reparado", GOLD)
            elif kind == "arrow":
                self.audio.play("sparkle", 0.7)
            elif kind == "slime":
                self.audio.play("whoosh", 0.8)
        if hit_kind:
            name = {"dirt": "mine_dirt", "stone": "mine_stone", "ore": "mine_ore", "gem": "mine_ore"}[hit_kind]
            self.audio.play(f"{name}{random.randrange(4)}", 0.8, throttle=0.05)
        r.events.clear()

    # ------------------------------------------------------------ dibujo
    @property
    def cs(self):
        return max(28, min(60, int((self.vis.h - 20) / 10.5), int((self.vis.w - 330) / (L.COLS + 2))))

    def rows_visible(self):
        return (self.vis.h - 20) / self.cs

    def well_rect(self):
        cs = self.cs
        w = cs * L.COLS
        return pygame.Rect(self.vis.centerx - w // 2, self.vis.y + 10, w, self.vis.h - 20)

    def world_screen(self, x, y):
        wr = self.well_rect()
        return wr.x + x * self.cs, wr.y + (y - self.cam) * self.cs

    def draw_well(self, surf, wr):
        cs = self.cs
        run = self.run
        surf.set_clip(wr.inflate(cs * 2, 0))
        r0 = int(math.floor(self.cam)) - 1
        r1 = r0 + int(self.rows_visible()) + 3
        # fondo degradado por bandas
        for row in range(r0, r1):
            _, y = self.world_screen(0, row)
            surf.fill(well_color(row), (wr.x, int(y), wr.w, cs + 1))
        # paredes de roca madre
        for row in range(max(0, r0), r1):
            _, y = self.world_screen(0, row)
            surf.blit(tex("bedrock", cs), (wr.x - cs, int(y)))
            surf.blit(tex("bedrock", cs), (wr.right, int(y)))
        # hierba alta sobre el césped (desaparece con su bloque)
        if r0 <= -1:
            for c in (0, 2, 3, 6, 8):
                if run and (run.cell(c, 0) or [None])[0] != "grass":
                    continue
                x, y = self.world_screen(c, -1)
                surf.blit(tex("tall_grass", cs), (int(x), int(y)))
        pulse = 0.5 + 0.5 * math.sin(self.t * 3)
        for row in range(max(0, r0), r1):
            if run:
                cells = run.row(row)
            else:
                if not hasattr(self, "_preview"):
                    self._preview = L.Run(random.Random(7))
                cells = self._preview.row(row)
            for c, b in enumerate(cells):
                if not b:
                    continue
                x, y = self.world_screen(c, row)
                surf.blit(tex(block_tex(b[0], row), cs), (int(x), int(y)))
                full = L.BLOCKS[b[0]][1]
                if b[1] < full:
                    stage = min(9, int(10 * (1 - b[1] / full)))
                    surf.blit(tex(f"crack_{stage}", cs), (int(x), int(y)))
                if b[0] == "redstone":                      # la redstone emite luz
                    gfx.glow(surf, (x + cs / 2, y + cs / 2), int(cs * 0.95), (255, 40, 30),
                             0.16 + 0.10 * math.sin(self.t * 3 + c * 1.7 + row))
                elif b[0] in ("diamond_block", "emerald_block"):
                    gfx.glow(surf, (x + cs / 2, y + cs / 2), int(cs * 0.8), ORE_COL[b[0]], 0.10 + 0.08 * pulse)
        if run:
            px, py = self.world_screen(run.x, run.y)
            size = int(cs * 1.3 * run.widen)
            img = pygame.transform.rotate(tex(f"pickaxe_{run.tier}", size), run.angle)
            if run.widen > 1:
                gfx.glow(surf, (px, py), size, (180, 130, 255), 0.4)
            surf.blit(img, img.get_rect(center=(int(px), int(py))))
            hp = f"{max(0, int(run.dur))}/{run.max_dur}"
            hx, hy = int(px), int(py - size * 0.62 - 6)
            k = max(0.0, run.dur / run.max_dur)
            gfx.text(surf, "♥", (hx - gfx.text_w(hp, 14, "bl") // 2 - 12, hy), 14, "bl",
                     gfx.lerp_col((240, 60, 60), (255, 120, 120), k), anchor="center")
            gfx.text(surf, hp, (hx + 6, hy), 14, "bl", (255, 255, 255), anchor="center")
            for f in self.floaters:
                x, y = self.world_screen(f["x"] + 0.5, f["y"] + 0.2)
                a = int(255 * max(0.0, 1 - f["t"] / 1.2))
                gfx.text(surf, f["txt"], (x, y - 30 * f["t"]), 18 if f.get("big") else 12, "bl", f["col"],
                         anchor="center", alpha=a)
        surf.set_clip(None)
        pygame.draw.rect(surf, INK, wr.inflate(cs * 2 + 8, 8), 4, border_radius=6)

    def draw_reel(self, surf, wr):
        rl = self.reel
        cs = 72
        box = pygame.Rect(0, 0, cs + 40, cs * 3 + 24)
        box.center = wr.center
        gfx.box(surf, box, (30, 26, 34, 245), 12, outline=GOLD, ow=4, shadow_off=6)
        inner = box.inflate(-20, -20)
        surf.set_clip(inner)
        k = min(1.0, rl["t"] / REEL_TIME)
        pos = (1 - (1 - k) ** 3) * (len(rl["strip"]) - 1)       # frena al final
        for i, sym in enumerate(rl["strip"]):
            y = inner.centery + (i - pos) * (cs + 8) - cs / 2
            if y < inner.y - cs or y > inner.bottom:
                continue
            img = nothing_icon(cs) if sym == "nothing" else tex(f"pickaxe_{sym}", cs)
            surf.blit(img, (inner.centerx - cs // 2, int(y)))
        surf.set_clip(None)
        line = pygame.Rect(box.x + 4, box.centery - cs // 2 - 6, box.w - 8, cs + 12)
        pygame.draw.rect(surf, GOLD_HI, line, 3, border_radius=6)
        self.draw_pity(surf, box)

    def draw_pity(self, surf, box):
        """Cruces seguidas: 7 marcas bajo el rodillo (a la 8.ª tirada, pico seguro)."""
        w = 12
        x0 = box.centerx - (L.PITY * (w + 4) - 4) // 2
        for k in range(L.PITY):
            r_ = pygame.Rect(x0 + k * (w + 4), box.bottom + 8, w, 8)
            gfx.rrect(surf, r_, (*((230, 60, 60) if k < self.crosses else (60, 50, 60)), 255), 3)

    def draw(self, surf, rect):
        ui = self.ui
        v = self.vis
        felt(surf, v)
        wr = self.well_rect()
        run = self.run
        self.draw_well(surf, wr)
        if self.reel:
            self.draw_reel(surf, wr)
        # panel izquierdo: el pico (la vida va encima del propio pico)
        side = pygame.Rect(v.x + 16, v.y + 16, wr.x - self.cs - v.x - 32, v.h - 32)
        gfx.rrect(surf, side, (20, 22, 28, 200), 10)
        lx, lw = side.x + 10, side.w - 20
        y = side.y + 12
        tier = run.tier if run else None
        gfx.text(surf, "PICO", (lx, y), 12, "b", MUTED)
        if tier is not None:
            surf.blit(tex(f"pickaxe_{tier}", 48), (side.centerx - 24, y + 20))
            gfx.text(surf, L.TIERS[tier][0], (side.centerx, y + 76), 14, "bl", TEXT, anchor="midtop", max_w=lw)
        else:
            gfx.text(surf, "El rodillo", (side.centerx, y + 40), 12, "b", TEXT, anchor="midtop")
            gfx.text(surf, "decide", (side.centerx, y + 58), 12, "b", TEXT, anchor="midtop")
        y += 108
        if run:
            gfx.text(surf, f"Prof. {max(0, int(run.y))}", (lx, y), 12, "r", MUTED, max_w=lw)
            gfx.text(surf, f"Golpes {run.hits}", (lx, y + 20), 12, "r", MUTED, max_w=lw)
            if run.free_hits:
                gfx.text(surf, f"Gratis {run.free_hits}", (lx, y + 40), 12, "b", (200, 120, 255), max_w=lw)
            if run.widen > 1:
                gfx.text(surf, f"Ancho x{fmt_num(run.widen, 1)}", (lx, y + 60), 12, "b", (180, 140, 255), max_w=lw)
        self.cheat_pill(surf, side.x + 4, side.y + 200, side.w - 8)
        # ventajas durante la ronda: icono a la izquierda y texto aparte
        by = side.bottom - 54
        live = bool(run and not run.done)

        def ability(wid, key, name, style, icon, tip):
            nonlocal by
            ready = self.hint_ready(key)
            r_ = pygame.Rect(lx, by, lw, 46)
            hit = ui.button(wid, r_, "", style, enabled=ready and live, sound=None, tooltip=tip)
            surf.blit(tex(icon, 30), (r_.x + 6, r_.centery - 17))
            txt = name if ready else fmt_time(self.state.hint_remaining(key))
            gfx.text(surf, txt, (r_.x + 42 + (r_.w - 42) // 2, r_.centery - 2), 12, "b", TEXT, anchor="center",
                     max_w=r_.w - 46)
            by -= 54
            return hit
        if self.has_hint("pickaxe") and ability("pk_tnt", "pickaxe", "TNT", "red", "tnt",
                                               "Carga de TNT: explota donde está el pico."):
            self.use_hint("pickaxe")
            run.use_tnt()
        if self.has_hint("pick_bench") and ability("pk_anvil", "pick_bench", "YUNQUE", "green", "anvil",
                                                  "Yunque: repara el pico entero."):
            self.use_hint("pick_bench")
            run.use_anvil()
        # panel derecho: premio
        rside = pygame.Rect(wr.right + self.cs + 16, v.y + 16, v.right - wr.right - self.cs - 32, v.h - 32)
        gfx.rrect(surf, rside, (20, 22, 28, 200), 10)
        rx, rw = rside.x + 14, rside.w - 28
        y = rside.y + 12
        gfx.text(surf, "PREMIO", (rx, y), 12, "b", MUTED)
        win = run.win if run else 0.0
        gfx.text(surf, f"x{fmt_num(win, 2)}", (rx, y + 20), 22, "bl", GOLD_HI if win >= 1 else TEXT, max_w=rw)
        gfx.text(surf, fmt_money(win * (self.run_bet if run else self.bet)), (rx, y + 52), 12, "b", MUTED,
                 max_w=rw)
        y += 82
        for ore in reversed(L.ORES):
            surf.blit(tex(block_tex(ore, 0), 22), (rx, y))
            n = run.ores[ore] if run else 0
            gfx.text(surf, f"x{fmt_num(L.BLOCKS[ore][2], 2)}", (rx + 30, y + 3), 12, "r", MUTED)
            if n:
                gfx.text(surf, str(n), (rx + rw, y + 3), 12, "b", TEXT, anchor="topright")
            y += 27
        y += 6
        for i, m in enumerate(self.recent[::-1][:6]):
            col = GOLD if m >= 1 else (MUTED if m > 0 else DIM)
            gfx.text(surf, "nada" if m == 0 else f"x{fmt_num(m, 2)}", (rx + rw, y + i * 19), 12, "b", col,
                     anchor="topright")
        # controles
        c = self.controls_rect(rect)
        controls_bg(surf, c)
        pk = self.pack
        self.bet_control(surf, c.x + 16, c.y + 12, "APUESTA POR TIRADA")
        if pk:
            self.bet = pk["bet"]                       # la apuesta queda fija mientras dura el paquete
        sx = c.x + 376
        gfx.text(surf, "TIRADAS", (sx, c.y + 12), 12, "b", MUTED)
        if pk:
            gfx.rrect(surf, pygame.Rect(sx, c.y + 32, 160, 38), (20, 22, 28, 200), 8)
            gfx.text(surf, f"{pk['left']} de {pk['total']}", (sx + 80, c.y + 51), 14, "b", TEXT,
                     anchor="center", max_w=150)
        else:
            i = ui.segmented("pk_pack", (sx, c.y + 32, 160, 38), [str(n) for n in PACKS], PACKS.index(self.pack_n), 10)
            self.pack_n = PACKS[i]
        gfx.text(surf, "VELOCIDAD", (sx, c.y + 84), 10, "b", MUTED)
        sp = ui.segmented("pk_speed", (sx + 74, c.y + 78, 86, 24), [f"x{s}" for s in SPEEDS],
                          SPEEDS.index(self.speed), 10)
        self.speed = SPEEDS[sp]
        br = pygame.Rect(c.right - 190, c.y + 12, 170, 56)
        if self.has_hint("pick_netherite"):
            ready = self.hint_ready("pick_netherite")
            lbl = ("Netherita: SÍ" if self.use_netherite else "Netherita: no") if ready else                 f"Netherita {fmt_time(self.state.hint_remaining('pick_netherite'))}"
            nx = sx + 172
            if ui.button("pk_neth", (nx, c.y + 30, br.x - 12 - nx, 40), lbl,
                         "primary" if self.use_netherite else "dark", enabled=ready, size=10,
                         tooltip="El próximo pico que salga en el rodillo será de netherita."):
                self.use_netherite = not self.use_netherite
        keys = ui.keys if not ui.focus else []
        if pk:
            if ui.button("pk_pause", br, "SEGUIR" if self.paused else "PAUSA", "primary" if self.paused else "dark",
                         size=18, sound="ui", sub=f"llevas {fmt_money(pk['won'])}",
                         tooltip=f"Pagaste {fmt_money(pk['bet'] * pk['total'])} por {pk['total']} tiradas.")                     or pygame.K_SPACE in keys:
                self.paused = not self.paused
                if not self.paused:
                    self.start()
        else:
            cost = self.bet * self.pack_n
            if ui.button("pk_buy", br, f"COMPRAR {self.pack_n}", "primary", size=16, sound=None,
                         enabled=not self.busy_now() and self.state.money >= cost, sub=fmt_money(cost),
                         tooltip=f"{self.pack_n} tiradas de {fmt_money(self.bet)}: se pagan ya y se juegan seguidas."):
                self.buy_pack()

TNT_FEAT = 250          # bloques rotos por explosiones en una ronda (hazaña Dinamitero)
DEEP_FEAT = 110        # profundidad para la hazaña Plus Ultra
