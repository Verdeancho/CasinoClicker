"""Clase base para los juegos (pygame, interfaz en modo inmediato, estética retro)."""
import math
import random

import pygame

from .. import gfx
from ..data import GAME_BY_ID, HINTS
from ..fmt import fmt_money, fmt_num, fmt_time, parse_amount
from ..gfx import TEXT, MUTED, DIM, GOLD, GREEN, RED, ORANGE, PANEL_LO, LINE

CONTROLS_H = 112


class BaseGame:
    gid = ""

    def __init__(self, app):
        self.app = app
        self.state = app.state
        self.ui = app.ui
        self.audio = app.audio
        self.fx = app.fx
        self.gdef = GAME_BY_ID[self.gid]
        self.variant = None
        if self.gdef.variants:
            owned = [v.id for v in self.gdef.variants if self.state.has_variant(self.gid, v.id)]
            self.variant = owned[0] if owned else self.gdef.variants[0].id
        self.bet = max(self.gdef.min_bet, min(1.0, self.state.money))
        self.bet_text = ""
        self.busy = False
        self.banner = None
        self.t = 0.0
        self.timers = []
        self.vis = pygame.Rect(0, 0, 10, 10)
        self.setup()

    # ---------------------------------------------------------------- hooks
    def setup(self):
        pass

    def update(self, dt):
        pass

    def draw(self, surf, rect):
        pass

    def on_show(self):
        pass

    def on_hide(self):
        pass

    def on_upgrade(self, uid):
        pass

    def on_variant(self):
        pass

    def can_change_variant(self):
        return not self.busy

    def set_variant(self, vid):
        if vid == self.variant:
            return
        if not self.can_change_variant():
            self.show("Termina la ronda antes de cambiar de modalidad", RED)
            return
        self.variant = vid
        self.banner = None
        self.on_variant()

    # ------------------------------------------------------------- frame
    def _tick(self, dt):
        self.t += dt
        for tm in self.timers[:]:
            tm[0] -= dt
            if tm[0] <= 0:
                if tm in self.timers:
                    self.timers.remove(tm)
                tm[1]()
        self.update(dt)

    def update_timers_only(self, dt):
        self._tick(dt)

    def frame(self, surf, rect, dt):
        self._tick(dt)
        if self.gdef.variants:
            self.variant_bar(surf, pygame.Rect(rect.x, rect.y, rect.w, 46))
            rect = pygame.Rect(rect.x, rect.y + 54, rect.w, rect.h - 54)
        self.vis = pygame.Rect(rect.x, rect.y, rect.w, rect.h - CONTROLS_H - 10)
        self.draw(surf, rect)
        self.draw_hot(surf)
        self.draw_banner(surf)

    def draw_hot(self, surf):
        """Marco dorado y bote de la mesa caliente."""
        h = self.state.hot
        if not h or h["gid"] != self.gid:
            return
        v = self.vis
        pulse = 0.5 + 0.5 * math.sin(self.t * 5)
        col = gfx.lerp_col((240, 170, 40), (255, 236, 140), pulse)
        gfx.rrect(surf, v.inflate(8, 8), (0, 0, 0, 0), 22, border=gfx.INK, bw=8)
        gfx.rrect(surf, v.inflate(4, 4), (0, 0, 0, 0), 20, border=col, bw=5)
        rem = self.state.hot_remaining()
        txt = (f"MESA CALIENTE · ganancias x{fmt_num(self.state.hot_mult())} · bote {fmt_money(h['pot'])} · "
               f"{int(rem) // 60}:{int(rem) % 60:02d}")
        w = gfx.text_w(txt, 12, "b") + 30
        r = pygame.Rect(0, 0, w, 30)
        r.midtop = (v.centerx, v.y - 14)
        gfx.box(surf, r, (*gfx.mul_col(col, 0.55), 255), 8, outline=col, ow=3, shadow_off=3)
        gfx.text(surf, txt, r.center, 12, "b", (255, 248, 220), anchor="center")
        bar = pygame.Rect(r.x + 8, r.bottom - 6, r.w - 16, 3)
        fw = int(bar.w * h["pot"] / max(1e-9, h["pot0"]))
        if fw > 1:
            surf.fill((255, 240, 160), (bar.x, bar.y, fw, bar.h))

    def variant_bar(self, surf, r):
        """Botones para cambiar de modalidad (las bloqueadas muestran su precio y se compran aquí)."""
        ui = self.ui
        vs = self.gdef.variants
        gap = 8
        w = (r.w - gap * (len(vs) - 1)) / len(vs)
        can_switch = self.can_change_variant()
        for i, v in enumerate(vs):
            br = pygame.Rect(int(r.x + i * (w + gap)), r.y, int(w), r.h)
            owned = self.state.has_variant(self.gid, v.id)
            cur = v.id == self.variant
            if owned:
                if ui.button(("var", self.gid, v.id), br, v.name, "gold" if cur else "dark", size=12,
                             enabled=cur or can_switch, tooltip=v.desc):
                    if not cur:
                        self.set_variant(v.id)
            else:
                cost = self.state.variant_cost(self.gid, v.id)
                can = self.state.money >= cost and can_switch
                if ui.button(("varb", self.gid, v.id), br, v.name, "ghost", size=12, enabled=can, sound=None,
                             sub=f"abrir {fmt_money(cost)}", tooltip=v.desc):
                    if self.state.unlock_variant(self.gid, v.id):
                        self.audio.play("unlock")
                        self.fx.confetti(br.centerx, br.centery, 40, 0.6)
                        self.app.toast("Modalidad desbloqueada", f"{self.gdef.name}: {v.name}", GOLD, self.gid)
                        self.set_variant(v.id)

    def later(self, seconds, fn):
        self.timers.append([seconds, fn])

    def controls_rect(self, rect):
        return pygame.Rect(rect.x, rect.bottom - CONTROLS_H, rect.w, CONTROLS_H)

    # ---------------------------------------------------------- apuestas
    def clamp_bet(self):
        self.bet = max(self.gdef.min_bet, self.bet)
        if self.bet < 1e9:
            self.bet = round(self.bet, 2)

    def bet_control(self, surf, x, y, label="APUESTA", wid=None):
        """Selector de apuesta: campo editable + botones rápidos. Ocupa ~350x92."""
        ui = self.ui
        wid = wid or (self.gid, "bet")
        gfx.text(surf, label, (x, y), 12, "b", MUTED)
        focused = ui.focus == wid
        shown = self.bet_text if focused else fmt_num(self.bet)
        txt, done = ui.text_input(wid, (x, y + 20, 140, 50), shown, size=16, color=gfx.GOLD_HI)
        if focused or done:
            self.bet_text = txt
        if done:
            v = parse_amount(self.bet_text)
            if v is not None:
                self.bet = v
            self.bet_text = ""
        bx = x + 148
        bw = 46
        btns = [("½", lambda: self.bet / 2), ("x2", lambda: self.bet * 2),
                ("MIN", lambda: self.gdef.min_bet), ("MAX", lambda: max(self.gdef.min_bet, self.state.money))]
        for i, (lbl, fn) in enumerate(btns):
            if ui.button(wid + (lbl,), (bx + i * (bw + 4), y + 20, bw, 50), lbl, "dark", size=12, sound="chip0"):
                self.bet = fn()
        self.clamp_bet()
        ok = self.state.money >= self.bet
        t = f"tienes {fmt_money(self.state.money)}" if ok else "sin fondos"
        sz = 12 if gfx.text_w(label, 12, "b") + gfx.text_w(t, 12, "r") + 12 <= 338 else 10
        gfx.text(surf, t, (x + 338, y), sz, "r", MUTED if ok else RED, anchor="topright")
        return self.bet

    def take_bet(self, amount):
        ok = self.state.place_bet(self.gid, amount)
        if ok:
            self.audio.play(f"chip{random.randint(0, 2)}", 0.7)
        return ok

    def pay(self, bet, gross, label=None, streak=True, pos=None, quiet=False):
        payout = self.state.settle(self.gid, bet, gross, count_streak=streak, variant=self.variant)
        hot = self.state.hot_extra
        if hot > 0:
            hx, hy = pos or (self.vis.centerx, self.vis.bottom - 70)
            self.fx.text(hx, hy - 40, f"¡Mesa caliente! +{fmt_money(hot)}", (255, 214, 90), 22)
            self.fx.sparks(hx, hy - 40, 24, (255, 214, 90), 1.2)
        net = payout - bet
        mult = gross / bet if bet else 0
        px, py = pos or (self.vis.centerx, self.vis.bottom - 70)
        if net > 1e-9:
            txt = f"+{fmt_money(net)}"
            self.show(f"{label + '  ' if label else ''}{txt}" + (f"  x{fmt_num(mult)}" if mult > 0 else ""), GREEN,
                      big=mult >= 10)
            if not quiet:
                self.audio.play("win3" if mult >= 10 else "win2" if mult >= 2.5 else "win1")
            self.fx.text(px, py, txt, GREEN, 26 if mult < 10 else 34)
            self.fx.sparks(px, py, 14 if mult < 10 else 30, (120, 240, 170))
            if mult >= 10:
                self.fx.confetti(self.vis.centerx, self.vis.y, 90, w=self.vis.w)
                self.app.log(f"{self.gdef.name}: x{fmt_num(mult)} → +{fmt_money(net)}", GOLD)
            if mult >= 50:
                self.fx.add_shake(6)
        elif net < -1e-9:
            self.show(f"{label + '  ' if label else ''}-{fmt_money(-net)}", RED)
            if not quiet:
                self.audio.play("lose", 0.8)
        else:
            self.show(label or "Empate: recuperas la apuesta", MUTED)
            if not quiet:
                self.audio.play("push")
        return payout

    # ----------------------------------------------------------- ventajas
    def has_hint(self, key=None):
        return self.state.hint_owned(key or self.gid)

    def hint_ready(self, key=None):
        return self.state.hint_ready(key or self.gid)

    def use_hint(self, key=None):
        self.state.consume_hint(key or self.gid)
        self.audio.play("sparkle", 0.7)

    def reliable(self, base):
        """Probabilidad (oculta) de que la ventaja acierte; las legendarias la hacen segura."""
        return self.state.hint_reliability(self.gid, base)

    def feat(self, flag):
        """Marca una hazaña o logro de este juego."""
        if not self.state.flags.get(flag):
            self.state.set_flag(flag)

    # ------------------------------------------------------------- trampas
    def cheat_armed(self):
        return self.state.cheat_active(self.gid)

    def use_cheat(self):
        if self.state.consume_cheat(self.gid):
            self.audio.play("sparkle", 0.9)
            return True
        return False

    def cheat_pill(self, surf, x, y, w=250):
        if not self.cheat_armed():
            return None
        from ..data import CHEATS
        r = pygame.Rect(x, y, w, 34)
        gfx.rrect(surf, r, (40, 16, 46, 235), 8, border=(200, 90, 255), bw=4)
        gfx.text(surf, f"TRAMPA: {CHEATS[self.gid][0]}", (r.x + 12, r.centery), 12, "b", (230, 170, 255),
                 anchor="midleft", max_w=w - 20)
        return r

    def hint_pill(self, surf, x, y, w=250, key=None, name=None):
        """Indicador de una ventaja: nombre y si está lista o cuánto falta."""
        key = key or self.gid
        if not self.has_hint(key):
            return None
        name = name or HINTS[self.gid][0]
        ready = self.hint_ready(key)
        r = pygame.Rect(x, y, w, 34)
        gfx.rrect(surf, r, (*((70, 60, 20) if ready else PANEL_LO), 235), 8, border=gfx.GOLD if ready else LINE, bw=4)
        from ..icons import icon
        surf.blit(icon("golden", 24), (r.x + 8, r.y + 5))
        txt = f"{name}: ¡LISTA!" if ready else f"{name}: {fmt_time(self.state.hint_remaining(key))}"
        gfx.text(surf, txt, (r.x + 38, r.centery), 12, "b", gfx.GOLD_HI if ready else MUTED, anchor="midleft",
                 max_w=w - 46)
        return r

    # ------------------------------------------------------------ banner
    def show(self, text, color=TEXT, big=False):
        self.banner = {"text": text, "color": color, "t": 0.0, "big": big}

    def draw_banner(self, surf):
        b = self.banner
        if not b:
            return
        b["t"] += self.ui.dt
        t = b["t"]
        k = gfx.ease_out_back(min(1.0, t / 0.3))
        size = 22 if b["big"] else 16
        tw = gfx.text_w(b["text"], size, "b")
        w, h = tw + 44, gfx.line_height(size) + 22
        cx, cy = self.vis.centerx, self.vis.bottom - 30
        a = 255 if t < 4.0 else int(max(120, 255 - (t - 4.0) * 300))
        r = pygame.Rect(0, 0, max(8, int(w * k)), max(8, int(h * k)))
        r.center = (cx, cy)
        gfx.box(surf, r, (*PANEL_LO, int(240 * a / 255)), 10, outline=b["color"], ow=4, shadow_off=5)
        if k > 0.6:
            if b["big"]:
                gfx.wavy_text(surf, b["text"], r.center, size, b["color"], self.t, 2, 6, weight="b")
            else:
                gfx.text(surf, b["text"], r.center, size, "b", b["color"], anchor="center", alpha=a)

    def title_text(self, surf, s, pos, size=14, color=MUTED):
        gfx.text(surf, s, pos, size, "b", color)
