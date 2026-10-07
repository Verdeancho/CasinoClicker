"""La Última Apuesta."""
import datetime
import math
import random

import pygame

from .base import BaseGame
from .common import dark_panel, controls_bg
from .. import gfx
from ..extra import T
from ..fmt import fmt_money
from ..gfx import TEXT, MUTED, DIM, GOLD_HI, RED

SUSPENSE = 3.4
SPIN_IN = 1.5
PW, PH = 760, 860
INK = (28, 52, 150)
PAPER = (246, 243, 232)
TYPE_SPEED = 38

RED_BTN = (226, 54, 62)
BLUE_BTN = (40, 110, 236)


def _fields():
    hoy = datetime.date.today().strftime("%d/%m/%Y")
    return [tuple(x.replace("{hoy}", hoy) if isinstance(x, str) else x for x in f) for f in T["fields"]]


class LastBet(BaseGame):
    gid = "lastbet"

    def setup(self):
        self.fields = _fields()
        self.fill = {}
        self.armed = False
        self.stake = 0.0
        self.chosen = None
        self.stage = "pick"
        self.st = 0.0
        self.tick_next = 0.0
        if self.state.flags.get("s4") and not self.state.flags.get("s3"):
            self.stage = "form"

    # ------------------------------------------------------------ estado
    def takeover(self):
        return self.stage in ("suspense", "spin", "form", "sent")

    def press(self, color):
        if not self.armed or self.stage != "pick":
            return
        self.chosen = color
        self.stake = self.state.money
        self.state.spend(self.state.money)
        self.state.flags["s4"] = True
        self.app.save_now()
        self.stage = "suspense"
        self.st = 0.0
        self.tick_next = 0.0
        self.audio.play("spin_start", 0.9)

    def done(self, i):
        f = self.fields[i]
        v = self.fill.get(i)
        if f[0] == "txt":
            return v is not None and v >= len(f[2])
        if f[0] == "chk":
            return v is not None
        if f[0] == "sig":
            return v is not None and v >= 1.0
        return True

    def all_done(self):
        return all(self.done(i) for i in range(len(self.fields)))

    def submit(self):
        self.stage = "sent"
        self.st = 0.0
        self.audio.play("explode", 0.6)
        self.fx.add_shake(8)

    def finish(self):
        f = self.state.flags
        f["s2"] = f.get("s1") or "dice"
        f["s3"] = True
        self.app.close_game()
        self.app.toast(T["toast_t"], T["toast_m"], RED, "star")
        self.app.log(T["log"], RED)
        try:
            pygame.display.set_caption(T["cap"])
        except pygame.error:
            pass
        self.app.save_now()

    def update(self, dt):
        self.st += dt
        if self.stage == "suspense":
            if self.st >= self.tick_next:
                gap = max(0.035, 0.26 * max(0.0, 1 - self.st / SUSPENSE) ** 1.6)
                self.tick_next = self.st + gap
                self.audio.play("reel_tick", 0.5 + 0.4 * self.st / SUSPENSE, throttle=0.02)
            if self.st >= SUSPENSE:
                self.stage = "spin"
                self.st = 0.0
                self.audio.play("whoosh", 0.9)
        elif self.stage == "spin" and self.st >= SPIN_IN:
            self.stage = "form"
            self.st = 0.0
            self.audio.play("reel_stop", 0.8)
        elif self.stage == "form":
            for i, f in enumerate(self.fields):
                v = self.fill.get(i)
                if f[0] == "txt" and v is not None and v < len(f[2]):
                    self.fill[i] = min(len(f[2]), v + dt * TYPE_SPEED)
                    if int(v) != int(self.fill[i]) and f[2][int(v)] != " ":
                        self.audio.play("tick0", 0.35, throttle=0.03)
                elif f[0] == "sig" and v is not None and v < 1.0:
                    self.fill[i] = min(1.0, v + dt / 1.2)
        elif self.stage == "sent" and self.st >= 2.2:
            self.finish()

    # ------------------------------------------------------------ dibujo
    def button_rects(self):
        v = self.vis
        r = 112
        return {"red": (v.centerx - 230, v.y + 300, r), "blue": (v.centerx + 230, v.y + 300, r)}

    def draw_button(self, surf, cx, cy, r, col, lit, shake=0.0):
        cx += random.uniform(-shake, shake)
        cy += random.uniform(-shake, shake)
        if lit:
            gfx.glow(surf, (cx, cy), int(r * 2.1), col, 0.35 + 0.15 * math.sin(self.t * 6))
        base = col if lit else gfx.mul_col(col, 0.35)
        pygame.draw.circle(surf, (14, 14, 22), (int(cx), int(cy) + 14), r + 10)
        pygame.draw.circle(surf, gfx.mul_col(base, 0.55), (int(cx), int(cy) + 10), r)
        pygame.draw.circle(surf, base, (int(cx), int(cy)), r)
        pygame.draw.circle(surf, gfx.mul_col(base, 1.25), (int(cx - r * 0.3), int(cy - r * 0.32)), int(r * 0.28))
        pygame.draw.circle(surf, (20, 20, 30), (int(cx), int(cy)), r, 6)

    def draw(self, surf, rect):
        ui = self.ui
        v = self.vis
        dark_panel(surf, v, 20, (40, 18, 30), (12, 10, 20))
        gfx.wavy_text(surf, "LA ÚLTIMA APUESTA", (v.centerx, v.y + 60), 34, GOLD_HI, self.t, 3, 4, anchor="center",
                      weight="bl")
        gfx.text(surf, "Dos botones. Uno lo cambia todo.", (v.centerx, v.y + 110), 16, "b", TEXT, anchor="center")
        gfx.text(surf, "Para pulsarlos tienes que jugártelo todo.", (v.centerx, v.y + 138), 14, "r", MUTED,
                 anchor="center")
        lit = self.armed
        for col, (cx, cy, r) in self.button_rects().items():
            if self.stage != "pick" and col == self.chosen:
                continue
            self.draw_button(surf, cx, cy, r, RED_BTN if col == "red" else BLUE_BTN, lit)
            br = pygame.Rect(cx - r, cy - r, 2 * r, 2 * r)
            if self.stage == "pick" and lit and ui.hover(br):
                ui.hot_any = True
                if ui.pressed:
                    ui.active = ("lb", col)
                if ui.released and ui.active == ("lb", col):
                    self.press(col)
        if self.stage == "pick":
            msg = "¿Rojo o azul?" if lit else "Pulsa MAX para desbloquear los botones"
            gfx.text(surf, msg, (v.centerx, v.y + 300), 16, "b", GOLD_HI if lit else DIM, anchor="center")
        c = self.controls_rect(rect)
        controls_bg(surf, c)
        gfx.text(surf, "APUESTA", (c.x + 16, c.y + 12), 12, "b", MUTED)
        amount = self.state.money if self.stage == "pick" else self.stake
        gfx.rrect(surf, (c.x + 16, c.y + 32, 300, 50), (12, 12, 22, 255), 10, border=(70, 66, 104), bw=1)
        gfx.text(surf, fmt_money(amount if self.armed else 0), (c.x + 30, c.y + 57), 18, "b", GOLD_HI,
                 anchor="midleft", max_w=270)
        if ui.button("lb_max", (c.x + 330, c.y + 32, 120, 50), "MAX", "gold", size=18, enabled=self.stage == "pick",
                     sound="chip0"):
            self.armed = True
            self.audio.play("unlock", 0.8)
        gfx.text(surf, "Todo tu dinero. Sin vuelta atrás.", (c.x + 470, c.y + 57), 14, "r", MUTED, anchor="midleft")

    def draw_takeover(self, surf):
        W, H = surf.get_size()
        cx, cy, r = self.button_rects()[self.chosen] if self.chosen else (W // 2, H // 2, 112)
        col = RED_BTN if self.chosen == "red" else BLUE_BTN
        if self.stage == "suspense":
            k = min(1.0, self.st / SUSPENSE)
            dim = pygame.Surface((W, H), pygame.SRCALPHA)
            dim.fill((0, 0, 0, int(225 * min(1.0, k * 1.6))))
            surf.blit(dim, (0, 0))
            flick = col if int(self.st * (6 + 18 * k)) % 2 == 0 else (BLUE_BTN if col == RED_BTN else RED_BTN)
            self.draw_button(surf, cx, cy, r, flick, True, shake=1 + 9 * k * k)
            if k > 0.55:
                gfx.text(surf, "." * (1 + int(self.st * 3) % 3), (cx, cy + r + 40), 28, "bl", TEXT, anchor="center")
            return
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 225))
        surf.blit(dim, (0, 0))
        px, py = (W - PW) // 2, (H - PH) // 2
        if self.stage == "spin":
            self.draw_button(surf, cx, cy, r, col, True)
            k = min(1.0, self.st / SPIN_IN)
            e = 1 - (1 - k) ** 3
            paper = pygame.Surface((PW, PH), pygame.SRCALPHA)
            self.draw_paper(paper, 0, 0, interactive=False)
            img = pygame.transform.rotozoom(paper, (1 - e) * 900, max(0.02, e))
            x = cx + (W // 2 - cx) * e
            y = cy + (H // 2 - cy) * e
            surf.blit(img, img.get_rect(center=(int(x), int(y))))
            return
        self.draw_paper(surf, px, py, interactive=self.stage == "form")
        if self.stage == "sent":
            k = min(1.0, self.st / 0.35)
            sc = 2.4 - 1.4 * k
            stamp = pygame.Surface((420, 130), pygame.SRCALPHA)
            pygame.draw.rect(stamp, (210, 30, 40, 230), stamp.get_rect(), 10, border_radius=14)
            gfx.text(stamp, T["stamp"], (210, 66), 56, "bl", (210, 30, 40), anchor="center", shadow=False)
            img = pygame.transform.rotozoom(stamp, 14, sc)
            img.set_alpha(int(255 * k))
            surf.blit(img, img.get_rect(center=(W // 2 + 120, H // 2 + 250)))

    def draw_paper(self, surf, ox, oy, interactive):
        ui = self.ui
        pygame.draw.rect(surf, (0, 0, 0, 90) if surf.get_flags() & pygame.SRCALPHA else (20, 20, 20),
                         (ox + 10, oy + 12, PW, PH), border_radius=6)
        pygame.draw.rect(surf, PAPER, (ox, oy, PW, PH), border_radius=6)
        gfx.text(surf, T["title"], (ox + PW // 2, oy + 52), 46, "bl", (20, 20, 28), anchor="center", shadow=False)
        gfx.text(surf, T["sub"], (ox + PW // 2, oy + 92), 12, "r", (90, 90, 100), anchor="center", shadow=False,
                 max_w=PW - 60)
        pygame.draw.line(surf, (20, 20, 28), (ox + 40, oy + 112), (ox + PW - 40, oy + 112), 3)
        y = oy + 126
        lx = ox + 40
        for i, f in enumerate(self.fields):
            kind = f[0]
            if kind == "sec":
                band = pygame.Rect(lx, y, PW - 80, 26)
                pygame.draw.rect(surf, (214, 228, 242), band)
                pygame.draw.rect(surf, (60, 70, 90), band, 2)
                gfx.text(surf, f[1], band.center, 12, "bl", (20, 26, 40), anchor="center", shadow=False)
                y += 36
                continue
            label = f[1] if f[1].endswith("?") else f[1] + ":"
            gfx.text(surf, label, (lx, y + 6), 12, "b", (24, 24, 32), shadow=False)
            fx = lx + gfx.text_w(label, 12, "b") + 10
            row = pygame.Rect(fx - 4, y - 2, ox + PW - 40 - fx + 4, 30)
            v = self.fill.get(i)
            if kind == "txt":
                pygame.draw.line(surf, (40, 40, 50), (fx, y + 24), (ox + PW - 40, y + 24), 2)
                if v is not None:
                    txt = f[2][:int(v)]
                    gfx.text(surf, txt, (fx + 4, y + 4), 14, "b", INK, shadow=False, max_w=row.w - 8)
                    if v < len(f[2]) and int(self.t * 6) % 2 == 0:
                        tx = fx + 6 + gfx.text_w(txt, 14, "b")
                        pygame.draw.line(surf, INK, (tx, y + 4), (tx, y + 20), 2)
                elif interactive:
                    gfx.text(surf, T["fill"], (fx + 4, y + 6), 12, "r", (150, 150, 160), shadow=False)
                clicked = interactive and v is None and ui.hover(row)
            elif kind == "chk":
                bx = fx
                for j, opt in enumerate(f[2]):
                    box = pygame.Rect(bx, y + 2, 20, 20)
                    pygame.draw.rect(surf, (255, 255, 255), box)
                    pygame.draw.rect(surf, (30, 30, 40), box, 2)
                    if v is not None and (v == j if f[3] is None else j == f[3]):
                        pygame.draw.line(surf, INK, (box.x + 3, box.y + 3), (box.right - 4, box.bottom - 4), 4)
                        pygame.draw.line(surf, INK, (box.right - 4, box.y + 3), (box.x + 3, box.bottom - 4), 4)
                    gfx.text(surf, opt, (box.right + 8, y + 4), 12, "b", (24, 24, 32), shadow=False)
                    hit = pygame.Rect(box.x, box.y, box.w + 12 + gfx.text_w(opt, 12, "b"), box.h)
                    if interactive and v is None and ui.hover(hit):
                        ui.hot_any = True
                        if ui.released:
                            self.fill[i] = j if f[3] is None else f[3]
                            self.audio.play("tick2", 0.8)
                    bx = hit.right + 20
                y += 36
                continue
            else:
                pygame.draw.line(surf, (40, 40, 50), (fx, y + 30), (fx + 300, y + 30), 2)
                if v is not None:
                    self.draw_signature(surf, fx + 10, y + 22, v)
                elif interactive:
                    gfx.text(surf, T["sign"], (fx + 4, y + 8), 12, "r", (150, 150, 160), shadow=False)
                row = pygame.Rect(fx - 4, y - 6, 320, 40)
                clicked = interactive and v is None and ui.hover(row)
            if clicked:
                ui.hot_any = True
                if ui.released:
                    self.fill[i] = 0.0
                    self.audio.play("ui", 0.6)
            y += 40 if kind == "sig" else 36
        ok = self.all_done()
        sb = pygame.Rect(ox + PW - 250, oy + PH - 74, 210, 54)
        if interactive:
            if ui.button("lb_submit", sb, T["submit"], "blue", size=20, enabled=ok, sound="ui"):
                self.submit()
            if not ok:
                gfx.text(surf, T["need"], (sb.x - 16, sb.centery), 12, "r", (120, 120, 130), anchor="midright",
                         shadow=False)
        else:
            pygame.draw.rect(surf, (150, 160, 175), sb, border_radius=10)
            gfx.text(surf, T["submit"], sb.center, 20, "b", (240, 240, 245), anchor="center", shadow=False)
        gfx.text(surf, T["page"], (ox + 40, oy + PH - 34), 12, "r", (110, 110, 120), shadow=False)

    def draw_signature(self, surf, x, y, k):
        pts = []
        n = 90
        for s in range(int(n * k) + 1):
            u = s / n
            pts.append((x + u * 260, y - 8 * math.sin(u * 19) - 6 * math.sin(u * 7 + 1) + 4 * math.cos(u * 31)))
        if len(pts) > 1:
            pygame.draw.lines(surf, INK, False, pts, 3)
