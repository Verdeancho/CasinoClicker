"""Ventana principal (pygame, estética indie-retro): clicker, negocios, pestañas, juegos, oportunidades,
mercado negro, bolsa, VIP, logros."""
import math
import os
import random
import time
from collections import deque

import pygame

from . import data, gfx, icons, art, skins
from .extra import T
from .audio import Audio
from .data import (BUILDINGS, GAMES, GAME_BY_ID, UPGRADES, UPGRADE_BY_ID, VIP_PERKS, RTP_CAP, HINTS, UNIQUES,
                   UNIQUE_BY_ID, RARITIES, RARITY_NAME, RARITY_COL, FEATS, CHEATS, THEMES, BUILDING_TIERS)
from .fmt import fmt_money, fmt_num, fmt_int, fmt_time
from .fx import FX
from .gfx import (W, H, TEXT, MUTED, DIM, GOLD, GOLD_HI, GOLD_DK, GREEN, RED, BLUE, PURPLE, ORANGE, PANEL, PANEL_HI,
                  PANEL_LO, LINE, INK)
from .games import common as games_common
from .state import GameState
from .ui import UI

TOP_H = 78
LEFT = pygame.Rect(14, 86, 320, 798)
CENTER = pygame.Rect(346, 86, 900, 798)
RIGHT = pygame.Rect(1258, 86, 328, 798)
CONTENT = pygame.Rect(CENTER.x + 16, CENTER.y + 66, CENTER.w - 32, CENTER.h - 80)
COIN_C = (LEFT.centerx, LEFT.y + 222)
COIN_SIZE = 232

CAT_ICON = {"click": "click", "casino": "chip", "business": "business", "golden": "golden"}
CAT_COL = {"click": ORANGE, "casino": RED, "business": GREEN, "golden": (120, 210, 120)}
TABS = [("casino", "Casino", "chip"), ("upgrades", "Mejoras", "upgrade"), ("market", "Bolsa", "stats"),
        ("vip", "VIP", "crown"), ("achievements", "Logros", "trophy"), ("stats", "Datos", "cards")]
SHIELD_COL = (120, 200, 255)
MAX_CPS = 25  # clics por segundo en la moneda: frena los autoclickers, un jitter o butterfly no llega
WIN_SCALES = (0.5, 0.6, 0.67, 0.75, 0.8, 0.9, 1.0, 1.1, 1.25, 1.5, 1.75, 2.0)
INFO_DELAY = 1.0  # segundos con el ratón encima para ver la descripción completa


def b_col(b):
    return gfx.hexc(b.color)


def g_col(g):
    return gfx.hexc(g.color)


def draw_shield(surf, c, r, col=SHIELD_COL):
    x, y = c
    pts = [(x - r, y - r * 0.8), (x, y - r * 1.1), (x + r, y - r * 0.8), (x + r * 0.85, y + r * 0.3), (x, y + r * 1.1),
           (x - r * 0.85, y + r * 0.3)]
    pygame.draw.polygon(surf, INK, [(px, py + 3) for px, py in pts])
    pygame.draw.polygon(surf, col, pts)
    pygame.draw.polygon(surf, INK, pts, 3)
    pygame.draw.line(surf, (255, 255, 255), (x, y - r * 0.8), (x, y + r * 0.7), 3)


class App:
    def __init__(self, save_path, headless=False):
        self.save_path = save_path
        os.environ.setdefault("SDL_WINDOWS_DPI_AWARENESS", "permonitorv2")
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.init()
        # el juego se dibuja siempre en un lienzo de 1600x900 que se escala al tamaño de la ventana (present)
        self.window = pygame.display.set_mode((W, H), 0 if headless else pygame.RESIZABLE)
        self.screen = self.window if headless else pygame.Surface((W, H)).convert()
        self.view = pygame.Rect(0, 0, W, H)
        self._scaled = None
        pygame.display.set_caption("Casino Clicker")
        try:
            pygame.display.set_icon(icons.icon("chip", 64))
        except pygame.error:
            pass
        self.headless = headless
        self.clock = pygame.time.Clock()
        self.state = GameState.load(save_path)
        self.state.review()
        if self.state.flags.get("s2") and not headless:
            pygame.display.set_caption(T["cap"])
        self._win_applied = 0.0
        if not headless:
            self.apply_window()
        self.audio = Audio(self.state.settings)
        self.ui = UI(self.audio)
        self.ui.map_pos = self.to_canvas
        self.fx = FX()
        from .market import Market
        self.market = Market(self.state)
        self.running = True
        self.tab = "casino"
        self.current_game = None
        self.games = {}
        self.game_panel = None
        self.buy_qty = 0
        self.upg_filter = 0
        self.upg_view = 0
        self.money_disp = self.state.money
        self.money_pop = 0.0
        self.coin_scale = 1.0
        self.coin_vel = 0.0
        self.ray_angle = 0.0
        self.auto_acc = 0.0
        self.click_times = deque()
        self.slow_hint = 0.0
        self.auto_fx_acc = 0.0
        self.golden = None
        self.next_golden = time.time() + random.uniform(60, 100)
        self.toasts = []
        self.logs = []
        self.modal = None
        self.bm_pick = [None, None]
        self.mk_qty = "1"
        self.last_save = time.time()
        self.last_ach = time.time()
        self.last_level = self.state.player_level()
        self._aff_cache = (0, 0)
        self.log("¡Bienvenido a Casino Clicker! Pulsa la moneda para ganar tus primeros céntimos.", GOLD)
        if self.state.flags.pop("_migrated", None):
            self.toast("¡Nueva versión!", "La economía ha cambiado por completo: empiezas de cero. Tu partida "
                                         "anterior se ha guardado aparte.", GOLD, "star")
        self.offline_earnings()
        if self.state.flags.get("s4") and not self.state.flags.get("s3"):
            self.open_game("lastbet")

    # ------------------------------------------------------------ ventana
    def fit_scale(self):
        """Escala más grande con la que la ventana cabe entera en la pantalla."""
        try:
            dw, dh = pygame.display.get_desktop_sizes()[0]
        except Exception:
            return 1.0
        return max(0.3, min((dw - 40) / W, (dh - 110) / H))

    @staticmethod
    def _window():
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            return pygame.Window.from_display_module()

    def window_scale(self):
        k = self.state.settings.get("win_scale")
        return min(1.0, self.fit_scale()) if k is None else k

    def apply_window(self):
        """Aplica el tamaño de ventana de los ajustes. El juego se dibuja siempre a 1600x900 y se escala."""
        if self.headless:
            return
        st = self.state.settings
        self._win_applied = time.time()
        try:
            win = self._window()
            win.minimum_size = (W // 4, H // 4)
            if st.get("fullscreen"):
                win.set_fullscreen(True)
                return
            win.set_windowed()
            k = self.window_scale()
            win.size = (int(W * k), int(H * k))
            win.position = pygame.WINDOWPOS_CENTERED
        except Exception:
            pass

    def present(self):
        """Escala el lienzo a la ventana (con bandas negras si no tiene la misma proporción) y lo muestra."""
        win = pygame.display.get_surface()
        ww, wh = win.get_size()
        k = min(ww / W, wh / H)
        size = (max(1, round(W * k)), max(1, round(H * k)))
        self.view = pygame.Rect(0, 0, *size)
        self.view.center = (ww // 2, wh // 2)
        if size == (W, H):
            win.blit(self.screen, self.view)
        else:
            if self._scaled is None or self._scaled.get_size() != size:
                self._scaled = pygame.Surface(size).convert()
            pygame.transform.smoothscale(self.screen, size, self._scaled)
            if self.view.size != (ww, wh):
                win.fill((0, 0, 0))
            win.blit(self._scaled, self.view)
        pygame.display.flip()

    def to_canvas(self, pos):
        """Posición del ratón en la ventana -> posición en el lienzo de 1600x900."""
        v = self.view
        if self.headless or v.size == (W, H) and v.topleft == (0, 0):
            return pos
        return (int((pos[0] - v.x) * W / v.w), int((pos[1] - v.y) * H / v.h))

    def set_window_scale(self, k):
        self.state.settings["win_scale"] = k
        self.state.settings["fullscreen"] = False
        self.apply_window()

    def toggle_fullscreen(self):
        st = self.state.settings
        st["fullscreen"] = not st.get("fullscreen")
        self.apply_window()

    def on_window_resized(self):
        """Si el jugador estira la ventana a mano, se recuerda ese tamaño."""
        if self.headless or self.state.settings.get("fullscreen") or time.time() - self._win_applied < 1.0:
            return
        try:
            win = self._window()
            self.state.settings["win_scale"] = round(win.size[0] / W, 3)
        except Exception:
            pass

    # ================================================================ util
    def log(self, text, color=TEXT):
        self.logs.insert(0, {"text": text, "color": color, "age": 0.0})
        del self.logs[40:]

    def toast(self, title, text, color=GOLD, icon="star"):
        self.toasts.append({"title": title, "text": text, "color": color, "icon": icon, "age": 0.0, "life": 5.0})
        if len(self.toasts) > 4:
            self.toasts.pop(0)

    def float_text(self, text, color=GREEN):
        self.fx.text(COIN_C[0], COIN_C[1] - 140, text, color, 24)

    def save_now(self, quiet=True):
        try:
            self.market.save()
            self.state.save(self.save_path)
            self.last_save = time.time()
            if not quiet:
                self.toast("Partida guardada", "Tu progreso está a salvo.", GREEN, "star")
        except OSError as e:
            self.log(f"Error al guardar: {e}", RED)

    def offline_earnings(self):
        s = self.state
        elapsed = time.time() - s.last_time
        if elapsed > 60:
            secs = min(elapsed, s.offline_cap())
            amount = s.income_per_sec() * secs * s.offline_rate()
            if amount > 0:
                s.earn(amount, "passive")
                self.money_disp = s.money
                msg = f"En {fmt_time(elapsed)} tus negocios ganaron {fmt_money(amount)}."
                self.log(msg, GREEN)
                self.toast("¡Bienvenido de nuevo!", msg, GREEN, "business")

    # ================================================================ loop
    def run(self):
        while self.running:
            dt = min(0.05, self.clock.tick(144) / 1000.0)
            events = pygame.event.get()
            for e in events:
                if e.type == pygame.QUIT:
                    self.running = False
                elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                    if self.takeover():
                        pass
                    elif self.modal:
                        self.modal = None
                    elif self.game_panel:
                        self.game_panel = None
                elif e.type == pygame.KEYDOWN and e.key == pygame.K_F11:
                    self.toggle_fullscreen()
                elif e.type == pygame.WINDOWSIZECHANGED:
                    self.on_window_resized()
            self.step(events, dt)
            self.present()
        self.save_now()
        pygame.quit()

    def takeover(self):
        g = self.games.get(self.current_game) if self.current_game else None
        return g if g is not None and getattr(g, "takeover", None) and g.takeover() else None

    def step(self, events, dt):
        self.update(dt)
        self.ui.modal = bool(self.modal) or bool(self.takeover())
        self.ui._in_modal = False
        self.ui.begin(self.screen, events, dt)
        self.draw(dt)
        self.ui.end()

    # ============================================================== update
    def update(self, dt):
        s = self.state
        now = time.time()
        s.stats["play_time"] += dt
        s.tick_buffs()
        games_common.THEME["felt"] = s.theme_felt
        ips = s.income_per_sec()
        if ips > 0:
            s.earn(ips * dt, "passive")
        acps = s.autoclicks_per_sec()
        if acps > 0:
            self.auto_acc += acps * dt
            n = int(self.auto_acc)
            if n:
                self.auto_acc -= n
                s.stats["auto_clicks"] += n
                s.earn(s.autoclick_value() * n, "auto")
                self.auto_fx_acc += n
                if self.auto_fx_acc >= max(1, acps / 4):
                    self.auto_fx_acc = 0
                    self.fx.coins(COIN_C[0] + random.uniform(-60, 60), COIN_C[1] - 40, 1, 0.6, 18)
        s.decay_combo()
        self.market.update(dt)
        hev = s.update_hot()
        if hev == "new":
            gname = GAME_BY_ID[s.hot["gid"]].name
            self.audio.play("unlock")
            self.toast("¡Mesa caliente!", f"{gname}: tus ganancias valen x{fmt_num(s.hot_mult())} durante "
                       f"{int(s.hot['dur'])} s. Bote: {fmt_money(s.hot['pot'])}.", GOLD, s.hot["gid"])
            self.log(f"Mesa caliente: {gname} (bote {fmt_money(s.hot['pot'])})", GOLD)
        elif hev == "empty":
            self.toast("¡Bote vaciado!", "Te has llevado todo el bote de la mesa caliente.", GOLD, "golden")
        ev = s.update_opportunity()
        if ev == "new":
            u = UNIQUE_BY_ID[s.opp["uid"]]
            self.audio.play("unlock" if u.rarity in ("epic", "legendary") else "sparkle")
            self.toast(f"Oportunidad {RARITY_NAME[u.rarity].lower()}", f"{u.name}: {u.desc} "
                       f"Precio {fmt_money(s.opp['price'])}.", RARITY_COL[u.rarity], "business")
            self.log(f"Oportunidad: {u.name} por {fmt_money(s.opp['price'])}", RARITY_COL[u.rarity])
        elif ev == "expired":
            self.log("La oportunidad se ha esfumado.", DIM)
        self.coin_vel += (1.0 - self.coin_scale) * 900 * dt
        self.coin_vel *= math.exp(-16 * dt)
        self.coin_scale += self.coin_vel * dt
        self.ray_angle = (self.ray_angle + dt * 10) % 360
        old = self.money_disp
        if abs(s.money - self.money_disp) < max(0.005, abs(s.money) * 1e-6):
            self.money_disp = s.money
        else:
            self.money_disp = gfx.approach(self.money_disp, s.money, dt, 9)
        if s.money - old > max(0.5, abs(old) * 0.002) and self.money_disp > old:
            self.money_pop = min(1.0, self.money_pop + 0.25)
        self.money_pop = max(0.0, self.money_pop - dt * 3)
        self.update_golden(now, dt)
        self.fx.update(dt)
        for t in self.toasts:
            t["age"] += dt
        self.toasts = [t for t in self.toasts if t["age"] < t["life"]]
        for lg in self.logs:
            lg["age"] += dt
        while s.events:
            kind, text, color = s.events.pop(0)
            if kind == "error":
                self.audio.play("error")
                g = self.games.get(self.current_game) if self.tab == "casino" else None
                if g:
                    g.show(text, RED)
                    continue
            if kind == "news":
                self.audio.play("tick2", 0.8)
                self.toast("Noticia en el buzón", text, (150, 200, 255), "mail")
                continue
            if kind == "milestone":
                m = data.MARKET_MILESTONE_BY_ID[text]
                self.audio.play("achievement")
                self.toast(f"¡Hito! {m[1]}", m[3], (150, 200, 255), "stats")
                self.log(f"Hito de la bolsa: {m[1]}", (150, 200, 255))
                continue
            if kind == "shield":
                self.audio.play("unlock")
                self.toast("Escudo", text, SHIELD_COL, "star")
            self.log(text, color if isinstance(color, tuple) else TEXT)
        if now - self.last_ach > 1.0:
            self.last_ach = now
            lvl = s.player_level()
            if lvl > self.last_level:
                self.level_up(self.last_level, lvl)
                self.last_level = lvl
            for f in s.check_feats():
                u = UPGRADE_BY_ID[f.reward]
                self.audio.play("achievement")
                self.toast(f"¡Hazaña! {f.name}", f"{GAME_BY_ID[f.game].name}: consigues «{u.name}».", ORANGE, f.game)
                self.log(f"Hazaña: {f.name} → {u.name}", ORANGE)
            new = s.check_achievements()
            for a in new:
                self.log(f"Logro: {a.name}", GOLD)
            if len(new) == 1:
                self.toast("Logro desbloqueado", f"{new[0].name} — {new[0].desc}", GOLD, "trophy")
            elif new:
                self.toast(f"{len(new)} logros desbloqueados", ", ".join(a.name for a in new[:5]), GOLD, "trophy")
            if new:
                self.audio.play("achievement")
        if now - self.last_save > 30:
            self.save_now()

    def level_up(self, old, lvl):
        s = self.state
        s.invalidate()
        parts = [f"Ventajas cada {fmt_time(s.hint_cooldown('coinflip'))}."]
        if s.title(lvl) != s.title(old):
            parts.insert(0, f"Nuevo título: {s.title(lvl)}.")
        for attr, word in (("theme_coin", "Moneda nueva"), ("theme_felt", "Tapete nuevo")):
            for tid, tl in data.THEME_LEVELS[attr].items():
                if old < tl <= lvl:
                    parts.append(f"{word}: {data.theme_name(tid, attr)}.")
        from .market import ASSETS
        if old < data.MARKET_LEVEL <= lvl:
            parts.append("¡Se abre la Bolsa!")
        for a in ASSETS:
            if old < a[2] <= lvl and a[2] > data.MARKET_LEVEL:
                parts.append(f"Nuevo valor en bolsa: {a[1]}.")
        if old < data.SHORT_LEVEL <= lvl:
            parts.append("Ya puedes vender en corto.")
        if s.grant_level_shields():
            parts.append("¡Regalo: un escudo!")
        self.toast(f"¡Nivel de jugador {lvl}!", " ".join(parts), BLUE, "upgrade")
        self.log(f"Nivel {lvl} ({s.title(lvl)})", BLUE)
        self.audio.play("unlock")

    # =============================================================== draw
    def draw(self, dt):
        surf = self.screen
        gfx.swirl_bg(surf, self.ui.t)
        self.draw_topbar(surf)
        gfx.panel(surf, LEFT)
        gfx.panel(surf, CENTER)
        gfx.panel(surf, RIGHT)
        self.draw_clicker(surf)
        self.draw_business(surf)
        self.draw_center(surf, dt)
        self.draw_golden(surf)
        ox, oy = self.fx.shake_offset()
        if ox or oy:
            surf.scroll(int(ox), int(oy))
        self.fx.draw(surf)
        self.draw_toasts(surf)
        if self.modal:
            self.ui._in_modal = True
            self.draw_modal(surf)
        tk = self.takeover()
        if tk:
            self.ui._in_modal = True
            tk.draw_takeover(surf)

    # ------------------------------------------------------------ top bar
    def draw_topbar(self, surf):
        s = self.state
        ui = self.ui
        surf.blit(icons.icon("chip", 48), (18, 14))
        gfx.wavy_text(surf, "CASINO", (76, 12), 22, ORANGE, ui.t, 2, 4, anchor="topleft", weight="bl")
        alt = bool(s.flags.get("s2"))
        gfx.wavy_text(surf, T["logo"] if alt else "CLICKER", (76, 40), 22, RED if alt else TEXT, ui.t + 1, 2, 4,
                      anchor="topleft", weight="bl")
        mb = pygame.Rect(CENTER.x, 8, 430, 64)
        gfx.box(surf, mb, (*PANEL_LO, 255), 10, ow=4, shadow_off=5)
        k = 1 + 0.12 * self.money_pop
        img = gfx.text_surf(fmt_money(self.money_disp), 32, "bl", GOLD_HI)
        if k > 1.01:
            img = gfx.scaled(img, k)
        surf.blit(img, img.get_rect(midleft=(mb.x + 14, mb.centery)))
        tot = s.total_passive()
        gfx.text(surf, f"+{fmt_money(tot)}/s", (mb.right - 14, mb.y + 22), 12, "b", GREEN, anchor="midright")
        ui.tooltip("ips", mb, f"Ingresos pasivos: {fmt_money(tot)}/s\n"
                              f"Negocios: {fmt_money(s.income_per_sec())}/s\n"
                              f"Auto-clics: {fmt_money(s.auto_income_per_sec())}/s "
                              f"({fmt_int(s.autoclicks_per_sec())} por segundo)")
        boost = s.buff_mult("click_x2") > 1
        gfx.text(surf, "¡CLICS x2!" if boost else "por segundo", (mb.right - 14, mb.y + 44), 12, "r",
                 ORANGE if boost else DIM, anchor="midright")
        # nivel de jugador
        lvl, prog, nxt = s.level_progress()
        lb = pygame.Rect(mb.right + 12, 8, 250, 64)
        gfx.box(surf, lb, (*PANEL_LO, 255), 10, ow=4, shadow_off=5)
        gfx.text(surf, f"NIVEL {lvl}", (lb.x + 14, lb.y + 18), 16, "bl", BLUE, anchor="midleft")
        gfx.text(surf, s.title(), (lb.right - 14, lb.y + 18), 12, "b", MUTED, anchor="midright", max_w=110)
        bar = pygame.Rect(lb.x + 14, lb.y + 36, lb.w - 28, 14)
        gfx.rrect(surf, bar, (20, 26, 30, 255), 4)
        fw = int(bar.w * gfx.clamp(prog, 0, 1))
        if fw > 3:
            gfx.rrect(surf, (bar.x, bar.y, fw, bar.h), (*BLUE, 255), 4)
        nshield = min((n for n in data.SHIELD_LEVELS if n > lvl), default=None)
        ui.tooltip("lvl", lb, f"Nivel de jugador {lvl} · {s.title()}\n"
                              "Sube apostando: cuenta lo que la casa espera ganarte, ganes o pierdas.\n"
                              f"Ventajas de los juegos: se recargan cada {fmt_time(s.hint_cooldown('coinflip'))}.\n"
                              + (f"Próximo escudo de regalo: nivel {nshield}.\n" if nshield else "")
                              + f"Experiencia: {fmt_num(s.stats.get('xp', 0))} / {fmt_num(nxt)}")
        x = lb.right + 12
        # mesa caliente
        if s.hot:
            h = s.hot
            rem = s.hot_remaining()
            gname = GAME_BY_ID[h["gid"]].name
            sub_t = f"{fmt_money(h['pot'])} · {int(rem) // 60}:{int(rem) % 60:02d}"
            r = pygame.Rect(x, 8, max(gfx.text_w(gname, 12, "b"), gfx.text_w(sub_t, 12)) + 62, 64)
            pulse = 0.5 + 0.5 * math.sin(ui.t * 5)
            gfx.box(surf, r, (*gfx.lerp_col((90, 60, 10), (150, 104, 20), pulse), 255), 10, outline=GOLD, ow=4,
                    shadow_off=5)
            surf.blit(icons.icon(h["gid"], 36), (r.x + 10, r.y + 14))
            gfx.text(surf, gname, (r.x + 52, r.y + 22), 12, "b", GOLD_HI, anchor="midleft")
            gfx.text(surf, sub_t, (r.x + 52, r.y + 44), 12, "r", TEXT, anchor="midleft")
            ui.tooltip("hot_tip", r, f"Mesa caliente: {gname}\nTus ganancias valen x{fmt_num(s.hot_mult())} hasta "
                                     "que se acabe el tiempo o el bote.\nPulsa para ir a la mesa.")
            if ui.clicked_area("hot_go", r, sound="tab") and h["gid"] in s.games_unlocked:
                self.tab = "casino"
                self.open_game(h["gid"])
            x = r.right + 10
        # escudos
        if s.shields or s.shield_armed:
            armed = s.shield_armed
            compact = bool(s.hot)
            if compact:
                r = pygame.Rect(x, 8, 96, 64)
            else:
                r = pygame.Rect(x, 8, max(gfx.text_w(f"ESCUDO x{s.shields}", 12, "b"),
                                          gfx.text_w("pulsa para activar", 12)) + 66, 64)
            hov = ui.hover(r) and not armed
            gfx.box(surf, r, (*(gfx.lerp_col(PANEL_LO, SHIELD_COL, 0.35) if armed else
                                gfx.lerp_col(PANEL_LO, (70, 90, 110), 0.6 if hov else 0.0)), 255), 10, ow=4,
                    shadow_off=5, outline=SHIELD_COL if armed else None)
            draw_shield(surf, (r.x + 28, r.centery), 15)
            if compact:
                gfx.text(surf, f"x{s.shields}", (r.x + 52, r.y + 22), 14, "b", TEXT, anchor="midleft")
                gfx.text(surf, "ON" if armed else "OFF", (r.x + 52, r.y + 44), 12, "b",
                         SHIELD_COL if armed else MUTED, anchor="midleft")
            else:
                gfx.text(surf, f"ESCUDO x{s.shields}", (r.x + 52, r.y + 22), 12, "b", TEXT, anchor="midleft")
                gfx.text(surf, "ACTIVO" if armed else "pulsa para activar", (r.x + 52, r.y + 44), 12, "r",
                         SHIELD_COL if armed else MUTED, anchor="midleft")
            ui.tooltip("shield", r, "Escudo: si pierdes tu próxima apuesta, te devuelve lo apostado y se gasta.\n"
                                    "Si ganas, se queda activo para la siguiente." +
                       ("" if armed else "\nPulsa para activarlo."))
            if not armed and ui.clicked_area("shield_btn", r, sound="ui"):
                if s.arm_shield():
                    self.toast("Escudo activado", "Tu próxima apuesta perdida te será devuelta.", SHIELD_COL, "star")
            x = r.right + 10
        rx = W - 16
        if ui.button("settings", (rx - 48, 12, 48, 56), "", "dark", icon="gear", tooltip="Ajustes"):
            self.modal = "settings"
        rx -= 56
        muted = s.settings.get("muted")
        if ui.button("mute", (rx - 48, 12, 48, 56), "", "dark", icon="sound_off" if muted else "sound_on",
                     tooltip="Silenciar / activar sonido"):
            s.settings["muted"] = not muted
            self.audio.apply_music()
        rx -= 56
        if ui.button("looks", (rx - 48, 12, 48, 56), "", "dark", icon="palette", tooltip="Aspecto: moneda y tapetes"):
            self.modal = "appearance"
        rx -= 56
        if (s.prestige_level or s.claimable_chips()) and rx - x > 120:
            txt = f"{s.vip_chips} fichas"
            w = gfx.text_w(txt, 14, "b") + 56
            r = pygame.Rect(rx - w, 8, w, 64)
            gfx.box(surf, r, (*gfx.PURPLE_DK, 255), 10, ow=4, shadow_off=5)
            surf.blit(icons.icon("crown", 30), (r.x + 10, r.y + 17))
            gfx.text(surf, txt, (r.x + 46, r.centery), 14, "b", TEXT, anchor="midleft")
            ui.tooltip("vipchips", r, f"Fichas VIP: {s.vip_chips}\nNivel de prestigio: {s.prestige_level} "
                                      f"(+{s.prestige_level * 2}%)")

    # ------------------------------------------------------------ clicker
    def draw_clicker(self, surf):
        s = self.state
        ui = self.ui
        cx, cy = COIN_C
        gfx.wavy_text(surf, "PULSA LA MONEDA", (LEFT.centerx, LEFT.y + 26), 12, MUTED, ui.t, 2, 3)
        rot = pygame.transform.rotate(self._rays(), self.ray_angle)
        surf.blit(rot, rot.get_rect(center=(cx, cy)), special_flags=pygame.BLEND_RGB_ADD)
        boost = s.buff_mult("click_x2") > 1
        hover = ui.hover(pygame.Rect(cx - 112, cy - 112, 224, 224)) and math.hypot(ui.mx - cx, ui.my - cy) < 112
        if hover:
            ui.hot_any = True
            if ui.pressed:
                self.click_coin(ui.mx, ui.my)
        hv = ui.anim("coin_hover", 1.0 if hover else 0.0, 10)
        sc = self.coin_scale * (1 + 0.03 * hv)
        wob = math.sin(ui.t * 1.6) * 3
        coin = skins.coin_skin(s.theme_coin, COIN_SIZE, boost)
        img = gfx.scaled(coin, sc)
        if abs(wob) > 0.5:
            img = pygame.transform.rotate(img, wob)
        gfx.rrect(surf, (cx - 90, cy + COIN_SIZE * 0.5 - 4, 180, 18), (0, 0, 0, 90), 8)
        if boost:
            gfx.glow(surf, (cx, cy), 150, (255, 120, 60), 0.35 + 0.1 * math.sin(ui.t * 6))
        gfx.blit_center(surf, img, (cx, cy + math.sin(ui.t * 2.1) * 3))
        if self.slow_hint > ui.t:
            gfx.text(surf, f"máx. {MAX_CPS} clics por segundo", (cx, cy + COIN_SIZE * 0.5 + 16), 10, "b", MUTED,
                     anchor="center")
        # combo
        cap = s.combo_cap()
        y = LEFT.y + 372
        fv = ui.anim("combo_bar", s.combo / cap if cap else 0, 10)
        gfx.text(surf, "COMBO", (LEFT.x + 22, y), 12, "b", MUTED)
        gfx.text(surf, f"+{s.combo}%" if s.combo else "clic rápido", (LEFT.right - 22, y), 12, "b",
                 ORANGE if s.combo else DIM, anchor="topright")
        bar = pygame.Rect(LEFT.x + 22, y + 22, LEFT.w - 44, 16)
        gfx.rrect(surf, bar, (20, 26, 30, 255), 4, border=LINE, bw=2)
        if fv > 0.005:
            col = gfx.lerp_col(ORANGE, RED, fv)
            gfx.rrect(surf, (bar.x + 2, bar.y + 2, max(6, int((bar.w - 4) * fv)), bar.h - 4), (*col, 255), 2)
        info = f"{fmt_money(s.click_value())} por clic"
        cr = s.crit_chance()
        if cr:
            info += f" · crítico {cr * 100:.0f}%"
        gfx.text(surf, info, (LEFT.centerx, y + 50), 12, "r", MUTED, anchor="midtop", max_w=LEFT.w - 30)
        # oportunidad / registro
        ly = LEFT.y + 452
        if s.opp:
            oh = 226
            self.draw_opportunity(surf, pygame.Rect(LEFT.x + 14, ly, LEFT.w - 28, oh))
            ly += oh + 10
        lr = pygame.Rect(LEFT.x + 14, ly, LEFT.w - 28, LEFT.bottom - ly - 14)
        gfx.rrect(surf, lr, (*PANEL_LO, 255), 8, border=LINE, bw=4)
        gfx.text(surf, "REGISTRO", (LEFT.x + 28, ly + 12), 12, "b", MUTED)
        if s.bm_unlocked():
            br = pygame.Rect(lr.right - 44, lr.y + 6, 34, 30)
            ready = s.bm_ready()
            hv2 = ui.anim("bm_hov", 1.0 if ui.hover(br) else 0.0, 12)
            col = gfx.lerp_col((60, 40, 70), (150, 80, 190), max(hv2, 0.5 + 0.5 * math.sin(ui.t * 3) if ready else 0))
            gfx.rrect(surf, br, (*col, 255), 6, border=INK, bw=3)
            pygame.draw.polygon(surf, (20, 14, 26), [(br.x + 7, br.y + 19), (br.right - 7, br.y + 19),
                                                     (br.centerx + 6, br.y + 9), (br.centerx - 6, br.y + 9)])
            pygame.draw.rect(surf, (20, 14, 26), (br.x + 4, br.y + 19, br.w - 8, 4))
            ui.tooltip("bm_tip", br, "Mercado negro" + ("" if ready else f"\nEl mercader vuelve en {fmt_time(s.bm_remaining())}"))
            if ui.clicked_area("bm_open", br, sound="ui"):
                self.open_black_market()
        y = ly + 36
        for lg in self.logs:
            lines = gfx.wrap(lg["text"], 12, "r", LEFT.w - 70)
            lh = gfx.line_height(12)
            hgt = len(lines) * lh + 6
            if y + hgt > LEFT.bottom - 22:
                break
            a = min(255, int(lg["age"] * 900))
            surf.fill(lg["color"], (LEFT.x + 26, y + 6, 6, 6))
            for i, ln in enumerate(lines):
                gfx.text(surf, ln, (LEFT.x + 40, y + i * lh), 12, "r", gfx.lerp_col(MUTED, lg["color"], 0.5),
                         alpha=a)
            y += hgt

    def draw_opportunity(self, surf, r):
        s = self.state
        ui = self.ui
        o = s.opp
        u = UNIQUE_BY_ID[o["uid"]]
        col = RARITY_COL[u.rarity]
        pulse = 0.5 + 0.5 * math.sin(ui.t * (6 if u.rarity == "legendary" else 3))
        if u.rarity in ("epic", "legendary"):
            gfx.glow(surf, r.center, r.w // 2 + 20, col, 0.18 + 0.12 * pulse)
        gfx.box(surf, r, (*gfx.lerp_col(PANEL_LO, col, 0.16), 255), 10, outline=col, ow=4, shadow_off=5)
        head = pygame.Rect(r.x + 4, r.y + 4, r.w - 8, 30)
        gfx.rrect(surf, head, (*gfx.mul_col(col, 0.6), 255), 6)
        gfx.text(surf, "¡OPORTUNIDAD!", (head.x + 10, head.centery), 12, "bl", TEXT, anchor="midleft")
        rem = s.opp_remaining()
        gfx.text(surf, f"{int(rem)}s", (head.right - 10, head.centery), 12, "b", TEXT, anchor="midright")
        bar = pygame.Rect(r.x + 8, r.y + 38, r.w - 16, 6)
        surf.blit(icons.badge(u.icon, 46, col), (r.x + 12, r.y + 54))
        gfx.text(surf, u.name, (r.x + 68, r.y + 52), 14, "b", TEXT, max_w=r.w - 80)
        gfx.text(surf, f"Única · {RARITY_NAME[u.rarity]}", (r.x + 68, r.y + 74), 10, "b", col)
        lines = gfx.wrap(u.desc, 12, "r", r.w - 80)[:4]
        for i, ln in enumerate(lines):
            gfx.text(surf, ln, (r.x + 68, r.y + 90 + i * 19), 12, "r", MUTED)
        ui.tooltip(("opp", u.id), pygame.Rect(r.x, r.y, r.w, r.h - 56),
                   f"{u.name} ({RARITY_NAME[u.rarity]})\n{u.desc}", INFO_DELAY, title=RARITY_COL[u.rarity])
        price = o["price"]
        can = s.money >= price
        gfx.rrect(surf, bar, (20, 26, 30, 255), 3)
        fw = int(bar.w * rem / max(1, o["dur"]))
        if fw > 2:
            gfx.rrect(surf, (bar.x, bar.y, fw, bar.h), (*col, 255), 3)
        br = pygame.Rect(r.x + 14, r.bottom - 52, r.w - 28, 42)
        sub = fmt_money(price) if can else f"te faltan {fmt_money(price - s.money)}"
        if ui.button("opp_buy", br, "COMPRAR", "gold" if can else "dark", enabled=can, size=13, sub=sub, sound=None):
            uid = s.buy_opportunity()
            if uid:
                self.audio.play("buy_big")
                self.fx.confetti(br.centerx, br.centery, 70, 0.8)
                self.fx.sparks(br.centerx, br.centery, 30, col)
                self.toast("¡Mejora única!", f"{UNIQUE_BY_ID[uid].name}: {UNIQUE_BY_ID[uid].desc}", col, "star")
                self.log(f"Mejora única: {UNIQUE_BY_ID[uid].name}", col)

    def _rays(self):
        if not hasattr(self, "_rays_s"):
            size = 200
            small = pygame.Surface((size, size), pygame.SRCALPHA)
            c = size // 2
            for i in range(12):
                a = i * math.tau / 12
                pts = [(c, c), (c + size * math.cos(a - 0.12), c + size * math.sin(a - 0.12)),
                       (c + size * math.cos(a + 0.12), c + size * math.sin(a + 0.12))]
                pygame.draw.polygon(small, (34, 40, 22), pts)
            mask = pygame.Surface((size, size))
            mask.fill((0, 0, 0))
            for k in range(8, 0, -1):
                v = int(255 * (1 - k / 8) ** 0.8)
                pygame.draw.circle(mask, (v, v, v), (c, c), int(c * k / 8))
            small.blit(mask, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
            self._rays_s = pygame.transform.scale(small, (size * 2, size * 2))
        return self._rays_s

    def click_coin(self, mx, my):
        now = time.perf_counter()
        q = self.click_times
        while q and now - q[0] >= 1.0:
            q.popleft()
        if len(q) >= MAX_CPS:
            self.slow_hint = self.ui.t + 1.5
            return
        q.append(now)
        s = self.state
        v, crit = s.do_click()
        self.coin_scale = 0.88
        self.coin_vel = -1.5
        cap = s.combo_cap()
        idx = min(15, int(s.combo / max(1, cap) * 15))
        self.audio.play(f"click{idx}", throttle=0.01, pan=(mx - W / 2) / W)
        if crit:
            self.audio.play("crit")
            self.fx.sparks(mx, my, 24, (255, 120, 100), 1.4)
            self.fx.add_shake(3)
            self.fx.text(mx, my - 30, f"¡CRÍTICO! +{fmt_money(v)}", RED, 26)
        else:
            self.fx.text(mx + random.uniform(-20, 20), my - 24, f"+{fmt_money(v)}", TEXT, 16)
        self.fx.coins(mx, my, 2 if not crit else 8, 1.0, 20)

    # ------------------------------------------------------- moneda dorada
    def update_golden(self, now, dt):
        g = self.golden
        if g:
            g["age"] += dt
            if g["age"] > g["life"]:
                self.golden = None
                self.schedule_golden(now)
        elif now >= self.next_golden:
            self.golden = {"x": random.uniform(80, W - 80), "y": random.uniform(TOP_H + 60, H - 70), "age": 0.0,
                           "life": 12.0}
            self.audio.play("sparkle", 0.8)

    def schedule_golden(self, now):
        self.next_golden = now + random.uniform(0.6, 1.4) * self.state.golden_interval()

    def draw_golden(self, surf):
        g = self.golden
        if not g:
            return
        t = g["age"]
        appear = gfx.ease_out_back(min(1, t / 0.5))
        fade = 1.0 if t < g["life"] - 2 else max(0.0, (g["life"] - t) / 2)
        x = g["x"]
        y = g["y"] + math.sin(t * 2.4) * 8
        gfx.glow(surf, (x, y), int(70 + 10 * math.sin(t * 5)), (255, 200, 60), 0.8 * fade)
        img = gfx.scaled(art.golden_coin(84), max(0.05, appear * (1 + 0.06 * math.sin(t * 6))))
        img = pygame.transform.rotate(img, math.sin(t * 3) * 10)
        gfx.blit_center(surf, img, (x, y), 255 * fade)
        if random.random() < 0.12:
            self.fx.sparks(x + random.uniform(-30, 30), y + random.uniform(-30, 30), 1, (255, 240, 160), 0.3, 8)
        if self.ui.clicked_area("golden", pygame.Rect(x - 46, y - 46, 92, 92)):
            self.collect_golden(x, y)

    def collect_golden(self, x, y):
        self.golden = None
        self.schedule_golden(time.time())
        s = self.state
        s.stats["golden_clicked"] += 1
        bonus = s.golden_reward_mult()
        roll = random.random()
        if roll < 0.005:
            s.shields += 1
            title, msg = "¡Un escudo!", "Protege una apuesta: si la pierdes, recuperas lo apostado."
            col = SHIELD_COL
        elif roll < 0.70:
            amount = max(s.click_value(0) * 30, min(s.income_per_sec() * 30, s.money * 0.03)) * bonus
            s.earn(amount, "golden")
            title, msg, col = "¡Pellizco de suerte!", f"Ganas {fmt_money(amount)}", GOLD
        else:
            s.add_buff("click_x2", "Clics x2", 2, 20 * bonus)
            title, msg, col = "¡Dedos dorados!", "Tus clics valen el doble durante un rato", GOLD
        self.audio.play("golden")
        self.fx.flash(x, y, 120)
        self.fx.sparks(x, y, 30, (255, 220, 120), 1.6, 12, 1.0)
        self.fx.coins(x, y, 10, 1.2, 20)
        self.fx.text(x, y - 40, title, GOLD_HI, 26)
        self.toast(title, msg, col, "golden")
        self.log(f"{title} {msg}", col)

    # ------------------------------------------------------------ negocios
    def draw_business(self, surf):
        s = self.state
        ui = self.ui
        gfx.text(surf, "NEGOCIOS", (RIGHT.x + 20, RIGHT.y + 22), 16, "bl", ORANGE)
        self.buy_qty = ui.segmented("qty", (RIGHT.right - 196, RIGHT.y + 14, 180, 36), ["1", "10", "100", "MAX"],
                                    self.buy_qty, 12)
        gfx.text(surf, f"{fmt_money(s.income_per_sec())}/s · {s.total_buildings()} negocios",
                 (RIGHT.x + 20, RIGHT.y + 56), 12, "r", MUTED, max_w=RIGHT.w - 40)
        area = pygame.Rect(RIGHT.x + 10, RIGHT.y + 78, RIGHT.w - 20, RIGHT.h - 90)
        highest = max([i for i, b in enumerate(BUILDINGS) if s.buildings.get(b.id, 0) > 0], default=-1)
        visible = max(1, highest + 1)
        rows = [(i, b) for i, b in enumerate(BUILDINGS) if i <= visible + 1]
        row_h = 92
        off = ui.begin_scroll("biz", area, len(rows) * row_h + 8)
        qty_val = [1, 10, 100, -1][self.buy_qty]
        total_ips = s.income_per_sec()
        for k, (i, b) in enumerate(rows):
            r = pygame.Rect(area.x + 2, area.y + 2 + k * row_h - off, area.w - 16, row_h - 12)
            if r.bottom < area.y - 10 or r.y > area.bottom:
                continue
            owned = s.buildings.get(b.id, 0)
            q = qty_val if qty_val > 0 else max(1, s.max_affordable(b.id))
            cost = s.building_cost(b.id, q)
            can = s.money >= cost
            teaser = i == visible + 1 and owned == 0 and not can
            wid = ("biz", b.id)
            h = ui.hover(r) and not teaser
            hv = ui.anim(wid, 1.0 if h else 0.0, 14)
            fl = ui.anim((wid, "flash"), 0.0, 6)
            rr = r.move(0, -int(3 * hv))
            fill = PANEL_HI if not teaser else PANEL_LO
            fill = gfx.lerp_col(fill, (84, 100, 108), hv)
            gfx.box(surf, rr, (*fill, 255), 10, ow=4, shadow_off=5)
            if fl > 0.05:
                gfx.rrect(surf, rr, (255, 230, 150, 255), 10, alpha=int(110 * fl))
            if teaser:
                surf.blit(icons.icon("lock", 40), (rr.x + 14, rr.y + 20))
                gfx.text(surf, "???", (rr.x + 74, rr.y + 12), 16, "b", DIM)
                gfx.text(surf, "Por descubrir", (rr.x + 74, rr.y + 34), 12, "r", DIM)
                gfx.text(surf, fmt_money(cost), (rr.x + 74, rr.y + 54), 12, "b", (170, 90, 80))
                continue
            surf.blit(icons.badge(b.id, 54, b_col(b)), (rr.x + 10, rr.y + 10))
            cnt = str(owned)
            cw_ = gfx.text_w(cnt, 12, "b") + 10
            cr_ = pygame.Rect(rr.x + 64 - cw_, rr.y + 50, cw_, 22)
            gfx.rrect(surf, cr_, (*(INK if owned else PANEL_LO), 255), 5)
            gfx.text(surf, cnt, cr_.center, 12, "b", TEXT if owned else DIM, anchor="center")
            gfx.text(surf, b.name, (rr.x + 74, rr.y + 10), 12, "b", TEXT, max_w=rr.w - 84)
            unit = s.building_unit_income(b.id) * s.passive_mult()
            gfx.text(surf, f"+{fmt_money(unit)}/s", (rr.x + 74, rr.y + 30), 12, "r", MUTED, max_w=rr.w - 84)
            gfx.text(surf, (f"x{q} " if q > 1 else "") + fmt_money(cost), (rr.x + 74, rr.y + 50), 12, "b",
                     GOLD if can else (220, 110, 100), max_w=rr.w - 84)
            if h:
                share = (unit * owned / total_ips * 100) if total_ips > 0 else 0
                nxt = next((n for n, _ in BUILDING_TIERS if n > owned), None)
                ui.tooltip(wid, r, f"{b.name}\n{b.desc}\n\nCada uno: {fmt_money(unit)}/s\n"
                                   f"Total: {fmt_money(unit * owned)}/s ({share:.0f}%)"
                                   + (f"\nPróximo hito: {nxt} unidades" if nxt else ""), title=GREEN)
            if not teaser and ui.clicked_area(wid, r):
                n = q if qty_val > 0 else s.max_affordable(b.id)
                if n > 0 and s.buy_building(b.id, n):
                    self.audio.play("buy" if n < 10 else "buy_big")
                    ui.anims[(wid, "flash")] = 1.0
                    self.fx.sparks(rr.x + 37, rr.centery, 12, b_col(b), 0.8)
                    self.fx.text(rr.centerx, rr.y + 6, f"-{fmt_money(cost)}", GOLD, 16, 0.8, 30)
                else:
                    self.audio.play("error")
        ui.end_scroll("biz")

    # ------------------------------------------------------------- centro
    def draw_center(self, surf, dt):
        ui = self.ui
        s = self.state
        x = CENTER.x + 16
        y = CENTER.y + 14
        n_upg = self.count_affordable_upgrades()
        news_tab = None
        for key, label, ic in TABS:
            w = gfx.text_w(label, 14, "b") + 62
            sel = self.tab == key
            r = pygame.Rect(x, y, w, 44)
            locked = key == "market" and s.player_level() < data.MARKET_LEVEL
            if ui.button(("tab", key), r, label, "gold" if sel else "dark", icon="lock" if locked else ic, size=14,
                         sound="tab", enabled=not locked,
                         tooltip=f"Se abre en el nivel de jugador {data.MARKET_LEVEL}" if locked else None):
                if self.tab != key:
                    self.tab = key
                    self.game_panel = None
            if key == "market" and not locked and self.market.unread and self.market.news_remaining() > 0:
                news_tab = r
            if key == "upgrades" and n_upg:
                gfx.circle(surf, (r.right - 4, r.y + 2), 11, GREEN, border=LINE, bw=2)
                gfx.text(surf, str(min(99, n_upg)), (r.right - 4, r.y + 2), 12, "b", TEXT, anchor="center")
            x += w + 8
        if news_tab:                                  # noticia sin abrir: insignia NEWS! en la esquina de Bolsa
            img = art.news_badge(52)
            bob = round(2 * math.sin(self.ui.t * 4))
            surf.blit(img, img.get_rect(center=(news_tab.right - 4, news_tab.y + 2 + bob)))
        if self.tab == "casino":
            self.draw_casino(surf, dt)
        elif self.tab == "upgrades":
            self.draw_upgrades(surf)
        elif self.tab == "market":
            self.draw_market(surf)
        elif self.tab == "vip":
            self.draw_vip(surf)
        elif self.tab == "achievements":
            self.draw_achievements(surf)
        else:
            self.draw_stats(surf)

    # ------------------------------------------------------------- casino
    def draw_casino(self, surf, dt):
        if self.current_game:
            self.draw_game(surf, dt)
            return
        ui = self.ui
        s = self.state
        area = CONTENT
        cols, gap = 2, 14
        cw = (area.w - 16 - gap * (cols - 1)) // cols
        ch = 168
        lobby = ([data.LASTBET] if s.special_pending() else []) + GAMES
        rows = (len(lobby) + cols - 1) // cols
        off = ui.begin_scroll("lobby", area, rows * (ch + gap) + 10)
        for i, g in enumerate(lobby):
            cx = area.x + (i % cols) * (cw + gap)
            cy = area.y + 6 + (i // cols) * (ch + gap) - off
            r = pygame.Rect(cx, cy, cw, ch)
            if r.bottom < area.y - 10 or r.y > area.bottom:
                continue
            unlocked = g.id in s.games_unlocked or g.id == "lastbet"
            can = s.money >= g.unlock_cost
            wid = ("tile", g.id)
            h = ui.hover(r)
            hv = ui.anim(wid, 1.0 if h else 0.0, 12)
            rr = r.move(0, -int(5 * hv))
            col = g_col(g)
            fill = gfx.lerp_col(PANEL_HI, col, 0.35) if unlocked else PANEL_LO
            is_hot = bool(s.hot) and s.hot["gid"] == g.id
            if is_hot:
                gfx.rrect(surf, rr.inflate(10, 10), (0, 0, 0, 0), 16,
                          border=gfx.lerp_col(GOLD, (255, 240, 160), 0.5 + 0.5 * math.sin(ui.t * 5)), bw=5)
            gfx.box(surf, rr, (*fill, 255), 12, ow=4, shadow_off=6 + int(3 * hv))
            gfx.rrect(surf, (rr.x + 4, rr.y + 4, rr.w - 8, 34),
                      (*(gfx.mul_col(col, 0.75) if unlocked else (52, 62, 68)), 255), 8)
            gfx.text(surf, g.name, (rr.x + 14, rr.y + 21), 14, "b", TEXT if unlocked else MUTED, anchor="midleft",
                     max_w=rr.w - 150)
            ang = math.sin(ui.t * 3 + i) * 6 * hv
            ic = icons.icon(g.id, 80)
            if not unlocked:
                ic = ic.copy()
                ic.set_alpha(80)
            if abs(ang) > 0.5:
                ic = pygame.transform.rotate(ic, ang)
            surf.blit(ic, ic.get_rect(center=(rr.x + 56, rr.y + 96)))
            lines = gfx.wrap(g.desc, 12, "r", rr.w - 124)
            if len(lines) > 2:
                lines = lines[:2]
                lines[1] = lines[1].rstrip(".") + "…"
            for li, ln in enumerate(lines):
                gfx.text(surf, ln, (rr.x + 108, rr.y + 50 + li * 22), 12, "r", MUTED if unlocked else DIM)
            if unlocked:
                feats = [f for f in FEATS if f.game == g.id]
                if is_hot:
                    feats = []
                    gfx.text(surf, "¡CALIENTE!", (rr.right - 12, rr.y + 21), 12, "bl", GOLD_HI, anchor="midright")
                done = sum(1 for f in feats if s.flags.get(f.id))
                if feats:
                    gfx.text(surf, f"hazañas {done}/{len(feats)}", (rr.right - 12, rr.y + 21), 12, "r",
                             (230, 236, 240), anchor="midright")
            br = pygame.Rect(rr.x + 108, rr.bottom - 58, rr.w - 120, 46)
            if unlocked:
                if ui.button(("play", g.id), br, "JUGAR", "green", size=14):
                    self.open_game(g.id)
            else:
                if ui.button(("unlock", g.id), br, f"Abrir · {fmt_money(g.unlock_cost)}", "gold", enabled=can,
                             size=12, sound=None):
                    if s.unlock_game(g.id):
                        self.audio.play("unlock")
                        self.fx.confetti(br.centerx, br.centery, 50, 0.7)
                        self.fx.sparks(br.centerx, br.centery, 30, col)
                        self.toast("Nuevo juego", g.name, col, g.id)
                        self.log(f"¡Has desbloqueado {g.name}!", GOLD)
        ui.end_scroll("lobby")

    def open_game(self, gid):
        from .games import GAME_CLASSES
        if self.current_game and self.current_game in self.games:
            self.games[self.current_game].on_hide()
        if gid not in self.games:
            self.games[gid] = GAME_CLASSES[gid](self)
        self.current_game = gid
        self.game_panel = None
        self.games[gid].on_show()

    def close_game(self):
        if self.current_game and self.current_game in self.games:
            self.games[self.current_game].on_hide()
        self.current_game = None
        self.game_panel = None

    def game_upgrades(self, gid):
        return [u for u in UPGRADES if u.game == gid]

    def count_game_affordable(self, gid):
        s = self.state
        return sum(1 for u in self.game_upgrades(gid) if s.can_buy_upgrade(u.id))

    def draw_game(self, surf, dt):
        ui = self.ui
        s = self.state
        g = self.games[self.current_game]
        gd = g.gdef
        col = g_col(gd)
        hx, hy = CONTENT.x, CONTENT.y
        if ui.button("back", (hx, hy, 48, 50), "", "dark", icon="back", tooltip="Volver al lobby"):
            self.close_game()
            return
        surf.blit(icons.badge(gd.id, 46, col), (hx + 58, hy))
        title = gd.name
        if gd.variants and getattr(g, "variant", None):
            vn = next((v.name for v in gd.variants if v.id == g.variant), "")
            title += f" · {vn}"
        gfx.text(surf, title, (hx + 116, hy + 14), 18, "bl", TEXT, anchor="midleft", max_w=400)
        gs = s.game_stats.get(gd.id)
        if gs:
            net = gs["returned"] - gs["wagered"]
            gfx.text(surf, f"{gs['played']} jugadas · {'+' if net >= 0 else ''}{fmt_money(net)}", (hx + 116, hy + 38),
                     12, "r", MUTED, anchor="midleft", max_w=380)
        n_aff = self.count_game_affordable(gd.id)
        ub = pygame.Rect(CONTENT.right - 170, hy, 170, 50)
        if ui.button("gupg", ub, "MEJORAS", "gold" if self.game_panel == "upg" else "primary", icon="upgrade",
                     size=14):
            self.game_panel = None if self.game_panel == "upg" else "upg"
        if n_aff:
            gfx.circle(surf, (ub.right - 4, ub.y + 2), 11, GREEN, border=LINE, bw=2)
            gfx.text(surf, str(min(99, n_aff)), (ub.right - 4, ub.y + 2), 12, "b", TEXT, anchor="center")
        jb = pygame.Rect(ub.x - 168, hy, 158, 50)
        if ui.button("gmenu", jb, "JUEGOS", "gold" if self.game_panel == "games" else "dark", icon="chip", size=14,
                     tooltip="Cambiar de juego sin volver al lobby"):
            self.game_panel = None if self.game_panel == "games" else "games"
        area = pygame.Rect(CONTENT.x, CONTENT.y + 62, CONTENT.w, CONTENT.h - 62)
        if self.game_panel == "upg":
            g.update_timers_only(dt)
            self.draw_game_upgrades(surf, area, g)
        elif self.game_panel == "games":
            g.update_timers_only(dt)
            self.draw_game_switcher(surf, area, gd)
        else:
            g.frame(surf, area, dt)

    def draw_game_switcher(self, surf, area, current):
        """Todos los juegos desbloqueados para saltar de uno a otro."""
        ui = self.ui
        s = self.state
        gfx.box(surf, area, (*PANEL_LO, 255), 12, ow=4, shadow_off=0)
        gfx.text(surf, "CAMBIAR DE JUEGO", (area.x + 20, area.y + 22), 14, "bl", ORANGE, anchor="midleft")
        hot = getattr(s, "hot", None)
        games = [o for o in GAMES if o.id in s.games_unlocked]
        cols = 4
        gap = 10
        cw = (area.w - 40 - gap * (cols - 1)) // cols
        ch = 76
        for i, o in enumerate(games):
            r = pygame.Rect(area.x + 20 + (i % cols) * (cw + gap), area.y + 48 + (i // cols) * (ch + gap), cw, ch)
            sel = o.id == current.id
            is_hot = bool(hot) and hot.get("gid") == o.id
            hv = ui.anim(("gsw", o.id), 1.0 if ui.hover(r) else 0.0, 14)
            fill = gfx.lerp_col(PANEL_HI, g_col(o), 0.45 if sel else 0.18 + 0.15 * hv)
            gfx.box(surf, r.move(0, -int(3 * hv)), (*fill, 255), 10, outline=GOLD if is_hot else None,
                    ow=4, shadow_off=4)
            rr = r.move(0, -int(3 * hv))
            surf.blit(icons.icon(o.id, 48), (rr.x + 10, rr.centery - 24))
            gfx.text(surf, o.name, (rr.x + 66, rr.centery - (10 if is_hot else 0)), 12, "b", TEXT, anchor="midleft",
                     max_w=rr.w - 74)
            if is_hot:
                gfx.text(surf, "¡MESA CALIENTE!", (rr.x + 66, rr.centery + 14), 10, "b", GOLD_HI, anchor="midleft")
            if ui.clicked_area(("gswc", o.id), r, sound="tab"):
                self.game_panel = None
                if not sel:
                    self.open_game(o.id)
                return

    def draw_game_upgrades(self, surf, area, g):
        ui = self.ui
        s = self.state
        gd = g.gdef
        gfx.box(surf, area, (*PANEL_LO, 255), 12, ow=4, shadow_off=0)
        y = area.y + 16
        x = area.x + 20
        if s.game_rtp(gd.id, getattr(g, "variant", None)) is None:
            gfx.text(surf, "Juego de habilidad contra rivales: aquí cuenta cómo juegas.", (x, y), 12, "r", MUTED)
        else:
            gfx.text(surf, "Ventajas que ganas con hazañas y mejoras que compras para esta mesa.", (x, y), 12, "r",
                     MUTED)
        y += 28
        inner = pygame.Rect(area.x + 12, y, area.w - 24, area.bottom - y - 12)
        items = []
        feats = [f for f in FEATS if f.game == gd.id]
        legs = [u for u in UNIQUES if u.rarity == "legendary" and u.icon == gd.id]
        if feats or legs:
            items.append(("title", "HAZAÑAS Y VENTAJAS"))
            for f in feats:
                items.append(("feat", f))
            for u in legs:
                items.append(("leg", u))
        ups = [u for u in self.game_upgrades(gd.id) if not u.feat]
        if ups:
            items.append(("title", "MEJORAS DE ESTE JUEGO"))
            for u in ups:
                items.append(("upg", u))
        desc_w = inner.w - 16 - 300

        def hgt(k, o):
            if k == "title":
                return 38
            if k in ("feat", "leg"):
                return 86
            return max(96, 68 + 21 * len(gfx.wrap(o.desc, 12, "r", desc_w)))
        heights = [hgt(k, o) for k, o in items]
        off = ui.begin_scroll(("gup", gd.id), inner, sum(heights) + 10)
        yy = inner.y - off
        for (kind, obj), hh in zip(items, heights):
            if yy + hh < inner.y - 10 or yy > inner.bottom:
                yy += hh
                continue
            r = pygame.Rect(inner.x, yy, inner.w - 16, hh - 10)
            if kind == "title":
                gfx.text(surf, obj, (inner.x + 8, yy + 14), 14, "bl", ORANGE)
            elif kind == "feat":
                f = obj
                done = s.flags.get(f.id)
                u = UPGRADE_BY_ID[f.reward]
                gfx.box(surf, r, (*(gfx.lerp_col(PANEL_HI, ORANGE, 0.22) if done else PANEL_HI), 255), 10, ow=4,
                        shadow_off=4)
                surf.blit(icons.icon("trophy" if done else "trophy_off", 40), (r.x + 14, r.centery - 20))
                gfx.text(surf, f.name, (r.x + 68, r.y + 12), 14, "b", GOLD_HI if done else TEXT, max_w=r.w - 330)
                gfx.text(surf, f.desc, (r.x + 68, r.y + 38), 12, "r", MUTED, max_w=r.w - 330)
                gfx.text(surf, "Recompensa", (r.right - 240, r.y + 14), 12, "r", DIM)
                gfx.text(surf, u.name, (r.right - 240, r.y + 36), 12, "b", GREEN if done else TEXT, max_w=224)
                ui.tooltip(("ft", f.id), r, f"{f.name}\n{f.desc}\n\nRecompensa: {u.name}\n{u.desc}", title=GOLD_HI)
                if done and u.id.startswith("hint_"):
                    rem = s.hint_remaining(gd.id)
                    gfx.text(surf, "¡LISTA!" if rem <= 0 else f"lista en {fmt_time(rem)}", (r.right - 240, r.y + 56),
                             12, "b", GREEN if rem <= 0 else MUTED)
            elif kind == "leg":
                u = obj
                own = u.id in s.uniques
                gfx.box(surf, r, (*(gfx.lerp_col(PANEL_HI, RARITY_COL["legendary"], 0.25) if own else PANEL_LO), 255),
                        10, outline=RARITY_COL["legendary"] if own else LINE, ow=4, shadow_off=4)
                surf.blit(icons.icon("star" if own else "lock", 40), (r.x + 14, r.centery - 20))
                gfx.text(surf, f"Legendaria: {u.name}", (r.x + 68, r.y + 12), 14, "b",
                         GOLD_HI if own else MUTED, max_w=r.w - 90)
                gfx.text(surf, u.desc if own else "Solo aparece, muy de vez en cuando, como oportunidad.",
                         (r.x + 68, r.y + 38), 12, "r", MUTED, max_w=r.w - 90)
                if own:
                    ui.tooltip(("lg", u.id), r, f"{u.name}\n{u.desc}", INFO_DELAY, title=RARITY_COL["legendary"])
            else:
                u = obj
                lvl = s.lvl(u.id)
                maxed = lvl >= u.max_level
                cost = s.upgrade_cost(u.id)
                lock = s.upgrade_lock(u.id)
                can = s.can_buy_upgrade(u.id)
                gfx.box(surf, r, (*PANEL_HI, 255), 10, ow=4, shadow_off=4)
                ic = "star" if u.id.startswith("mastery") else "chip"
                surf.blit(icons.badge(ic, 48, PURPLE if u.id.startswith("mastery") else RED), (r.x + 12, r.centery - 26))
                name = u.name + (f"  {lvl}/{u.max_level}" if u.max_level > 1 else "")
                gfx.text(surf, name, (r.x + 74, r.y + 14), 14, "b", TEXT, max_w=r.w - 300)
                gfx.text_wrapped(surf, u.desc, (r.x + 74, r.y + 38), 12, "r", MUTED, r.w - 300)
                ui.tooltip(("gut", u.id), r, f"{name}\n{u.desc}", INFO_DELAY, title=GREEN)
                br = pygame.Rect(r.right - 200, r.centery - 24, 184, 48)
                if maxed:
                    gfx.text(surf, "AL MÁXIMO", br.center, 14, "b", GREEN, anchor="center")
                elif lock:
                    ui.button(("gub", u.id), br, "Bloqueada", "dark", enabled=False, size=12, sub=lock)
                elif ui.button(("gub", u.id), br, fmt_money(cost), "gold" if can else "dark", enabled=can, size=13,
                               sound=None):
                    if s.buy_upgrade(u.id):
                        self.audio.play("buy")
                        self.fx.sparks(br.centerx, br.centery, 18, ORANGE)
                        self.fx.text(br.centerx, br.y, "¡Mejorado!", ORANGE, 16, 0.8, 30)
                        g.on_upgrade(u.id)
            yy += hh
        ui.end_scroll(("gup", gd.id))

    # ------------------------------------------------------------ mejoras
    def visible_upgrades(self):
        s = self.state
        f = [None, "click", "casino", "business", "golden"][self.upg_filter]
        res = [u for u in UPGRADES if u.game is None and (f is None or u.category == f) and s.upgrade_visible(u.id)]
        res.sort(key=lambda u: s.upgrade_cost(u.id))
        return res

    def count_affordable_upgrades(self):
        s = self.state
        if time.time() - self._aff_cache[0] > 0.3:
            n = sum(1 for u in UPGRADES if u.game is None and s.upgrade_visible(u.id) and s.can_buy_upgrade(u.id))
            self._aff_cache = (time.time(), n)
        return self._aff_cache[1]

    def draw_upgrades(self, surf):
        ui = self.ui
        a = CONTENT
        self.upg_view = min(self.upg_view, 2)
        new = ui.segmented("upgv", (a.x, a.y, 420, 42), ["Tienda", "Colección", "Desglose"], self.upg_view, 12)
        if new != self.upg_view:
            self.upg_view = new
        if self.upg_view == 0:
            self.draw_shop(surf)
        elif self.upg_view == 1:
            self.draw_collection(surf)
        else:
            self.draw_breakdown(surf)

    def draw_market_upgrades(self, surf):
        """Hitos de la bolsa y mejoras únicas de noticias (dentro de la página de la bolsa)."""
        from .market import NEWS_STREAK
        ui = self.ui
        s = self.state
        a = CONTENT
        if ui.button("mk_back", (a.x, a.y, 160, 40), "Volver", "dark", icon="back", size=12):
            self.market_upg = False
            return
        y = a.y + 62
        gfx.text(surf, "HITOS DE LA BOLSA", (a.x, y), 14, "bl", ORANGE)
        gfx.text(surf, "Se consiguen jugando y no se pierden con el prestigio.",
                 (a.x + gfx.text_w("HITOS DE LA BOLSA", 14, "bl") + 12, y + 2), 12, "r", MUTED)
        y += 30
        lh = gfx.line_height(12)
        for mid, name, how, reward in data.MARKET_MILESTONES:
            done = bool(s.flags.get(mid))
            how_l = [] if done else gfx.wrap("Cómo: " + how, 12, "r", a.w - 106)
            rew_l = gfx.wrap(("Tienes: " if done else "Recompensa: ") + reward, 12, "r", a.w - 106)
            r = pygame.Rect(a.x, y, a.w - 16, 44 + (len(how_l) + len(rew_l)) * lh + (24 if done else 4))
            gfx.box(surf, r, (*(gfx.lerp_col(PANEL_HI, (150, 200, 255), 0.18) if done else PANEL_HI), 255), 10,
                    ow=4, shadow_off=4, outline=(150, 200, 255) if done else None)
            surf.blit(icons.icon("trophy" if done else "trophy_off", 44), (r.x + 14, r.y + 14))
            gfx.text(surf, name, (r.x + 72, r.y + 12), 14, "b", GOLD_HI if done else TEXT)
            ty = r.y + 36
            if done:
                gfx.text(surf, "CONSEGUIDO", (r.x + 72, ty), 12, "b", GREEN)
                ty += 24
            for ln in how_l:
                gfx.text(surf, ln, (r.x + 72, ty), 12, "r", MUTED)
                ty += lh
            for ln in rew_l:
                gfx.text(surf, ln, (r.x + 72, ty), 12, "r", (220, 214, 196) if done else DIM)
                ty += lh
            ui.tooltip(("mm", mid), r, f"{name}\nCómo: {how}\nRecompensa: {reward}", INFO_DELAY, title=GOLD_HI)
            if mid == "news_pro" and not done:
                st = s.flags.get("news_streak", 0)
                gfx.text(surf, f"racha {st}/{NEWS_STREAK}", (r.right - 16, r.y + 14), 12, "b", ORANGE,
                         anchor="topright")
            y += r.h + 10
        y += 10
        gfx.text(surf, "MEJORAS ÚNICAS DE NOTICIAS", (a.x, y), 14, "bl", ORANGE)
        gfx.text(surf, "Salen como oportunidad (cuando ya recibes noticias).",
                 (a.x + gfx.text_w("MEJORAS ÚNICAS DE NOTICIAS", 14, "bl") + 12, y + 2), 12, "r", MUTED)
        y += 30
        for uid in ("news_inside", "news_inside_2", "leg_news"):
            u = UNIQUE_BY_ID[uid]
            own = uid in s.uniques
            col = RARITY_COL[u.rarity]
            r = pygame.Rect(a.x, y, a.w - 16, 72)
            gfx.box(surf, r, (*(gfx.lerp_col(PANEL_HI, col, 0.2) if own else PANEL_LO), 255), 10,
                    outline=col if own else LINE, ow=4, shadow_off=4)
            if own:
                surf.blit(icons.badge(u.icon, 44, col), (r.x + 12, r.y + 12))
            else:
                surf.blit(icons.icon("lock", 34), (r.x + 16, r.y + 18))
            gfx.text(surf, u.name, (r.x + 72, r.y + 12), 14, "b", TEXT if own else MUTED)
            gfx.text(surf, RARITY_NAME[u.rarity], (r.right - 16, r.y + 14), 12, "b", col, anchor="topright")
            gfx.text(surf, u.desc, (r.x + 72, r.y + 40), 12, "r", MUTED if own else DIM, max_w=r.w - 90)
            ui.tooltip(("mu", uid), r, f"{u.name} ({RARITY_NAME[u.rarity]})\n{u.desc}", INFO_DELAY, title=RARITY_COL[u.rarity])
            y += 82

    def draw_shop(self, surf):
        ui = self.ui
        s = self.state
        a = CONTENT
        n_aff = self.count_affordable_upgrades()
        if ui.button("buyall", (a.right - 220, a.y - 2, 220, 46), f"Comprar todo ({n_aff})", "green",
                     enabled=n_aff > 0, size=13, sound=None):
            self.buy_all_upgrades()
        new = ui.segmented("upgf", (a.x, a.y + 54, 520, 38), ["Todas", "Clicker", "Casino", "Negocios", "Suerte"],
                           self.upg_filter, 12)
        if new != self.upg_filter:
            self.upg_filter = new
            ui.scroll_to_top("upg")
        gfx.text(surf, "Las mejoras únicas salen como oportunidades. Las de cada juego, en su mesa.",
                 (a.x + 536, a.y + 64), 10, "r", DIM, max_w=a.w - 540)
        ups = self.visible_upgrades()
        area = pygame.Rect(a.x, a.y + 104, a.w, a.h - 104)
        row_h = 100
        if not ups:
            gfx.text(surf, "No hay mejoras disponibles ahora mismo.", area.center, 16, "b", MUTED, anchor="center")
            return
        off = ui.begin_scroll("upg", area, len(ups) * row_h + 8)
        for k, u in enumerate(ups):
            r = pygame.Rect(area.x, area.y + 2 + k * row_h - off, area.w - 16, row_h - 12)
            if r.bottom < area.y - 10 or r.y > area.bottom:
                continue
            lvl = s.lvl(u.id)
            cost = s.upgrade_cost(u.id)
            lock = s.upgrade_lock(u.id)
            can = s.can_buy_upgrade(u.id)
            ccol = CAT_COL[u.category]
            hv = ui.anim(("upr", u.id), 1.0 if ui.hover(r) else 0.0)
            rr = r.move(0, -int(3 * hv))
            gfx.box(surf, rr, (*gfx.lerp_col(PANEL_HI, (80, 96, 104), hv), 255), 10, ow=4, shadow_off=5)
            surf.blit(icons.badge(CAT_ICON[u.category], 52, ccol), (rr.x + 12, rr.centery - 28))
            gfx.text(surf, u.name, (rr.x + 78, rr.y + 12), 14, "b", TEXT, max_w=rr.w - 320)
            gfx.text(surf, u.desc, (rr.x + 78, rr.y + 34), 12, "r", MUTED, max_w=rr.w - 320)
            ui.tooltip(("upt", u.id), r, u.name + (f" ({lvl}/{u.max_level})" if u.max_level > 1 else "")
                       + f"\n{u.desc}" + (f"\n{lock}" if lock else ""), INFO_DELAY, title=GREEN)
            if u.max_level > 1:
                lx, ly = rr.x + 78, rr.y + 62
                if u.max_level <= 25:
                    for j in range(u.max_level):
                        surf.fill(ccol if j < lvl else (70, 84, 92), (lx + j * 10, ly, 8, 8))
                    gfx.text(surf, f"{lvl}/{u.max_level}", (lx + u.max_level * 10 + 6, ly - 2), 12, "r", MUTED)
                else:
                    gfx.text(surf, f"Nivel {lvl}/{u.max_level}", (lx, ly - 2), 12, "r", MUTED)
            br = pygame.Rect(rr.right - 210, rr.centery - 25, 196, 50)
            if lock:
                ui.button(("ub", u.id), br, "Bloqueada", "dark", enabled=False, size=12, sub=lock)
            elif ui.button(("ub", u.id), br, fmt_money(cost), "gold" if can else "dark", enabled=can, size=14,
                           sound=None):
                if s.buy_upgrade(u.id):
                    self.audio.play("buy")
                    self.fx.sparks(br.centerx, br.centery, 18, ccol)
                    self.fx.text(br.centerx, br.y, "¡Mejorado!", ccol, 16, 0.8, 30)
                    self.log(f"Mejora: {u.name}", (150, 200, 255))
        ui.end_scroll("upg")

    def buy_all_upgrades(self):
        s = self.state
        bought = 0
        while bought < 500:
            ups = [u for u in UPGRADES if u.game is None and s.upgrade_visible(u.id) and s.can_buy_upgrade(u.id)]
            if not ups:
                break
            u = min(ups, key=lambda u: s.upgrade_cost(u.id))
            if not s.buy_upgrade(u.id):
                break
            bought += 1
        if bought:
            self.audio.play("buy_big")
            self.fx.confetti(CONTENT.right - 110, CONTENT.y + 20, 40, 0.6)
            self.log(f"Has comprado {bought} mejora{'s' if bought > 1 else ''}.", (150, 200, 255))

    def draw_collection(self, surf):
        ui = self.ui
        s = self.state
        a = CONTENT
        x = a.x
        for rar in RARITIES:
            tot = sum(1 for u in UNIQUES if u.rarity == rar)
            have = sum(1 for u in UNIQUES if u.rarity == rar and u.id in s.uniques)
            t = f"{RARITY_NAME[rar]} {have}/{tot}"
            w = gfx.text_w(t, 12, "b") + 26
            r = pygame.Rect(x, a.y + 56, w, 30)
            gfx.rrect(surf, r, (*gfx.mul_col(RARITY_COL[rar], 0.45), 255), 8, border=RARITY_COL[rar], bw=3)
            gfx.text(surf, t, r.center, 12, "b", TEXT, anchor="center")
            x += w + 8
        area = pygame.Rect(a.x, a.y + 100, a.w, a.h - 100)
        cols = 3
        cw = (area.w - 16 - 10 * (cols - 1)) // cols
        rh = 96
        order = sorted(UNIQUES, key=lambda u: (u.id not in s.uniques, -RARITIES.index(u.rarity), u.name))
        rows = (len(order) + cols - 1) // cols
        off = ui.begin_scroll("coll", area, rows * (rh + 10) + 8)
        for i, u in enumerate(order):
            r = pygame.Rect(area.x + (i % cols) * (cw + 10), area.y + 2 + (i // cols) * (rh + 10) - off, cw, rh)
            if r.bottom < area.y - 10 or r.y > area.bottom:
                continue
            own = u.id in s.uniques
            col = RARITY_COL[u.rarity]
            gfx.box(surf, r, (*(gfx.lerp_col(PANEL_HI, col, 0.2) if own else PANEL_LO), 255), 10,
                    outline=col if own else LINE, ow=4, shadow_off=4)
            if own:
                surf.blit(icons.badge(u.icon, 44, col), (r.x + 10, r.y + 12))
            else:
                surf.blit(icons.icon("lock", 34), (r.x + 14, r.y + 18))
            gfx.text(surf, u.name, (r.x + 62, r.y + 12), 12, "b", TEXT if own else DIM, max_w=r.w - 70)
            gfx.text(surf, RARITY_NAME[u.rarity], (r.x + 62, r.y + 32), 10, "b", col if own else gfx.mul_col(col, 0.6))
            lines = gfx.wrap(u.desc, 10, "r", r.w - 70)[:2]
            for li, ln in enumerate(lines):
                gfx.text(surf, ln, (r.x + 62, r.y + 50 + li * 16), 10, "r", MUTED if own else DIM)
            ui.tooltip(("col", u.id), r, f"{u.name} ({RARITY_NAME[u.rarity]})\n{u.desc}"
                                         + ("" if own else "\nSolo aparece como oportunidad."), title=RARITY_COL[u.rarity])
        ui.end_scroll("coll")

    def draw_breakdown(self, surf):
        ui = self.ui
        s = self.state
        a = CONTENT
        area = pygame.Rect(a.x, a.y + 56, a.w, a.h - 56)
        rows_b = [b for b in BUILDINGS if s.buildings.get(b.id, 0)]
        total_h = 330 + 60 + len(rows_b) * 30 + 40
        off = ui.begin_scroll("brk", area, total_h)
        y = area.y - off
        colw = (a.w - 16 - 12) // 2
        # clic
        r = pygame.Rect(a.x, y, colw, 320)
        gfx.box(surf, r, (*PANEL_HI, 255), 10, ow=4, shadow_off=4)
        surf.blit(icons.icon("click", 26), (r.x + 14, r.y + 12))
        gfx.text(surf, "VALOR DE UN CLIC", (r.x + 48, r.y + 25), 14, "bl", ORANGE, anchor="midleft")
        lines = [("Base (fuerza de dedo)", fmt_money(0.01 * (1 + s.lvl("click_power"))))]
        for name, k in s.click_breakdown():
            lines.append((f"× {name}", f"x{fmt_num(k)}"))
        lines.append(("= Clic base", fmt_money(s.click_base())))
        lines.append(("× Combo actual", f"+{s.combo}%"))
        if s.lvl("synergy"):
            lines.append(("+ Clic sinérgico", f"{s.lvl('synergy')}% de tus €/s"))
        lines.append(("= Por clic ahora", fmt_money(s.click_value())))
        lines.append((f"Auto-clics ({fmt_int(s.autoclicks_per_sec())}/s, sin combo)",
                      fmt_money(s.auto_income_per_sec()) + "/s"))
        for k, (key, val) in enumerate(lines):
            yy = r.y + 52 + k * 26
            strong = key.startswith("=")
            gfx.text(surf, key, (r.x + 16, yy), 12, "b" if strong else "r", TEXT if strong else MUTED, max_w=colw - 150)
            gfx.text(surf, val, (r.right - 16, yy), 12, "b", GOLD_HI if strong else TEXT, anchor="topright")
        # pasivo
        r2 = pygame.Rect(a.x + colw + 12, y, colw, 320)
        gfx.box(surf, r2, (*PANEL_HI, 255), 10, ow=4, shadow_off=4)
        surf.blit(icons.icon("business", 26), (r2.x + 14, r2.y + 12))
        gfx.text(surf, "INGRESOS PASIVOS", (r2.x + 48, r2.y + 25), 14, "bl", ORANGE, anchor="midleft")
        base = sum(s.building_unit_income(b.id) * s.buildings.get(b.id, 0) for b in BUILDINGS)
        lines = [("Suma de tus negocios", fmt_money(base) + "/s")]
        for name, k in s.passive_breakdown():
            lines.append((f"× {name}", f"x{fmt_num(k)}"))
        lines.append(("= Total", fmt_money(s.income_per_sec()) + "/s"))
        for k, (key, val) in enumerate(lines[:10]):
            yy = r2.y + 52 + k * 26
            strong = key.startswith("=")
            gfx.text(surf, key, (r2.x + 16, yy), 12, "b" if strong else "r", TEXT if strong else MUTED,
                     max_w=colw - 150)
            gfx.text(surf, val, (r2.right - 16, yy), 12, "b", GOLD_HI if strong else TEXT, anchor="topright")
        gfx.text_wrapped(surf, "Todo se multiplica entre sí. Las sumas solo están en la fuerza de dedo y el clic "
                               "sinérgico.", (r2.x + 16, r2.bottom - 52), 10, "r", DIM, colw - 32)
        # tabla de negocios
        y = r.bottom + 14
        t = pygame.Rect(a.x, y, a.w - 16, 56 + len(rows_b) * 30)
        gfx.box(surf, t, (*PANEL_HI, 255), 10, ow=4, shadow_off=4)
        cols = [("NEGOCIO", t.x + 16, "topleft"), ("UNID.", t.x + 300, "topright"), ("BASE", t.x + 410, "topright"),
                ("HITOS", t.x + 490, "topright"), ("ÚNICAS", t.x + 580, "topright"), ("TOTAL", t.right - 16, "topright")]
        for name, cx, anc in cols:
            gfx.text(surf, name, (cx, t.y + 16), 12, "b", MUTED, anchor=anc)
        pm = s.passive_mult()
        for k, b in enumerate(rows_b):
            yy = t.y + 46 + k * 30
            n = s.buildings.get(b.id, 0)
            tiers = 2 ** s.tier_count(b.id)
            um = s.fx()["bld"].get(b.id, 1.0)
            gfx.text(surf, b.name, (t.x + 16, yy), 12, "r", TEXT, max_w=250)
            gfx.text(surf, fmt_int(n), (t.x + 300, yy), 12, "b", TEXT, anchor="topright")
            gfx.text(surf, fmt_money(b.base_income), (t.x + 410, yy), 12, "r", MUTED, anchor="topright")
            gfx.text(surf, f"x{fmt_num(tiers)}", (t.x + 490, yy), 12, "b", GREEN if tiers > 1 else DIM, anchor="topright")
            gfx.text(surf, f"x{fmt_num(um)}", (t.x + 580, yy), 12, "b", RARITY_COL["rare"] if um > 1 else DIM,
                     anchor="topright")
            gfx.text(surf, fmt_money(b.base_income * tiers * um * n * pm) + "/s", (t.right - 16, yy), 12, "b",
                     GOLD_HI, anchor="topright")
        ui.end_scroll("brk")

    # ------------------------------------------------------------- bolsa
    def draw_market(self, surf):
        from .market import ASSETS, ASSET_BY_SYM, SPREAD
        from .fmt import parse_amount
        if getattr(self, "market_upg", False):
            self.draw_market_upgrades(surf)
            return
        ui = self.ui
        s = self.state
        mk = self.market
        a = CONTENT
        # lista de valores: los abiertos y el siguiente que se abrirá
        lw = 236
        y = a.y
        locked = [x for x in ASSETS if not mk.unlocked(x[0])]
        shown = [x for x in ASSETS if mk.unlocked(x[0])] + locked[:1]
        affected = mk.active["effects"] if (mk.active and mk.news_pro()) else {}
        for sym, name, lvl, *_ in shown:
            r = pygame.Rect(a.x, y, lw, 48)
            ok = mk.unlocked(sym)
            sel = mk.selected == sym
            asset = mk.assets[sym]
            ch = asset.change()
            fill = gfx.lerp_col(PANEL_HI, ORANGE, 0.3) if sel else (PANEL_HI if ok else PANEL_LO)
            gfx.box(surf, r, (*fill, 255), 8, ow=3, shadow_off=3,
                    outline=(150, 200, 255) if sym in affected else None)
            if ok:
                held = mk.p(sym)["qty"] > 0 or mk.p(sym).get("sq", 0) > 0
                gfx.text(surf, sym, (r.x + 12, r.y + 7), 12, "bl", TEXT)
                if held:
                    pygame.draw.circle(surf, GOLD_HI, (r.x + 20 + gfx.text_w(sym, 12, "bl"), r.y + 16), 4)
                pct = f"{ch * 100:+.1f}%"
                gfx.text(surf, fmt_money(asset.price()), (r.right - 10, r.y + 7), 12, "b", GOLD_HI, anchor="topright")
                gfx.text(surf, pct, (r.right - 10, r.y + 26), 12, "b", GREEN if ch >= 0 else RED, anchor="topright")
                gfx.text(surf, name, (r.x + 12, r.y + 28), 10, "b", MUTED,
                         max_w=r.w - 34 - gfx.text_w(pct, 12, "b"))
                if ui.clicked_area(("mk", sym), r, sound="tab"):
                    mk.selected = sym
            else:
                surf.blit(icons.icon("lock", 24), (r.x + 12, r.centery - 12))
                more = len(locked) - 1
                gfx.text(surf, f"{sym} · nivel {lvl}" + (f"  (+{more})" if more > 0 else ""), (r.x + 44, r.centery),
                         12, "b", DIM, anchor="midleft")
            y += 54
        tv = mk.total_value()
        gfx.text(surf, "TU CARTERA", (a.x + 4, y + 6), 12, "b", MUTED)
        gfx.text(surf, fmt_money(tv), (a.x + 4, y + 26), 16, "bl", GOLD_HI, max_w=lw - 8)
        # gráfica de velas
        sym = mk.selected if mk.unlocked(mk.selected) else "ORO"
        asset = mk.assets[sym]
        cr = pygame.Rect(a.x + lw + 14, a.y, a.w - lw - 30, 352)
        gfx.box(surf, cr, (16, 22, 28, 255), 10, ow=4, shadow_off=4)
        gfx.text(surf, f"{sym} · {asset.name}", (cr.x + 16, cr.y + 14), 14, "bl", TEXT,
                 max_w=cr.w - 200)
        if ui.button("mk_upg", (cr.right - 168, cr.y + 8, 156, 34), "MEJORAS", "primary", icon="upgrade", size=12):
            self.market_upg = True
            return
        plot = pygame.Rect(cr.x + 16, cr.y + 46, cr.w - 96, cr.h - 66)
        candles = list(asset.candles)
        if asset.cur:
            candles.append(tuple(asset.cur))
        if candles:
            hi = max(c[1] for c in candles)
            lo = min(c[2] for c in candles)
            span = max(1e-9, hi - lo)
            hi += span * 0.08
            lo -= span * 0.08
            span = hi - lo
            py_now = plot.bottom - (asset.price() - lo) / span * plot.h
            for k in range(5):
                gy = plot.y + plot.h * k / 4
                pygame.draw.line(surf, (34, 44, 52), (plot.x, gy), (plot.right, gy), 1)
                if abs(gy - py_now) > 18:
                    gfx.text(surf, fmt_money(hi - span * k / 4), (plot.right + 8, gy), 10, "r", DIM, anchor="midleft")
            n = len(candles)
            cw = plot.w / max(40, n)

            def Y(v):
                return plot.bottom - (v - lo) / span * plot.h
            for i, (o, h, l, c) in enumerate(candles):
                x = plot.x + i * cw + cw / 2
                col = (78, 196, 146) if c >= o else (254, 95, 85)
                pygame.draw.line(surf, col, (x, Y(h)), (x, Y(l)), 2)
                top, bot = Y(max(o, c)), Y(min(o, c))
                pygame.draw.rect(surf, col, (x - cw * 0.35, top, max(2, cw * 0.7), max(2, bot - top)))
            py = Y(asset.price())
            pygame.draw.line(surf, (253, 162, 0), (plot.x, py), (plot.right, py), 1)
            lab = pygame.Rect(0, 0, 78, 26)
            lab.midleft = (plot.right + 2, py)
            gfx.rrect(surf, lab, (*ORANGE, 255), 4)
            gfx.text(surf, fmt_num(asset.price()), lab.center, 12, "b", TEXT, anchor="center", max_w=74)
        gfx.text(surf, f"compra {fmt_money(mk.ask(sym))} · venta {fmt_money(mk.bid(sym))}", (cr.x + 16, cr.bottom - 10),
                 10, "b", MUTED, anchor="bottomleft")
        # noticias: buzón + titular
        nb = pygame.Rect(cr.x, cr.bottom + 10, cr.w, 80)
        gfx.box(surf, nb, (24, 32, 44, 255), 10, ow=4, shadow_off=4)
        mb = pygame.Rect(nb.x + 12, nb.y + 12, 56, 56)
        news = mk.active if mk.news_enabled() else None
        glow = mk.unread and news
        if glow:
            gfx.glow(surf, mb.center, 46, (150, 200, 255), 0.25 + 0.15 * math.sin(ui.t * 5))
        if ui.button("mailbox", mb, "", "primary" if glow else "dark", icon="mail", enabled=bool(news),
                     tooltip="Buzón: abre el periódico" if news else None):
            self.modal = "newspaper"
            mk.unread = False
        tx = mb.right + 14
        if news:
            gfx.text(surf, "NOTICIA" + (" NUEVA" if mk.unread else ""), (tx, nb.y + 12), 10, "bl",
                     (150, 200, 255))
            gfx.text(surf, f"quedan {fmt_time(mk.news_remaining())}", (nb.right - 14, nb.y + 12), 10, "b", MUTED,
                     anchor="topright")
            gfx.text(surf, news["title"], (tx, nb.y + 30), 12, "b", TEXT, max_w=nb.right - tx - 14)
            if mk.news_pro():
                fx_txt = ("Afecta a: " + " · ".join(news["effects"])) if news["effects"] else "Puro ruido: no mueve nada"
                gfx.text(surf, fx_txt, (tx, nb.y + 52), 10, "b", (150, 200, 255), max_w=nb.right - tx - 14)
            else:
                gfx.text(surf, "Pulsa el buzón para leerla entera.", (tx, nb.y + 52), 10, "r", DIM)
            if ui.clicked_area("news_strip", pygame.Rect(tx, nb.y, nb.right - tx, nb.h), sound="ui"):
                self.modal = "newspaper"
                mk.unread = False
        elif mk.news_enabled():
            gfx.text(surf, "BUZÓN VACÍO", (tx, nb.y + 18), 10, "bl", DIM)
            gfx.text(surf, "Las noticias llegan cada pocos minutos.", (tx, nb.y + 40), 12, "r", DIM)
        else:
            gfx.text(surf, "SIN NOTICIAS", (tx, nb.y + 14), 10, "bl", DIM)
            gfx.text_wrapped(surf, "Consigue el hito «Periódico financiero» (Mejoras → Bolsa): duplica una inversión "
                                   "por primera vez.", (tx, nb.y + 32), 12, "r", DIM, nb.right - tx - 14)
        o = pygame.Rect(cr.x, nb.bottom + 10, cr.w, a.bottom - nb.bottom - 10)
        gfx.box(surf, o, (*PANEL_HI, 255), 10, ow=4, shadow_off=4)
        gfx.text(surf, "CANTIDAD", (o.x + 16, o.y + 14), 12, "b", MUTED)
        wid = ("mkqty",)
        focused = ui.focus == wid
        txt, done = ui.text_input(wid, (o.x + 16, o.y + 34, 150, 46), self.mk_qty, size=16, color=GOLD_HI)
        if focused or done:
            self.mk_qty = txt
        qty = parse_amount(self.mk_qty) or 0.0
        ask = mk.ask(sym)
        maxq = int(s.money / ask * 1000) / 1000 if ask > 0 else 0
        bx = o.x + 174
        for lbl, fn in (("½", lambda q: q / 2), ("x2", lambda q: q * 2), ("MAX", lambda q: maxq)):
            if ui.button(("mkq", lbl), (bx, o.y + 34, 50, 46), lbl, "dark", size=12, sound="chip0"):
                v = fn(qty)
                self.mk_qty = fmt_num(v) if v < 1e9 else f"{v:.3e}"
                qty = parse_amount(self.mk_qty) or 0.0
            bx += 56
        gfx.text(surf, f"Total: {fmt_money(qty * ask)}", (o.x + 16, o.y + 92), 12, "b", TEXT, max_w=330)
        p = mk.p(sym)
        ly = o.y + 118
        if p["qty"] > 0:
            val = p["qty"] * mk.bid(sym)
            pnl = val - p["cost"]
            gfx.text(surf, f"Tienes {fmt_num(p['qty'])} · valen {fmt_money(val)}", (o.x + 16, ly), 12, "r", TEXT,
                     max_w=330)
            gfx.text(surf, f"{'+' if pnl >= 0 else ''}{fmt_money(pnl)}", (o.x + 16, ly + 20), 12, "b",
                     GREEN if pnl >= 0 else RED, max_w=330)
            ly += 46
        if p.get("sq", 0) > 0:
            sv = mk.short_value(sym)
            pnl = sv - p["coll"]
            gfx.text(surf, f"En corto {fmt_num(p['sq'])} · valen {fmt_money(sv)}", (o.x + 16, ly), 12, "r", TEXT,
                     max_w=330)
            gfx.text(surf, f"{'+' if pnl >= 0 else ''}{fmt_money(pnl)}", (o.x + 16, ly + 20), 12, "b",
                     GREEN if pnl >= 0 else RED, max_w=330)
        by = o.y + 34
        bx = o.x + 352
        if ui.button("mk_buy", (bx, by, 116, 46), "COMPRAR", "green", size=13,
                     enabled=qty > 0 and s.money >= qty * ask, sound=None):
            if mk.buy(sym, qty):
                self.audio.play("chip2")
                self.save_now()                       # cada operación se guarda al momento (no se puede deshacer)
        bx += 122
        if ui.button("mk_sell", (bx, by, 116, 46), "VENDER", "red", size=13, enabled=p["qty"] > 0, sound=None,
                     tooltip="Vende la cantidad indicada (o todo lo que tengas si es menos)."):
            self.market_sold(mk.sell(sym, qty if qty > 0 else p["qty"]), o)
        bx = o.x + 352
        by += 56
        if ui.button("mk_sell_all", (bx, by + 46, 238, 40), "VENDER TODO", "red", size=12, enabled=p["qty"] > 0,
                     sound=None, tooltip=f"Vende todas tus acciones de {sym} de golpe."):
            self.market_sold(mk.sell(sym, p["qty"]), o)
        if s.player_level() >= data.SHORT_LEVEL:
            if p.get("sq", 0) > 0:
                if ui.button("mk_cover", (bx, by, 238, 40), "CERRAR CORTO", "primary", size=12, sound=None):
                    r_ = mk.cover(sym)
                    self.audio.play("cashout" if r_ and r_ > 0 else "lose")
                    self.save_now()
            elif ui.button("mk_short", (bx, by, 238, 40), "VENDER EN CORTO", "primary", size=12,
                           enabled=qty > 0 and s.money >= qty * mk.bid(sym), sound=None,
                           tooltip="Ganas si el precio baja. Se bloquea como garantía lo que vendes."):
                if mk.short(sym, qty):
                    self.audio.play("chip1")
                    self.save_now()
        else:
            gfx.text(surf, f"Venta en corto: nivel {data.SHORT_LEVEL}", (bx + 119, by + 20), 12, "r", DIM,
                     anchor="center")
        gfx.text(surf, f"Comisión: {SPREAD * 100 * s.fx()['market_fee']:.1f}% entre compra y venta. El mercado "
                       "cambia de fase sin avisar y a veces se desploma.", (o.x + 16, o.bottom - 26), 10, "r", DIM,
                 max_w=o.w - 32)

    def market_sold(self, r_, o):
        if r_ is None:
            return
        self.audio.play("cashout" if r_ > 0 else "lose")
        self.fx.text(o.centerx, o.y, ("+" if r_ >= 0 else "") + fmt_money(r_), GREEN if r_ >= 0 else RED, 20)
        self.save_now()

    # ---------------------------------------------------------------- VIP
    def draw_vip(self, surf):
        ui = self.ui
        s = self.state
        a = CONTENT
        hero = pygame.Rect(a.x, a.y, a.w, 210)
        gfx.box(surf, hero, (*gfx.PURPLE_DK, 255), 14, ow=4, shadow_off=6)
        crown = icons.icon("crown", 120)
        surf.blit(crown, (hero.x + 40, hero.y + 42 + math.sin(ui.t * 2) * 5))
        x = hero.x + 200
        gfx.wavy_text(surf, "SALA VIP", (x, hero.y + 20), 26, GOLD_HI, ui.t, 2, 4, anchor="topleft", weight="bl")
        gfx.text_wrapped(surf, "Reinicia a cambio de fichas VIP. Cada ficha da +2% permanente y se gasta en "
                               "ventajas.", (x, hero.y + 62), 12, "r", (226, 214, 240), hero.w - 230)
        claim = s.claimable_chips()
        gfx.text(surf, f"Prestigio {s.prestige_level} (+{s.prestige_level * 2}%) · fichas {s.vip_chips}",
                 (x, hero.y + 116), 14, "b", TEXT)
        gfx.text(surf, f"Siguiente ficha: {fmt_money(s.next_chip_at())} ganados", (x, hero.y + 144), 12,
                 "r", (210, 196, 230), max_w=hero.right - 340 - x)
        if ui.button("prestige", (hero.right - 320, hero.bottom - 64, 300, 50),
                     f"Reiniciar y cobrar {claim}", "gold", enabled=claim > 0, size=14):
            self.modal = ("confirm", "¿Hacer prestigio?",
                          f"Reinicias dinero, negocios, mejoras y mejoras únicas (las legendarias se quedan) y cobras "
                          f"{claim} fichas VIP. Mantienes logros, hazañas, nivel de jugador y ventajas VIP.",
                          self.do_prestige)
        gfx.text(surf, "VENTAJAS PERMANENTES", (a.x, hero.bottom + 20), 14, "bl", ORANGE)
        area = pygame.Rect(a.x, hero.bottom + 44, a.w, a.bottom - hero.bottom - 44)
        cw = (a.w - 16 - 12) // 2
        rows = (len(VIP_PERKS) + 1) // 2
        rh = 104
        off = ui.begin_scroll("vip", area, rows * rh + 8)
        for i, p in enumerate(VIP_PERKS):
            r = pygame.Rect(area.x + (i % 2) * (cw + 12), area.y + 2 + (i // 2) * rh - off, cw, rh - 12)
            if r.bottom < area.y - 10 or r.y > area.bottom:
                continue
            lvl = s.vip(p.id)
            maxed = lvl >= p.max_level
            gfx.box(surf, r, (*(gfx.lerp_col(PANEL_HI, PURPLE, 0.35) if lvl else PANEL_HI), 255), 10, ow=4,
                    shadow_off=4)
            surf.blit(icons.icon("crown" if lvl else "lock", 36), (r.x + 12, r.centery - 18))
            name = p.name + (f"  {lvl}/{p.max_level}" if p.max_level > 1 else "")
            gfx.text(surf, name, (r.x + 58, r.y + 12), 14, "b", TEXT, max_w=r.w - 190)
            desc = p.desc(lvl if lvl else 1) if maxed or lvl else p.desc(1)
            if lvl and not maxed:
                desc = f"Ahora: {p.desc(lvl)} Siguiente: {p.desc(lvl + 1)}"
            lines = gfx.wrap(desc, 10, "r", r.w - 190)[:3]
            ui.tooltip(("vipt", p.id), r, name + "\n" + desc.replace(" Siguiente:", "\nSiguiente:"), INFO_DELAY, title="legendary")
            for li, ln in enumerate(lines):
                gfx.text(surf, ln, (r.x + 58, r.y + 38 + li * 16), 10, "r", MUTED)
            if maxed:
                gfx.text(surf, "AL MÁXIMO", (r.right - 20, r.centery), 12, "b", GREEN, anchor="midright")
            else:
                cost = s.vip_cost(p.id)
                if ui.button(("vip", p.id), (r.right - 124, r.centery - 22, 110, 44), f"{cost} fichas", "primary",
                             enabled=s.vip_chips >= cost, size=12, sound=None):
                    if s.buy_vip(p.id):
                        self.audio.play("unlock")
                        self.fx.sparks(r.centerx, r.centery, 30, PURPLE)
                        self.toast("Ventaja VIP", f"{p.name} nivel {s.vip(p.id)}", PURPLE, "crown")
                        if p.id == "alley":
                            self.log("Alguien te espera en el callejón... (botón junto al registro)", (190, 120, 230))
        ui.end_scroll("vip")

    def do_prestige(self):
        s = self.state
        claim = s.claimable_chips()
        if s.prestige():
            for g in self.games.values():
                g.on_hide()
            self.games = {}
            self.current_game = None
            self.money_disp = s.money
            self.audio.play("prestige")
            self.fx.confetti(W / 2, 0, 160, w=W)
            self.toast("Prestigio", f"+{claim} fichas VIP", PURPLE, "crown")
            self.log(f"¡Prestigio! +{claim} fichas VIP.", PURPLE)
            self.save_now()

    # ------------------------------------------------------ mercado negro
    def open_black_market(self):
        s = self.state
        if s.bm_ready() and s.bm_offer is None:
            s.bm_make_offer()
        self.bm_pick = [None, None]
        self.modal = "blackmarket"

    def draw_black_market(self, surf):
        ui = self.ui
        s = self.state
        r = pygame.Rect(0, 0, 900, 620)
        r.center = (W // 2, H // 2)
        gfx.box(surf, r, (30, 20, 36, 255), 14, outline=(150, 80, 190), ow=4, shadow_off=8)
        gfx.wavy_text(surf, "MERCADO NEGRO", (r.x + 30, r.y + 22), 22, (220, 150, 255), ui.t, 2, 4, anchor="topleft",
                      weight="bl")
        if ui.button("bm_close", (r.right - 60, r.y + 16, 44, 44), "X", "dark", size=14):
            self.modal = None
            return
        if not s.bm_ready():
            gfx.text_wrapped(surf, "El callejón está vacío. Un papel en el suelo dice: «vuelvo en "
                                   f"{fmt_time(s.bm_remaining())}».", (r.x + 30, r.y + 80), 14, "r", MUTED, r.w - 60)
            return
        off = s.bm_offer or s.bm_make_offer()
        gfx.text_wrapped(surf, "«Psst... Te consigo una trampa que no falla. Una sola jugada, gana seguro. Eso sí, "
                               "quiero algo tuyo a cambio: una de tus mejoras únicas.»", (r.x + 30, r.y + 64), 12, "r",
                         (220, 200, 230), r.w - 60)
        if not off["cheats"] or not off["price"]:
            gfx.text_wrapped(surf, "«No tienes nada que me interese (necesito una mejora única que no sea "
                                   "legendaria), o no juegas a nada donde pueda ayudarte. Vuelve luego.»",
                             (r.x + 30, r.y + 130), 14, "r", MUTED, r.w - 60)
            return
        gfx.text(surf, "1 · ELIGE TU TRAMPA", (r.x + 30, r.y + 120), 14, "bl", ORANGE)
        cw = (r.w - 60 - 20) // 3
        for i, gid in enumerate(off["cheats"]):
            cr = pygame.Rect(r.x + 30 + i * (cw + 10), r.y + 148, cw, 150)
            sel = self.bm_pick[0] == gid
            gfx.box(surf, cr, (*(gfx.lerp_col((50, 34, 60), (190, 100, 240), 0.45) if sel else (50, 34, 60)), 255), 10,
                    outline=(200, 110, 255) if sel else LINE, ow=4, shadow_off=4)
            surf.blit(icons.icon(gid, 44), (cr.x + 12, cr.y + 12))
            name, desc = CHEATS[gid]
            gfx.text(surf, name, (cr.x + 64, cr.y + 16), 12, "b", TEXT, max_w=cw - 72)
            gfx.text(surf, GAME_BY_ID[gid].name, (cr.x + 64, cr.y + 38), 10, "r", MUTED, max_w=cw - 72)
            for li, ln in enumerate(gfx.wrap(desc, 10, "r", cw - 24)[:4]):
                gfx.text(surf, ln, (cr.x + 12, cr.y + 70 + li * 16), 10, "r", (220, 210, 230))
            ui.tooltip(("bmct", gid), cr, f"{name} ({GAME_BY_ID[gid].name})\n{desc}", INFO_DELAY, title=(205, 120, 255))
            if ui.clicked_area(("bmc", gid), cr, sound="ui"):
                self.bm_pick[0] = gid
        gfx.text(surf, "2 · ELIGE QUÉ LE DAS", (r.x + 30, r.y + 318), 14, "bl", ORANGE)
        for i, uid in enumerate(off["price"]):
            u = UNIQUE_BY_ID[uid]
            col = RARITY_COL[u.rarity]
            cr = pygame.Rect(r.x + 30 + i * (cw + 10), r.y + 346, cw, 130)
            sel = self.bm_pick[1] == uid
            gfx.box(surf, cr, (*(gfx.lerp_col((50, 34, 60), col, 0.35) if sel else (50, 34, 60)), 255), 10,
                    outline=col if sel else LINE, ow=4, shadow_off=4)
            surf.blit(icons.badge(u.icon, 40, col), (cr.x + 12, cr.y + 12))
            gfx.text(surf, u.name, (cr.x + 60, cr.y + 14), 12, "b", TEXT, max_w=cw - 68)
            gfx.text(surf, RARITY_NAME[u.rarity], (cr.x + 60, cr.y + 36), 10, "b", col)
            for li, ln in enumerate(gfx.wrap(u.desc, 10, "r", cw - 24)[:3]):
                gfx.text(surf, ln, (cr.x + 12, cr.y + 66 + li * 16), 10, "r", (220, 210, 230))
            ui.tooltip(("bmut", uid), cr, f"{u.name} ({RARITY_NAME[u.rarity]})\n{u.desc}", INFO_DELAY, title=RARITY_COL[u.rarity])
            if ui.clicked_area(("bmu", uid), cr, sound="ui"):
                self.bm_pick[1] = uid
        ok = all(self.bm_pick)
        if ui.button("bm_deal", (r.centerx - 160, r.bottom - 82, 320, 56), "CERRAR EL TRATO", "red", enabled=ok,
                     size=15, sound=None):
            gid, uid = self.bm_pick
            if s.bm_deal(gid, uid):
                self.audio.play("unlock")
                self.toast("Trato hecho", f"{CHEATS[gid][0]} lista en {GAME_BY_ID[gid].name}. Pierdes "
                                          f"«{UNIQUE_BY_ID[uid].name}».", (200, 110, 255), gid)
                self.log(f"Mercado negro: {CHEATS[gid][0]} por {UNIQUE_BY_ID[uid].name}", (200, 110, 255))
                self.modal = None

    # ------------------------------------------------------------- logros
    def draw_achievements(self, surf):
        ui = self.ui
        s = self.state
        a = CONTENT
        n = len(s.achievements)
        tot = len(data.ACHIEVEMENTS)
        gfx.text(surf, f"LOGROS {n}/{tot}", (a.x, a.y + 12), 18, "bl", ORANGE, anchor="midleft")
        gfx.text(surf, f"+{n}% a clics e ingresos", (a.right - 16, a.y + 12), 12, "r", MUTED, anchor="midright")
        pb = pygame.Rect(a.x, a.y + 34, a.w - 16, 14)
        gfx.rrect(surf, pb, (20, 26, 30, 255), 4, border=LINE, bw=2)
        gfx.rrect(surf, (pb.x + 2, pb.y + 2, max(6, int((pb.w - 4) * n / tot)), pb.h - 4), (*ORANGE, 255), 2)
        area = pygame.Rect(a.x, a.y + 62, a.w, a.h - 62)
        cols = 3
        cw = (area.w - 16 - 10 * (cols - 1)) // cols
        rh = 84
        rows = (tot + cols - 1) // cols
        off = ui.begin_scroll("ach", area, rows * (rh + 10) + 8)
        for i, ach in enumerate(data.ACHIEVEMENTS):
            r = pygame.Rect(area.x + (i % cols) * (cw + 10), area.y + 2 + (i // cols) * (rh + 10) - off, cw, rh)
            if r.bottom < area.y - 10 or r.y > area.bottom:
                continue
            got = ach.id in s.achievements
            gfx.box(surf, r, (*(gfx.lerp_col(PANEL_HI, GOLD, 0.25) if got else PANEL_LO), 255), 10, ow=4, shadow_off=4)
            surf.blit(icons.icon("trophy" if got else "trophy_off", 40), (r.x + 10, r.centery - 20))
            gfx.text(surf, ach.name, (r.x + 58, r.y + 12), 12, "b", GOLD_HI if got else MUTED, max_w=r.w - 66)
            gfx.text_wrapped(surf, ach.desc, (r.x + 58, r.y + 32), 12, "r", (220, 214, 196) if got else DIM, r.w - 66)
            ui.tooltip(("acht", ach.id), r, f"{ach.name}\n{ach.desc}", INFO_DELAY, title=GOLD_HI)
        ui.end_scroll("ach")

    # ------------------------------------------------------- estadísticas
    def draw_stats(self, surf):
        s = self.state
        st = s.stats
        a = CONTENT
        ui = self.ui
        wr = st["bets_won"] / st["bets"] * 100 if st["bets"] else 0
        lvl, prog, nxt = s.level_progress()
        groups = [
            ("General", "stats", [("Tiempo jugado", fmt_time(st["play_time"])), ("Dinero", fmt_money(s.money)),
                                  ("Ganado esta partida", fmt_money(st["run_earned"])),
                                  ("Ganado en total", fmt_money(st["all_time_earned"])),
                                  ("Nivel de jugador", f"{lvl} · {s.title()}"),
                                  ("Prestigios", fmt_int(st["prestiges"]))]),
            ("Clicker", "click", [("Clics", fmt_int(st["clicks"])), ("Auto-clics", fmt_int(st["auto_clicks"])),
                                  ("Críticos", fmt_int(st["crits"])), ("Mejor combo", fmt_int(st["best_combo"])),
                                  ("Ganado con clics", fmt_money(st["click_earned"])),
                                  ("Ganado con auto-clics", fmt_money(st.get("auto_earned", 0.0))),
                                  ("Monedas doradas", fmt_int(st["golden_clicked"]))]),
            ("Ingresos pasivos", "business", [("Total", fmt_money(s.total_passive()) + "/s"),
                                      ("De negocios", fmt_money(s.income_per_sec()) + "/s"),
                                      ("De auto-clics", fmt_money(s.auto_income_per_sec()) + "/s"),
                                      ("Ganado con negocios", fmt_money(st["passive_earned"])),
                                      ("Negocios", fmt_int(s.total_buildings())),
                                      ("Mejoras únicas", f"{len(s.uniques)}/{len(UNIQUES)}"),
                                      ("Oportunidades vistas", fmt_int(st.get("opps_seen", 0)))]),
            ("Casino", "chip", [("Apuestas", fmt_int(st["bets"])),
                                ("Ganadas", f"{fmt_int(st['bets_won'])} ({wr:.0f}%)"),
                                ("Total apostado", fmt_money(st["wagered"])),
                                ("Balance", fmt_money(st["gamble_won"] - st["gamble_lost"])),
                                ("Mayor premio", fmt_money(st["biggest_win"])),
                                ("Mejor multiplicador", f"x{fmt_num(st['best_multiplier'])}"),
                                ("Hazañas", f"{sum(1 for f in FEATS if s.flags.get(f.id))}/{len(FEATS)}"),
                                ("Ventajas usadas", fmt_int(st.get("hints_used", 0))),
                                ("Escudos usados", fmt_int(st.get("shields_used", 0))),
                                ("Operaciones en bolsa", fmt_int(st.get("trades", 0)))]),
        ]
        played = [g for g in GAMES if s.game_stats.get(g.id)]
        colw = (a.w - 16 - 12) // 2
        heights = [56 + len(rows) * 30 for _, _, rows in groups]
        total_h = max(heights[0] + heights[2], heights[1] + heights[3]) + 24 + 60 + len(played) * 28
        area = pygame.Rect(a.x, a.y, a.w, a.h)
        off = ui.begin_scroll("stats", area, total_h)
        ys = [a.y - off, a.y - off]
        for gi, (title, ic, rows) in enumerate(groups):
            c = 0 if gi in (0, 2) else 1
            r = pygame.Rect(a.x + c * (colw + 12), ys[c], colw, heights[gi])
            gfx.box(surf, r, (*PANEL_HI, 255), 10, ow=4, shadow_off=4)
            surf.blit(icons.icon(ic, 26), (r.x + 14, r.y + 12))
            gfx.text(surf, title.upper(), (r.x + 48, r.y + 25), 14, "bl", ORANGE, anchor="midleft")
            for k, (key, val) in enumerate(rows):
                yy = r.y + 52 + k * 30
                gfx.text(surf, key, (r.x + 16, yy), 12, "r", MUTED)
                gfx.text(surf, val, (r.right - 16, yy), 12, "b", TEXT, anchor="topright", max_w=colw - 200)
            ys[c] += heights[gi] + 12
        y = max(ys) + 4
        if played:
            r = pygame.Rect(a.x, y, a.w - 16, 56 + len(played) * 28)
            gfx.box(surf, r, (*PANEL_HI, 255), 10, ow=4, shadow_off=4)
            gfx.text(surf, "POR JUEGO", (r.x + 16, r.y + 24), 14, "bl", ORANGE, anchor="midleft")
            for k, g in enumerate(played):
                yy = r.y + 50 + k * 28
                gs = s.game_stats[g.id]
                net = gs["returned"] - gs["wagered"]
                surf.blit(icons.icon(g.id, 24), (r.x + 16, yy - 4))
                gfx.text(surf, g.name, (r.x + 48, yy), 12, "b", TEXT)
                gfx.text(surf, f"{gs['played']} jugadas · {gs['won']} ganadas", (r.x + 330, yy), 12, "r", MUTED)
                gfx.text(surf, ("+" if net >= 0 else "") + fmt_money(net), (r.right - 16, yy), 12, "b",
                         GREEN if net >= 0 else RED, anchor="topright")
        ui.end_scroll("stats")

    # ------------------------------------------------------------- toasts
    def draw_toasts(self, surf):
        y = H - 18
        for t in reversed(self.toasts):
            a = t["age"]
            k = gfx.ease_out_back(min(1, a / 0.45))
            out = max(0.0, (a - (t["life"] - 0.4)) / 0.4)
            lines = gfx.wrap(t["text"], 12, "r", 270)[:4]
            lh = gfx.line_height(12)
            h = 50 + len(lines) * lh
            w = 360
            x = W - 16 - w * k + out * (w + 20)
            y -= h
            r = pygame.Rect(int(x), y, w, h)
            gfx.box(surf, r, (*PANEL_LO, 250), 10, outline=LINE, ow=4, shadow_off=6)
            gfx.rrect(surf, (r.x + 4, r.y + 4, 8, r.h - 8), (*t["color"], 255), 3)
            surf.blit(icons.icon(t["icon"], 40), (r.x + 20, r.y + 12))
            gfx.text(surf, t["title"], (r.x + 72, r.y + 14), 14, "b", t["color"], max_w=w - 86)
            for i, ln in enumerate(lines):
                gfx.text(surf, ln, (r.x + 72, r.y + 38 + i * lh), 12, "r", TEXT)
            y -= 10

    # -------------------------------------------------------------- modal
    def draw_modal(self, surf):
        ui = self.ui
        if not hasattr(self, "_dim"):
            self._dim = pygame.Surface((W, H), pygame.SRCALPHA)
            self._dim.fill((6, 10, 12, 180))
        surf.blit(self._dim, (0, 0))
        if self.modal == "settings":
            r = pygame.Rect(0, 0, 560, 598)
            r.center = (W // 2, H // 2)
            gfx.box(surf, r, (*PANEL, 255), 14, ow=4, shadow_off=8)
            surf.blit(icons.icon("gear", 40), (r.x + 24, r.y + 20))
            gfx.text(surf, "AJUSTES", (r.x + 76, r.y + 40), 22, "bl", ORANGE, anchor="midleft")
            st = self.state.settings
            y = r.y + 96
            for key, label in (("master", "Volumen general"), ("sfx", "Efectos"), ("music", "Música")):
                gfx.text(surf, label, (r.x + 32, y), 14, "b", TEXT)
                gfx.text(surf, f"{int(st.get(key, 0.8) * 100)}%", (r.right - 32, y), 14, "b", ORANGE, anchor="topright")
                old = st.get(key, 0.8)
                st[key] = ui.slider(("sl", key), (r.x + 36, y + 38, r.w - 72, 12), old)
                if abs(st[key] - old) > 1e-4:
                    self.audio.apply_music()
                    if key != "music":
                        self.audio.play("tick1", throttle=0.08)
                y += 80
            mo = st.get("music_on")
            if ui.button("music", (r.x + 30, y, 240, 52), "Música: SÍ" if mo else "Música: NO",
                         "primary" if mo else "dark", icon="music", size=13):
                self.audio.set_music(not mo)
            if ui.button("save2", (r.x + 290, y, 240, 52), "Guardar ahora", "dark", size=13):
                self.save_now(False)
            y += 66
            fs = bool(st.get("fullscreen"))
            k = self.window_scale()
            gfx.text(surf, "Tamaño de ventana", (r.x + 32, y + 2), 14, "b", TEXT)
            gfx.text(surf, "pantalla completa" if fs else ("ajustada · " if st.get("win_scale") is None else "")
                     + f"{round(k * 100)}%", (r.right - 32, y + 2), 14, "b", ORANGE, anchor="topright")
            y += 32
            fit = self.fit_scale()
            smaller = [v for v in WIN_SCALES if v < k - 0.005]
            bigger = [v for v in WIN_SCALES if k + 0.005 < v <= fit + 0.005]
            if ui.button("win_minus", (r.x + 30, y, 60, 48), "-", "dark", size=16, enabled=bool(smaller) and not fs,
                         tooltip="Ventana más pequeña"):
                self.set_window_scale(smaller[-1])
            if ui.button("win_plus", (r.x + 98, y, 60, 48), "+", "dark", size=16, enabled=bool(bigger) and not fs,
                         tooltip="Ventana más grande"):
                self.set_window_scale(bigger[0])
            if ui.button("win_fit", (r.x + 166, y, 160, 48), "Ajustar", "dark", size=12,
                         tooltip="El tamaño más grande que cabe en tu pantalla"):
                self.set_window_scale(None)
            if ui.button("win_fs", (r.x + 334, y, 196, 48), "En ventana" if fs else "Pantalla completa",
                         "primary" if fs else "dark", size=12, tooltip="También con F11"):
                self.toggle_fullscreen()
            y += 66
            if ui.button("reset", (r.x + 30, y, 240, 52), "Borrar partida", "red", size=13):
                self.modal = ("confirm", "¿Borrar la partida?",
                              "Se perderá TODO: dinero, prestigio, logros y estadísticas. No se puede deshacer.",
                              self.hard_reset)
                return
            if ui.button("close", (r.x + 290, y, 240, 52), "Cerrar", "dark", size=13):
                self.modal = None
        elif self.modal == "appearance":
            self.draw_appearance(surf)
        elif self.modal == "newspaper":
            self.draw_newspaper(surf)
        elif self.modal == "blackmarket":
            self.draw_black_market(surf)
        elif isinstance(self.modal, tuple) and self.modal[0] == "confirm":
            _, title, text, fn = self.modal
            r = pygame.Rect(0, 0, 560, 300)
            r.center = (W // 2, H // 2)
            gfx.box(surf, r, (*PANEL, 255), 14, ow=4, shadow_off=8)
            gfx.text(surf, title, (r.centerx, r.y + 36), 18, "bl", ORANGE, anchor="center")
            gfx.text_wrapped(surf, text, (r.x + 36, r.y + 76), 12, "r", MUTED, r.w - 72)
            if ui.button("cf_no", (r.x + 30, r.bottom - 80, 230, 54), "Cancelar", "dark", size=14):
                self.modal = None
            if ui.button("cf_yes", (r.right - 260, r.bottom - 80, 230, 54), "Confirmar", "red", size=14):
                self.modal = None
                fn()

    def draw_newspaper(self, surf):
        ui = self.ui
        mk = self.market
        news = mk.active
        if not news:
            self.modal = None
            return
        paper, paper2, ink, faded = (238, 228, 202), (226, 214, 186), (36, 30, 24), (106, 92, 76)
        accent = (150, 40, 36)
        tw = 700
        tl = gfx.wrap(news["title"], 24, "bl", tw)
        bl = gfx.wrap(news["body"], 16, "r", tw)
        hh = 150 + len(tl) * (gfx.line_height(24) + 4) + 18 + len(bl) * (gfx.line_height(16) + 6)
        hh += 80 if mk.news_pro() else 0
        r = pygame.Rect(0, 0, 780, max(500, hh + 200))
        r.center = (W // 2, H // 2)
        gfx.box(surf, r, (*paper, 255), 4, ow=4, shadow_off=10)
        # textura de papel: líneas muy suaves
        for yy in range(r.y + 6, r.bottom - 6, 6):
            pygame.draw.line(surf, paper2, (r.x + 6, yy), (r.right - 6, yy), 1)
        inner = r.inflate(-40, -36)
        # cabecera
        top = inner.y
        gfx.text(surf, "Nº 1.337", (inner.x, top + 4), 12, "b", faded, shadow=False)
        gfx.text(surf, "0,10 €", (inner.right, top + 4), 12, "b", faded, anchor="topright", shadow=False)
        gfx.text(surf, "FINANCIAL DIMES", (r.centerx, top + 40), 36, "bl", ink, anchor="center", shadow=False)
        gfx.text(surf, "★", (r.centerx - gfx.text_w("FINANCIAL DIMES", 36, "bl") // 2 - 30, top + 40), 20, "bl",
                 accent, anchor="center", shadow=False)
        gfx.text(surf, "★", (r.centerx + gfx.text_w("FINANCIAL DIMES", 36, "bl") // 2 + 30, top + 40), 20, "bl",
                 accent, anchor="center", shadow=False)
        gfx.text(surf, "«Sin dimes ni diretes: solo lo que mueve tu dinero»", (r.centerx, top + 74), 14, "r", faded,
                 anchor="center", shadow=False)
        y = top + 90
        pygame.draw.line(surf, ink, (inner.x, y), (inner.right, y), 3)
        pygame.draw.line(surf, ink, (inner.x, y + 5), (inner.right, y + 5), 1)
        gfx.text(surf, "EDICIÓN ESPECIAL · ECONOMÍA Y MERCADOS", (inner.x, y + 22), 12, "b", ink, anchor="midleft", shadow=False)
        # temporizador: sello en la esquina
        rem = mk.news_remaining()
        stamp = pygame.Rect(0, 0, 190, 30)
        stamp.midright = (inner.right, y + 22)
        gfx.rrect(surf, stamp, (*accent, 255), 4)
        gfx.text(surf, f"VÁLIDA {int(rem) // 60}:{int(rem) % 60:02d}", stamp.center, 14, "bl", (250, 236, 220),
                 anchor="center", shadow=False)
        y += 40
        pygame.draw.line(surf, ink, (inner.x, y), (inner.right, y), 1)
        y += 20
        x0 = r.centerx - tw // 2
        for ln in tl:
            gfx.text(surf, ln, (x0, y), 24, "bl", ink, shadow=False)
            y += gfx.line_height(24) + 4
        y += 6
        pygame.draw.line(surf, faded, (x0, y), (x0 + 120, y), 2)
        y += 14
        for ln in bl:
            gfx.text(surf, ln, (x0, y), 16, "r", ink, shadow=False)
            y += gfx.line_height(16) + 6
        if mk.news_pro():
            y += 12
            box = pygame.Rect(x0, y, tw, 0)
            if news["effects"]:
                names = ", ".join(f"{s} ({self.market.assets[s].name})" for s in news["effects"])
                txt = f"FUENTES CONTRASTADAS · Afecta a: {names}."
            else:
                txt = "FUENTES CONTRASTADAS · Esto es puro ruido: no mueve ningún valor."
            lines = gfx.wrap(txt, 14, "b", tw - 24)
            box.h = len(lines) * (gfx.line_height(14) + 4) + 16
            gfx.rrect(surf, box, (*paper2, 255), 4, border=(40, 90, 150), bw=2)
            for k, ln in enumerate(lines):
                gfx.text(surf, ln, (box.x + 12, box.y + 9 + k * (gfx.line_height(14) + 4)), 14, "b", (40, 90, 150), shadow=False)
        # pie
        fy = inner.bottom - 92
        pygame.draw.line(surf, ink, (inner.x, fy), (inner.right, fy), 1)
        gfx.text(surf, "El Financial Dimes no responde de tus inversiones.", (r.centerx, fy + 18), 14, "r", faded,
                 anchor="center", shadow=False)
        if ui.button("np_close", (r.centerx - 110, inner.bottom - 54, 220, 50), "Cerrar el periódico", "dark",
                     size=14):
            self.modal = None

    def draw_appearance(self, surf):
        ui = self.ui
        s = self.state
        r = pygame.Rect(0, 0, 980, 640)
        r.center = (W // 2, H // 2)
        gfx.box(surf, r, (*PANEL, 255), 14, ow=4, shadow_off=8)
        gfx.text(surf, "ASPECTO", (r.x + 30, r.y + 34), 22, "bl", ORANGE, anchor="midleft")
        gfx.text(surf, "Se desbloquean subiendo de nivel de jugador.", (r.x + 200, r.y + 36), 12, "r", MUTED,
                 anchor="midleft")
        if ui.button("ap_close", (r.right - 60, r.y + 14, 44, 44), "X", "dark", size=14):
            self.modal = None
            return
        for row, (title, attr) in enumerate((("MONEDA DEL CLICKER", "theme_coin"), ("TAPETE DE LAS MESAS", "theme_felt"))):
            y0 = r.y + 76 + row * 280
            gfx.text(surf, title, (r.x + 30, y0), 14, "bl", GOLD)
            cw = (r.w - 60 - 9 * 8) // 10
            levels = data.THEME_LEVELS[attr]
            have = [tid for tid in levels if s.theme_unlocked(tid, attr)]
            left = [lv for tid, lv in levels.items() if tid not in have]
            if left:
                cr = pygame.Rect(r.x + 30 + len(have) * (cw + 8), y0 + 26, cw, 230)
                gfx.box(surf, cr, (*PANEL_LO, 255), 8, outline=LINE, ow=4, shadow_off=3)
                gfx.text(surf, "?", (cr.centerx, cr.y + 76), 32, "bl", DIM, anchor="center")
                for li, ln in enumerate(gfx.wrap(f"{len(left)} por desbloquear", 10, "r", cw - 8)[:3]):
                    gfx.text(surf, ln, (cr.centerx, cr.y + 150 + li * 16), 10, "b", DIM, anchor="midtop")
                gfx.text(surf, f"nivel {min(left)}", (cr.centerx, cr.bottom - 22), 10, "b", DIM, anchor="center")
            for i, tid in enumerate(have):
                name, lvl = data.theme_name(tid, attr), levels[tid]
                cr = pygame.Rect(r.x + 30 + i * (cw + 8), y0 + 26, cw, 230)
                ok = True
                sel = getattr(s, attr) == tid
                gfx.box(surf, cr, (*(gfx.lerp_col(PANEL_HI, ORANGE, 0.35) if sel else PANEL_HI), 255), 8,
                        outline=ORANGE if sel else LINE, ow=4, shadow_off=3)
                if attr == "theme_coin":
                    img = skins.coin_skin(tid, 72)
                else:
                    img = skins.felt_surf(cw - 12, 120, (40, 96, 74), tid, 10)
                if not ok:
                    img = img.copy()
                    img.set_alpha(70)
                surf.blit(img, img.get_rect(center=(cr.centerx, cr.y + 76)))
                for li, ln in enumerate(gfx.wrap(name, 10, "r", cw - 8)[:3]):
                    gfx.text(surf, ln, (cr.centerx, cr.y + 150 + li * 16), 10, "b", TEXT if ok else DIM, anchor="midtop")
                gfx.text(surf, "elegido" if sel else (f"nivel {lvl}" if not ok else ""), (cr.centerx, cr.bottom - 22),
                         10, "b", ORANGE if sel else DIM, anchor="center")
                if ok and ui.clicked_area(("th", attr, tid), cr, sound="ui"):
                    setattr(s, attr, tid)

    def hard_reset(self):
        settings = self.state.settings
        fresh = GameState()
        self.state.__dict__.update(fresh.__dict__)
        self.state.settings = settings
        from .market import Market
        self.market = Market(self.state)
        self.games = {}
        self.current_game = None
        self.money_disp = 0
        self.logs = []
        self.last_level = 0
        self.log("Partida borrada. ¡Empiezas de cero!", RED)
        self.save_now()
