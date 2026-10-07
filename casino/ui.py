"""Interfaz en modo inmediato: cada frame se llama a los widgets, que dibujan y devuelven eventos.
Las animaciones de hover/pulsación se guardan por id."""
import math
import time

import pygame

from . import gfx
from .gfx import TEXT, MUTED, DIM, WHITE

STYLES = {
    #          cara              texto
    "primary": ((150, 112, 196), (255, 255, 255)),
    "gold": ((253, 162, 0), (255, 255, 255)),
    "green": ((60, 182, 132), (255, 255, 255)),
    "red": ((254, 95, 85), (255, 255, 255)),
    "blue": ((0, 150, 245), (255, 255, 255)),
    "pink": ((236, 104, 164), (255, 255, 255)),
    "dark": ((70, 86, 94), (255, 255, 255)),
    "ghost": ((54, 66, 74), (220, 228, 232)),
}
DISABLED = ((66, 78, 86), (132, 144, 150))
LIP = 5


class UI:
    def __init__(self, audio=None):
        self.audio = audio
        self.mx = self.my = 0
        self.down = False
        self.pressed = False
        self.released = False
        self.rpressed = False
        self.wheel = 0
        self.active = None
        self.hot_any = False
        self.anims = {}
        self.focus = None
        self.typed = []
        self.keys = []
        self.clip_stack = []
        self.modal = None
        self.tip = None
        self.tip_title = None        # color del título del texto flotante (o "legendary": dorado animado)
        self.tip_id = None
        self.tip_since = 0
        self.scrolls = {}
        self.dt = 0.016
        self.t = 0.0
        self.frame_hover = None
        self.last_hover_sound = None
        self.surf = None
        self.drag = None
        self.map_pos = lambda pos: pos  # ventana -> lienzo (la ventana se puede escalar)

    # ------------------------------------------------------------- frame
    def begin(self, surf, events, dt):
        self.surf = surf
        self.dt = dt
        self.t += dt
        self.pressed = self.released = self.rpressed = False
        self.wheel = 0
        self.typed = []
        self.keys = []
        self.hot_any = False
        self.frame_hover = None
        self.tip = None
        self.tip_title = None
        for e in events:
            if e.type == pygame.MOUSEMOTION:
                self.mx, self.my = self.map_pos(e.pos)
            elif e.type == pygame.MOUSEBUTTONDOWN:
                self.mx, self.my = self.map_pos(e.pos)
                if e.button == 1:
                    self.down = True
                    self.pressed = True
                elif e.button == 3:
                    self.rpressed = True
            elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                self.mx, self.my = self.map_pos(e.pos)
                self.down = False
                self.released = True
            elif e.type == pygame.MOUSEWHEEL:
                self.wheel += e.y
            elif e.type == pygame.TEXTINPUT:
                self.typed.append(e.text)
            elif e.type == pygame.KEYDOWN:
                self.keys.append(e.key)

    def end(self):
        if self.released:
            self.active = None
            self.drag = None
        cur = pygame.SYSTEM_CURSOR_HAND if self.hot_any else pygame.SYSTEM_CURSOR_ARROW
        if cur != getattr(self, "_cursor", None):
            self._cursor = cur
            try:
                pygame.mouse.set_cursor(cur)
            except pygame.error:
                pass
        # sonido de hover muy sutil al entrar en un widget nuevo
        if self.frame_hover != self.last_hover_sound:
            if self.frame_hover is not None and self.audio:
                self.audio.play("hover", 1.0, throttle=0.04)
            self.last_hover_sound = self.frame_hover
        self.draw_tooltip()

    # ------------------------------------------------------------ helpers
    @property
    def mouse(self):
        return (self.mx, self.my)

    def push_clip(self, rect):
        rect = pygame.Rect(rect)
        if self.clip_stack:
            rect = rect.clip(self.clip_stack[-1])
        self.clip_stack.append(rect)
        self.surf.set_clip(rect)

    def pop_clip(self):
        self.clip_stack.pop()
        self.surf.set_clip(self.clip_stack[-1] if self.clip_stack else None)

    def hover(self, rect):
        rect = pygame.Rect(rect)
        if not rect.collidepoint(self.mx, self.my):
            return False
        if self.clip_stack and not self.clip_stack[-1].collidepoint(self.mx, self.my):
            return False
        if self.modal and not self._in_modal:
            return False
        return True

    _in_modal = False

    def anim(self, wid, target, speed=14.0):
        v = self.anims.get(wid, target if wid not in self.anims else 0.0)
        v = gfx.approach(v, target, self.dt, speed)
        self.anims[wid] = v
        return v

    def clicked_area(self, wid, rect, sound=None):
        """Zona clicable invisible. Devuelve True al soltar dentro."""
        h = self.hover(rect)
        if h:
            self.hot_any = True
            self.frame_hover = wid
            if self.pressed:
                self.active = wid
        if self.released and self.active == wid and h:
            if sound and self.audio:
                self.audio.play(sound)
            return True
        return False

    def tooltip(self, wid, rect, text, delay=0.35, title=None):
        """Texto flotante al dejar el ratón `delay` segundos sobre la zona. Con `title` (un color, o "legendary"),
        la primera línea se pinta como título de ese color."""
        if self.hover(rect):
            if self.tip_id != wid:
                self.tip_id = wid
                self.tip_since = self.t
            if self.t - self.tip_since > delay:
                self.tip = text
                self.tip_title = title
        elif self.tip_id == wid:
            self.tip_id = None

    def draw_tooltip(self):
        if not self.tip:
            return
        paras = str(self.tip).split("\n")
        head = []
        if self.tip_title:
            head = gfx.wrap(paras[0], 14, "bl" if self.tip_title == "legendary" else "b", 380) or [""]
            paras = paras[1:]
        lines = []
        for para in paras:
            lines += gfx.wrap(para, 12, "r", 380) or [""]
        lh = gfx.line_height(12) + 2
        hh = gfx.line_height(14) + 4
        w = max([gfx.text_w(l, 12) for l in lines] + [gfx.text_w(l, 14, "bl") + 4 for l in head]) + 28
        h = len(lines) * lh + len(head) * hh + (6 if head and lines else 0) + 18
        x = min(self.mx + 18, gfx.W - w - 8)
        y = min(self.my + 20, gfx.H - h - 8)
        self.surf.set_clip(None)
        legendary = self.tip_title == "legendary"
        gfx.box(self.surf, (x, y, w, h), (*gfx.PANEL_LO, 250), 8, ow=4, shadow_off=6)
        if legendary:
            pulse = 0.5 + 0.5 * math.sin(self.t * 4)
            pygame.draw.rect(self.surf, gfx.lerp_col((200, 130, 20), (255, 230, 120), pulse), (x, y, w, h), 2,
                             border_radius=8)
        ty = y + 10
        for l in head:
            if legendary:
                self.legendary_text(l, x + 14, ty)
            else:
                gfx.text(self.surf, l, (x + 14, ty), 14, "b", self.tip_title)
            ty += hh
        if head and lines:
            ty += 6
        for i, l in enumerate(lines):
            gfx.text(self.surf, l, (x + 14, ty + i * lh), 12, "r", TEXT)

    def legendary_text(self, s, x, y):
        """Título legendario: dorado que brilla en oleadas, letras que flotan un poco y destellos que lo cruzan."""
        t = self.t
        cx = x
        for i, ch in enumerate(s):
            k = 0.5 + 0.5 * math.sin(t * 5 - i * 0.45)
            col = gfx.lerp_col((240, 160, 20), (255, 248, 200), k)
            dy = round(1.5 * math.sin(t * 4 - i * 0.6))
            gfx.text(self.surf, ch, (cx, y + dy), 14, "bl", col)
            cx += gfx.text_w(ch, 14, "bl")
        tw = cx - x
        for j in range(2):                          # destellos que recorren el borde de arriba y el de abajo
            u = (t * 0.6 + j * 0.5) % 1.0
            sx, sy = x + u * tw, (y - 4) if j == 0 else (y + gfx.line_height(14) + 3)
            r = 1 + 2.5 * math.sin(u * math.pi)
            pygame.draw.line(self.surf, (255, 255, 230), (sx - r, sy), (sx + r, sy), 2)
            pygame.draw.line(self.surf, (255, 255, 230), (sx, sy - r), (sx, sy + r), 2)

    # ------------------------------------------------------------- botón
    def button(self, wid, rect, label="", style="primary", icon=None, enabled=True, size=16, weight="b",
               sound="ui", tooltip=None, radius=10, sub=None, selected=False):
        rect = pygame.Rect(rect)
        h = enabled and self.hover(rect)
        if h:
            self.hot_any = True
            self.frame_hover = wid
            if self.pressed:
                self.active = wid
        pressed = self.active == wid and self.down and h
        hv = self.anim(wid, 1.0 if h else 0.0, 18)
        face, fg = STYLES.get(style, STYLES["primary"]) if enabled else DISABLED
        if selected:
            face = gfx.mul_col(face, 1.2)
        if hv > 0.01:
            face = gfx.lerp_col(face, (255, 255, 255), 0.12 * hv)
        lip = LIP
        base_r = pygame.Rect(rect.x, rect.y + lip, rect.w, rect.h - lip)
        if style == "ghost":
            gfx.rrect(self.surf, rect, (*face, 255), radius, border=gfx.LINE, bw=4)
            face_r = rect
        else:
            gfx.rrect(self.surf, base_r.move(0, 2), (0, 0, 0, 90), radius)
            gfx.rrect(self.surf, base_r, (*gfx.mul_col(face, 0.62), 255), radius)
            face_r = pygame.Rect(rect.x, rect.y + (lip if pressed else 0), rect.w, rect.h - lip)
            gfx.rrect(self.surf, face_r, (*face, 255), radius)
        cx, cy = face_r.centerx, face_r.centery
        if icon is not None:
            from .icons import icon as get_icon
            isz = min(face_r.h - 8, max(20, size + 12))
            ic = get_icon(icon, isz)
            if label:
                tw = gfx.text_w(label, size, weight)
                total = isz + 8 + tw
                x0 = cx - total // 2
                self.surf.blit(ic, (x0, cy - isz // 2))
                gfx.text(self.surf, label, (x0 + isz + 8, cy), size, weight, fg, anchor="midleft")
            else:
                self.surf.blit(ic, ic.get_rect(center=(cx, cy)))
        elif label:
            if sub:
                gfx.text(self.surf, label, (cx, cy - gfx.line_height(size) * 0.42), size, weight, fg, anchor="center",
                         max_w=face_r.w - 10)
                gfx.text(self.surf, sub, (cx, cy + gfx.line_height(size) * 0.55), 12, "r",
                         gfx.mul_col(fg, 0.92), anchor="center", max_w=face_r.w - 8)
            else:
                gfx.text(self.surf, label, (cx, cy), size, weight, fg, anchor="center", max_w=face_r.w - 10)
        if tooltip:
            self.tooltip(wid, rect, tooltip)
        if self.released and self.active == wid and h:
            if sound and self.audio:
                self.audio.play(sound)
            return True
        return False

    # -------------------------------------------------------- segmentado
    def segmented(self, wid, rect, options, selected, size=14):
        rect = pygame.Rect(rect)
        n = len(options)
        gfx.rrect(self.surf, rect, (*gfx.PANEL_LO, 255), 8, border=gfx.LINE, bw=4)
        w = (rect.w - 8) / n
        pos = self.anim((wid, "sel"), float(selected), 20)
        sel_r = pygame.Rect(int(rect.x + 4 + pos * w), rect.y + 4, int(w), rect.h - 8)
        gfx.rrect(self.surf, sel_r, (*gfx.ORANGE, 255), 6)
        gfx.rrect(self.surf, (sel_r.x, sel_r.bottom - 4, sel_r.w, 4), (*gfx.mul_col(gfx.ORANGE, 0.65), 255), 2)
        result = selected
        for i, opt in enumerate(options):
            r = pygame.Rect(int(rect.x + 4 + i * w), rect.y, int(w), rect.h)
            h = self.hover(r)
            if h:
                self.hot_any = True
                self.frame_hover = (wid, i)
                if self.pressed:
                    self.active = (wid, i)
            col = TEXT if (i == selected or h) else MUTED
            gfx.text(self.surf, str(opt), r.center, size, "b", col, anchor="center", max_w=r.w - 4)
            if self.released and self.active == (wid, i) and h and i != selected:
                result = i
                if self.audio:
                    self.audio.play("ui")
        return result

    # ------------------------------------------------------------ slider
    def slider(self, wid, rect, value, color=gfx.ORANGE):
        rect = pygame.Rect(rect)
        h = self.hover(rect.inflate(0, 20))
        if h:
            self.hot_any = True
            if self.pressed:
                self.active = wid
        if self.active == wid and self.down:
            value = gfx.clamp((self.mx - rect.x) / rect.w, 0.0, 1.0)
        cy = rect.centery
        gfx.rrect(self.surf, (rect.x - 4, cy - 8, rect.w + 8, 16), (*gfx.PANEL_LO, 255), 6, border=gfx.LINE, bw=4)
        fw = int(rect.w * value)
        if fw > 2:
            gfx.rrect(self.surf, (rect.x, cy - 4, fw, 8), (*color, 255), 2)
        kx = rect.x + fw
        hv = self.anim(wid, 1.0 if (h or self.active == wid) else 0.0)
        kr = pygame.Rect(0, 0, 18, 26 + int(4 * hv))
        kr.center = (kx, cy)
        gfx.rrect(self.surf, kr.move(0, 3), (0, 0, 0, 110), 4)
        gfx.rrect(self.surf, kr, (255, 255, 255, 255), 4, border=gfx.LINE, bw=4)
        return value

    # ---------------------------------------------------- entrada texto
    def text_input(self, wid, rect, text, size=18, color=gfx.GOLD, align="center", placeholder=""):
        """Devuelve (texto, confirmado)."""
        rect = pygame.Rect(rect)
        h = self.hover(rect)
        committed = False
        if h:
            self.hot_any = True
        if self.pressed:
            if h:
                if self.focus != wid:
                    self.focus = wid
                    text = ""
                    pygame.key.start_text_input()
            elif self.focus == wid:
                self.focus = None
                committed = True
        focused = self.focus == wid
        if focused:
            for ch in self.typed:
                if len(text) < 14 and (ch.isdigit() or ch in ".,kKmMbBtTqQaAiI"):
                    text += ch
            for k in self.keys:
                if k == pygame.K_BACKSPACE:
                    text = text[:-1]
                elif k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE, pygame.K_TAB):
                    self.focus = None
                    committed = True
        fv = self.anim((wid, "f"), 1.0 if focused else 0.0)
        border = gfx.lerp_col(gfx.LINE, gfx.ORANGE, fv)
        gfx.rrect(self.surf, rect, (24, 30, 34, 255), 8, border=border, bw=4)
        shown = text if (text or focused) else placeholder
        if align == "center":
            r = gfx.text(self.surf, shown, rect.center, size, "b", color if text else DIM, anchor="center")
        else:
            r = gfx.text(self.surf, shown, (rect.x + 12, rect.centery), size, "b", color if text else DIM,
                         anchor="midleft")
        if focused and int(self.t * 2.2) % 2 == 0:
            x = r.right + 2 if text else rect.centerx
            pygame.draw.rect(self.surf, color, (x + 2, rect.centery - 8, 4, 16))
        return text, committed

    # ------------------------------------------------------------- scroll
    def begin_scroll(self, wid, rect, content_h):
        rect = pygame.Rect(rect)
        st = self.scrolls.setdefault(wid, {"y": 0.0, "target": 0.0})
        max_y = max(0, content_h - rect.h)
        if self.hover(rect) and self.wheel:
            st["target"] -= self.wheel * 70
        st["target"] = gfx.clamp(st["target"], 0, max_y)
        st["y"] = gfx.approach(st["y"], st["target"], self.dt, 16)
        if abs(st["y"] - st["target"]) < 0.5:
            st["y"] = st["target"]
        st["max"] = max_y
        st["rect"] = rect
        st["content"] = content_h
        self.push_clip(rect)
        return int(st["y"])

    def end_scroll(self, wid):
        st = self.scrolls[wid]
        self.pop_clip()
        rect = st["rect"]
        if st["max"] > 0:
            track = pygame.Rect(rect.right - 6, rect.y + 4, 4, rect.h - 8)
            th = max(30, track.h * rect.h / st["content"])
            ty = track.y + (track.h - th) * (st["y"] / st["max"])
            thumb = pygame.Rect(track.x - 2, int(ty), 8, int(th))
            h = self.hover(thumb.inflate(8, 0))
            if h and self.pressed:
                self.drag = (wid, self.my, st["target"])
            if self.drag and self.drag[0] == wid and self.down:
                dy = self.my - self.drag[1]
                st["target"] = gfx.clamp(self.drag[2] + dy * st["content"] / rect.h, 0, st["max"])
                st["y"] = st["target"]
            hv = self.anim((wid, "sb"), 1.0 if (h or self.hover(rect)) else 0.3)
            gfx.rrect(self.surf, thumb, (*gfx.lerp_col((90, 104, 112), (200, 210, 214), hv), 255), 2)

    def scroll_to_top(self, wid):
        if wid in self.scrolls:
            self.scrolls[wid]["target"] = 0
            self.scrolls[wid]["y"] = 0
