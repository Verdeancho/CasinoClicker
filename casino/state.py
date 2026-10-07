"""Estado del juego y toda la lógica económica."""
import base64
import json
import math
import os
import random
import time
import zlib

from . import data
from .data import (BUILDINGS, BUILDING_BY_ID, BUILDING_COST_GROWTH, BUILDING_TIERS, GAME_BY_ID, UPGRADE_BY_ID,
                   VIP_BY_ID, RTP_CAP, HINTS, UNIQUES, UNIQUE_BY_ID, RARITIES, OPP_RARITY, OPP_GAP, OPP_BARGAIN,
                   FEATS, XP_BASE, XP_GROWTH, MAX_PLAYER_LEVEL, SHIELD_LEVELS, HINT_COOLDOWN_MAX, HINT_COOLDOWN_MIN,
                   SPECIAL_COOLDOWNS, BLACK_MARKET_COOLDOWN, POKER_RAKE_EDGE, INHERIT, THEMES, HOT_GAP,
                   HOT_DURATION, HOT_MULT, HOT_POT_SECS)

SAVE_VERSION = 2
SAVE_MAGIC = b"CCSAVE1:"
ENCODE_SAVES = False  # main.py lo activa en el ejecutable: la partida se guarda comprimida y codificada
RARITY_RANK = {r: i for i, r in enumerate(RARITIES)}
SAVE_REV = 1          # formato de la partida (las anteriores no lo tienen)
_AUDIT = {"dice": (50, 0.75, 1.5)}
_PEAK = 1e6


def _default_stats():
    return {
        "clicks": 0, "auto_clicks": 0, "click_earned": 0.0, "passive_earned": 0.0, "auto_earned": 0.0,
        "all_time_earned": 0.0, "run_earned": 0.0, "wagered": 0.0, "gamble_won": 0.0,
        "gamble_lost": 0.0, "bets": 0, "bets_won": 0, "bets_lost": 0, "streak": 0,
        "best_streak": 0, "worst_streak": 0, "lose_streak": 0, "best_multiplier": 0.0,
        "biggest_win": 0.0, "biggest_loss": 0.0, "golden_clicked": 0, "prestiges": 0,
        "best_combo": 0, "crits": 0, "play_time": 0.0, "max_money": 0.0,
        "hints_used": 0, "xp": 0.0, "uniques_bought": 0, "opps_seen": 0, "opps_since_leg": 0,
        "bm_deals": 0, "shields_used": 0, "trades": 0, "shield_level_granted": 0, "hot_earned": 0.0,
        "hot_tables": 0,
    }


class GameState:
    def __init__(self):
        self.money = 0.0
        self.upgrades = {}
        self.buildings = {}
        self.games_unlocked = set()
        self.achievements = set()
        self.prestige_level = 0      # fichas VIP ganadas en total (dan bonus)
        self.vip_chips = 0           # fichas VIP sin gastar
        self.vip_perks = {}          # id -> nivel
        self.jackpot = 0.0
        self.stats = _default_stats()
        self.game_stats = {}         # id -> {"played","won","wagered","returned","best"}
        self.flags = {}
        self.counters = {}           # contadores de hazañas (rachas, empates...)
        self.last_time = time.time()
        self.settings = {"master": 0.8, "sfx": 0.8, "music": 0.5, "music_on": False, "muted": False}
        self.variants = set()        # "juego:variante"
        self.hint_at = {}            # clave -> instante (reloj real) en que vuelve a estar lista
        self.uniques = set()
        self.opp = None              # oportunidad activa: {"uid","price","end","dur","bargain"}
        self.opp_next = 600.0        # tiempo de juego en que aparecerá la siguiente
        self.shields = 0
        self.shield_armed = False
        self.bm_next = 0.0           # tiempo de juego en que vuelve el mercader
        self.bm_offer = None         # {"cheats": [...], "price": [...]} mientras está abierto el trato
        self.cheat = None            # juego con una trampa preparada
        self.market = {}             # estado guardado de la bolsa
        self.theme_coin = "cobre"
        self.theme_felt = "clasico"
        self.hot = None              # mesa caliente: {"gid","end","pot","pot0"}
        self.hot_next = 900.0        # tiempo de juego en que se encenderá la siguiente
        self.hot_extra = 0.0         # bonus de la última victoria en mesa caliente (para mostrarlo)
        self.rev = SAVE_REV
        # Estado de ejecución (no se guarda)
        self.buffs = []              # dicts: id, name, mult, end, total
        self.combo = 0
        self.last_click = 0.0
        self.events = []             # (tipo, texto, color) para que la UI los muestre
        self._cache_ips = None
        self._fx = None

    # ------------------------------------------------------------------ util
    def vip(self, pid):
        return self.vip_perks.get(pid, 0)

    def lvl(self, uid):
        return self.upgrades.get(uid, 0)

    def _base_earned(self):
        st = self.stats
        base = st.get("click_earned", 0.0) + st.get("passive_earned", 0.0) + st.get("auto_earned", 0.0)
        others = sum(max(0.0, g["returned"] - g["wagered"]) for gid, g in self.game_stats.items() if gid not in _AUDIT)
        return max(1000.0, 10 * base + others)

    def review(self):
        """Revisión única al pasar una partida antigua al formato actual."""
        f = self.flags
        if self.rev >= SAVE_REV:
            return f.get("s1")
        self.rev = SAVE_REV
        from .extra import T
        if f.get(T["old"]) and not f.get("s3"):
            f["s1"] = f.pop(T["old"])
        if f.get("s1"):
            return f["s1"]
        for gid, (n, wr, rtp) in _AUDIT.items():
            g = self.game_stats.get(gid)
            if g and g["played"] >= n and g["wagered"] > 0 and g["won"] / g["played"] >= wr                     and g["returned"] / g["wagered"] >= rtp:
                f["s1"] = gid
                return gid
        if self.stats.get("max_money", 0.0) >= _PEAK * self._base_earned():
            f["s1"] = "w"
        return f.get("s1")

    def special_pending(self):
        return bool(self.flags.get("s1")) and not self.flags.get("s3")

    def log(self, text, color="#e8e8f0", kind="log"):
        self.events.append((kind, text, color))

    def invalidate(self):
        self._cache_ips = None
        self._fx = None

    def earn(self, amount, source="other"):
        if amount <= 0:
            return
        self.money += amount
        self.stats["all_time_earned"] += amount
        self.stats["run_earned"] += amount
        if source == "click":
            self.stats["click_earned"] += amount
        elif source == "passive":
            self.stats["passive_earned"] += amount
        elif source == "auto":
            self.stats["auto_earned"] = self.stats.get("auto_earned", 0.0) + amount
        self.stats["max_money"] = max(self.stats["max_money"], self.money)

    def spend(self, amount):
        if amount > self.money + 1e-9:
            return False
        self.money -= amount
        if self.money < 1e-9:
            self.money = 0.0
        return True

    # ------------------------------------------------------- mejoras únicas
    def fx(self):
        """Suma de los efectos de las mejoras únicas (en caché)."""
        if self._fx is None:
            f = {"bld": {}, "passive": 1.0, "per_game": 0.0, "per_10b": 0.0, "per_unique": 0.0, "click": 1.0,
                 "auto": 0, "crit": 0.0, "crit_mult": 1.0, "combo": 0, "gold_freq": 0.0, "gold_reward": 1.0,
                 "opp_freq": 0.0, "opp_dur": 0, "opp_price": 0.0, "bm_cd": 0.0, "market_fee": 1.0,
                 "offline": 0.0, "hint_sure": set(), "special": set(), "hot_mult": 0.0, "hot_pot": 1.0,
                 "hot_dur": 0, "news_rel": 0.0, "news_true": 0}
            for uid in self.uniques:
                u = UNIQUE_BY_ID.get(uid)
                if not u:
                    continue
                for e in u.effects:
                    k = e[0]
                    if k == "bld":
                        f["bld"][e[1]] = f["bld"].get(e[1], 1.0) * e[2]
                    elif k in ("passive", "click", "crit_mult", "gold_reward", "market_fee", "hot_pot"):
                        f[k] *= e[1]
                    elif k in ("hint_sure", "special"):
                        f[k].add(e[1])
                    else:
                        f[k] += e[1]
            self._fx = f
        return self._fx

    def has_special(self, key):
        return key in self.fx()["special"]

    def hint_sure(self, gid):
        return gid in self.fx()["hint_sure"]

    def unique_available(self, uid):
        u = UNIQUE_BY_ID[uid]
        if uid in ("pick_netherite", "leg_pickaxe") and "pickaxe" not in self.games_unlocked:
            return False
        if uid.startswith("news_inside") or uid == "leg_news":
            if not self.flags.get("market_x2"):      # sin noticias todavía no tienen sentido
                return False
        return uid not in self.uniques and (u.requires is None or u.requires in self.uniques)

    # ---------------------------------------------------------------- buffs
    def buff_mult(self, bid):
        now = time.time()
        m = 1.0
        for b in self.buffs:
            if b["id"] == bid and b["end"] > now:
                m *= b["mult"]
        return m

    def add_buff(self, bid, name, mult, duration):
        now = time.time()
        self.buffs = [b for b in self.buffs if b["end"] > now and b["id"] != bid]
        self.buffs.append({"id": bid, "name": name, "mult": mult, "end": now + duration, "total": duration})
        self.invalidate()

    def tick_buffs(self):
        now = time.time()
        before = len(self.buffs)
        self.buffs = [b for b in self.buffs if b["end"] > now]
        if len(self.buffs) != before:
            self.invalidate()

    # ------------------------------------------------------------- bonuses
    def achievement_mult(self):
        return 1 + 0.01 * len(self.achievements)

    def prestige_mult(self):
        return 1 + 0.02 * self.prestige_level

    def global_mult(self):
        m = self.achievement_mult() * self.prestige_mult()
        if self.vip("whale"):
            m *= 2
        return m

    # ---------------------------------------------------- nivel de jugador
    @staticmethod
    def level_threshold(lvl):
        return 0.0 if lvl <= 0 else XP_BASE * XP_GROWTH ** (lvl - 1)

    def player_level(self):
        xp = self.stats.get("xp", 0.0)
        if xp < XP_BASE:
            return 0
        return min(MAX_PLAYER_LEVEL, int(math.log(xp / XP_BASE) / math.log(XP_GROWTH)) + 1)

    def level_progress(self):
        lvl = self.player_level()
        if lvl >= MAX_PLAYER_LEVEL:
            return lvl, 1.0, self.level_threshold(lvl)
        lo, hi = self.level_threshold(lvl), self.level_threshold(lvl + 1)
        return lvl, (self.stats.get("xp", 0.0) - lo) / max(1e-12, hi - lo), hi

    def title(self, lvl=None):
        lvl = self.player_level() if lvl is None else lvl
        t = data.TITLES[0][1]
        for n, name in data.TITLES:
            if lvl >= n:
                t = name
        return t

    def edge(self, gid, variant=None):
        rtp = self.game_rtp(gid, variant)
        return POKER_RAKE_EDGE if rtp is None else max(0.002, 1 - rtp)

    def add_xp(self, gid, bet, variant=None):
        self.stats["xp"] = self.stats.get("xp", 0.0) + bet * self.edge(gid, variant)

    # ----------------------------------------------------------- buildings
    def total_buildings(self):
        return sum(self.buildings.values())

    def cost_mult(self):
        return (1 - 0.04 * self.lvl("discount")) * (1 - 0.05 * self.vip("contacts"))

    def building_cost(self, bid, qty=1):
        b = BUILDING_BY_ID[bid]
        n = self.buildings.get(bid, 0)
        g = BUILDING_COST_GROWTH
        base = b.base_cost * self.cost_mult() * g ** n
        if qty == 1:
            return base
        return base * (g ** qty - 1) / (g - 1)

    def max_affordable(self, bid):
        b = BUILDING_BY_ID[bid]
        n = self.buildings.get(bid, 0)
        g = BUILDING_COST_GROWTH
        base = b.base_cost * self.cost_mult() * g ** n
        if self.money < base:
            return 0
        q = int(math.log(self.money * (g - 1) / base + 1) / math.log(g))
        while q > 0 and self.building_cost(bid, q) > self.money + 1e-9:
            q -= 1
        return q

    def buy_building(self, bid, qty=1):
        if qty <= 0:
            return False
        cost = self.building_cost(bid, qty)
        if not self.spend(cost):
            return False
        self.buildings[bid] = self.buildings.get(bid, 0) + qty
        self.invalidate()
        return True

    def tier_count(self, bid):
        return sum(1 for i in range(len(BUILDING_TIERS)) if self.lvl(f"b_{bid}_{i}"))

    def building_unit_income(self, bid):
        b = BUILDING_BY_ID[bid]
        return b.base_income * (2 ** self.tier_count(bid)) * self.fx()["bld"].get(bid, 1.0)

    def passive_breakdown(self):
        """Lista de (nombre, multiplicador) que se aplican a todos los ingresos pasivos."""
        f = self.fx()
        out = [("Logros", self.achievement_mult()), ("Prestigio", self.prestige_mult())]
        if self.vip("whale"):
            out.append(("VIP Ballena", 2.0))
        if f["passive"] != 1:
            out.append(("Mejoras únicas", f["passive"]))
        if f["per_game"]:
            out.append(("Sinergia de casino", 1 + f["per_game"] * len(self.games_unlocked)))
        if f["per_10b"]:
            out.append(("Marca registrada", 1 + f["per_10b"] * (self.total_buildings() // 10)))
        if f["per_unique"]:
            out.append(("Magnate", 1 + f["per_unique"] * len(self.uniques)))
        if self.vip("angel"):
            out.append(("VIP Inversor ángel", 1 + 0.25 * self.vip("angel")))
        return out

    def passive_mult(self):
        m = 1.0
        for _, k in self.passive_breakdown():
            m *= k
        return m

    def building_income(self, bid):
        """Ingresos/s totales de un tipo de negocio (con multiplicadores)."""
        return self.building_unit_income(bid) * self.buildings.get(bid, 0) * self.passive_mult()

    def income_per_sec(self, raw=False):
        if self._cache_ips is None:
            base = sum(self.building_unit_income(b.id) * self.buildings.get(b.id, 0) for b in BUILDINGS)
            self._cache_ips = base * self.passive_mult()
        return self._cache_ips

    # --------------------------------------------------------------- click
    def combo_cap(self):
        return 25 + 25 * self.lvl("combo") + self.fx()["combo"]

    def click_breakdown(self):
        out = [("Logros", self.achievement_mult()), ("Prestigio", self.prestige_mult())]
        if self.vip("whale"):
            out.append(("VIP Ballena", 2.0))
        if self.fx()["click"] != 1:
            out.append(("Guantes (únicas)", self.fx()["click"]))
        if self.vip("silk"):
            out.append(("VIP Dedos de seda", 1 + self.vip("silk")))
        return out

    def click_base(self):
        v = 0.01 * (1 + self.lvl("click_power"))
        for _, k in self.click_breakdown():
            v *= k
        return v

    def click_value(self, combo=None, manual=True):
        combo = self.combo if combo is None else combo
        v = self.click_base() * (1 + 0.01 * combo)
        if manual:
            v += self.income_per_sec() * 0.01 * self.lvl("synergy")
        return v * self.buff_mult("click_x2")

    def autoclick_value(self):
        return self.click_base() * self.buff_mult("click_x2")

    def crit_chance(self):
        return min(0.5, 0.02 * self.lvl("crit_chance") + self.fx()["crit"])

    def crit_mult(self):
        return (5 + 2 * self.lvl("crit_mult")) * self.fx()["crit_mult"]

    def do_click(self):
        """Clic manual. Devuelve (ganancia, es_crítico)."""
        now = time.time()
        if now - self.last_click < 0.6:
            self.combo = min(self.combo_cap(), self.combo + 1)
        else:
            self.combo = max(0, self.combo // 2)
        self.last_click = now
        self.stats["best_combo"] = max(self.stats["best_combo"], self.combo)
        v = self.click_value()
        crit = random.random() < self.crit_chance()
        if crit:
            v *= self.crit_mult()
            self.stats["crits"] += 1
        self.stats["clicks"] += 1
        self.earn(v, "click")
        return v, crit

    def auto_income_per_sec(self):
        return self.autoclicks_per_sec() * self.autoclick_value()

    def total_passive(self):
        """Todo lo que entra sin hacer nada: negocios + auto-clics."""
        return self.income_per_sec() + self.auto_income_per_sec()

    def autoclicks_per_sec(self):
        return self.lvl("autoclick") + 5 * self.vip("butler") + self.fx()["auto"]

    def decay_combo(self):
        if self.combo and time.time() - self.last_click > 1.2:
            self.combo = max(0, self.combo - 2)

    # ------------------------------------------------------------ upgrades
    def upgrade_cost(self, uid):
        u = UPGRADE_BY_ID[uid]
        return u.cost(self.lvl(uid))

    def plays_for(self, u):
        if u.game:
            return self.game_stats.get(u.game, {}).get("played", 0)
        return self.stats["bets"]

    def upgrade_lock(self, uid):
        """Motivo por el que no se puede comprar el siguiente nivel todavía (o None)."""
        u = UPGRADE_BY_ID[uid]
        if u.plays:
            lvl = self.lvl(uid)
            if lvl < len(u.plays):
                need = u.plays[lvl]
                have = self.plays_for(u)
                if have < need:
                    return f"{have}/{need} jugadas"
        return None

    def upgrade_visible(self, uid):
        u = UPGRADE_BY_ID[uid]
        if u.feat or self.lvl(uid) >= u.max_level:
            return False
        return u.requires is None or u.requires(self)

    def can_buy_upgrade(self, uid):
        u = UPGRADE_BY_ID[uid]
        return (not u.feat and self.lvl(uid) < u.max_level and self.upgrade_lock(uid) is None
                and self.money >= self.upgrade_cost(uid))

    def buy_upgrade(self, uid):
        u = UPGRADE_BY_ID[uid]
        if u.feat or self.lvl(uid) >= u.max_level or self.upgrade_lock(uid):
            return False
        if not self.spend(self.upgrade_cost(uid)):
            return False
        self.upgrades[uid] = self.lvl(uid) + 1
        self.invalidate()
        return True

    # ------------------------------------------------------------- hazañas
    def check_feats(self):
        """Concede las mejoras de las hazañas conseguidas. Devuelve las hazañas nuevas."""
        new = []
        for f in FEATS:
            if self.flags.get(f.id):
                u = UPGRADE_BY_ID[f.reward]
                if self.lvl(u.id) < u.max_level:
                    self.upgrades[u.id] = u.max_level
                    if not self.flags.get("_feat_seen_" + f.id):
                        self.flags["_feat_seen_" + f.id] = True
                        new.append(f)
        if new:
            self.invalidate()
        return new

    def count(self, key, value=None, add=None):
        """Contadores persistentes para las hazañas."""
        if value is not None:
            self.counters[key] = value
        elif add is not None:
            self.counters[key] = self.counters.get(key, 0) + add
        return self.counters.get(key, 0)

    # -------------------------------------------------------------- casino
    def max_bet(self):
        return float("inf")

    def unlock_game(self, gid):
        g = GAME_BY_ID[gid]
        if gid in self.games_unlocked or not self.spend(g.unlock_cost):
            return False
        self.games_unlocked.add(gid)
        if g.variants:
            self.variants.add(f"{gid}:{g.variants[0].id}")
        self.invalidate()
        return True

    # ------------------------------------------------------------ variantes
    def has_variant(self, gid, vid):
        return f"{gid}:{vid}" in self.variants

    def variant_cost(self, gid, vid):
        g = GAME_BY_ID[gid]
        v = next(v for v in g.variants if v.id == vid)
        return g.unlock_cost * v.cost_mult

    def unlock_variant(self, gid, vid):
        if self.has_variant(gid, vid) or gid not in self.games_unlocked:
            return False
        if not self.spend(self.variant_cost(gid, vid)):
            return False
        self.variants.add(f"{gid}:{vid}")
        return True

    def game_rtp(self, gid, variant=None):
        g = GAME_BY_ID[gid]
        if variant and g.variants:
            for v in g.variants:
                if v.id == variant:
                    return v.rtp if v.rtp is not None else g.rtp
        return g.rtp

    # --------------------------------------------------------- premio extra
    def profit_bonus(self, gid):
        return 0.01 * self.lvl("luck") + 0.02 * self.lvl(f"mastery_{gid}") + 0.01 * self.vip("tiger")

    def payout_mult(self, gid, variant=None):
        """Multiplicador que se aplica a los premios. Nunca deja que el retorno supere RTP_CAP."""
        base = self.game_rtp(gid, variant)
        if base is None:
            return 1.0
        return max(1.0, min(1.0 + self.profit_bonus(gid), RTP_CAP / base))

    def effective_rtp(self, gid, variant=None):
        base = self.game_rtp(gid, variant)
        if base is None:
            return None
        return base * self.payout_mult(gid, variant)

    # ----------------------------------------------------------- ventajas
    def hint_cooldown(self, key):
        if key in SPECIAL_COOLDOWNS:
            return SPECIAL_COOLDOWNS[key]
        k = min(1.0, self.player_level() / 40)
        return HINT_COOLDOWN_MAX - (HINT_COOLDOWN_MAX - HINT_COOLDOWN_MIN) * k

    def hint_owned(self, key):
        if key in SPECIAL_COOLDOWNS:
            if key in data.FEAT_SPECIALS:
                return self.lvl(key) > 0
            return self.has_special(key)
        return self.lvl(f"hint_{key}") > 0

    def hint_ready(self, key):
        return self.hint_owned(key) and time.time() >= self.hint_at.get(key, 0)

    def hint_remaining(self, key):
        return max(0.0, self.hint_at.get(key, 0) - time.time())

    def consume_hint(self, key):
        self.hint_at[key] = time.time() + self.hint_cooldown(key)
        self.stats["hints_used"] = self.stats.get("hints_used", 0) + 1

    def hint_reliability(self, gid, base):
        return 1.0 if self.hint_sure(gid) else base

    # -------------------------------------------------------------- trampas
    def cheat_active(self, gid):
        return self.cheat == gid

    def consume_cheat(self, gid):
        if self.cheat == gid:
            self.cheat = None
            return True
        return False

    # -------------------------------------------------------------- apuestas
    def can_bet(self, gid, amount):
        g = GAME_BY_ID[gid]
        if amount < g.min_bet - 1e-9:
            return False, f"La apuesta mínima es {g.min_bet:.2f} €"
        if amount > self.money + 1e-9:
            return False, "No tienes suficiente dinero"
        return True, ""

    def _gs(self, gid):
        return self.game_stats.setdefault(gid, {"played": 0, "won": 0, "wagered": 0.0, "returned": 0.0, "best": 0.0})

    def place_bet(self, gid, amount):
        ok, msg = self.can_bet(gid, amount)
        if not ok:
            self.log(msg, "#e74c3c", "error")
            return False
        self.spend(amount)
        self.stats["wagered"] += amount
        self._gs(gid)["wagered"] += amount
        if self.lvl("slots_jackpot"):
            self.jackpot += amount * 0.01
        return True

    def wager(self, gid, amount):
        """Apuesta adicional dentro de una misma mano (póker, doblar, dividir...)."""
        if amount > self.money + 1e-9:
            return False
        self.spend(amount)
        self.stats["wagered"] += amount
        self._gs(gid)["wagered"] += amount
        return True

    def settle(self, gid, bet, gross, count_streak=True, variant=None):
        """Liquida una apuesta. `gross` es lo que devolvería el juego sin bonus.
        Devuelve lo que realmente recibe el jugador."""
        gs = self._gs(gid)
        gs["played"] += 1
        self.stats["bets"] += 1
        self.add_xp(gid, bet, variant)
        payout = gross
        if gross > bet:
            payout = gross * self.payout_mult(gid, variant)
        elif gross < bet - 1e-9 and self.shield_armed and bet > 0:
            # escudo: devuelve lo perdido y se gasta
            payout = bet
            self.shield_armed = False
            self.shields = max(0, self.shields - 1)
            self.stats["shields_used"] = self.stats.get("shields_used", 0) + 1
            self.events.append(("shield", "¡El escudo te devuelve la apuesta!", (120, 200, 255)))
        self.hot_extra = 0.0
        h = self.hot
        if h and h["gid"] == gid and payout > bet and h["pot"] > 0:
            extra = min(h["pot"], (payout - bet) * (self.hot_mult() - 1))
            h["pot"] -= extra
            payout += extra
            self.hot_extra = extra
            self.stats["hot_earned"] = self.stats.get("hot_earned", 0.0) + extra
        if payout > 0:
            self.money += payout
            self.stats["max_money"] = max(self.stats["max_money"], self.money)
        gs["returned"] += payout
        net = payout - bet
        # las ganancias del casino cuentan en neto (lo perdido resta)
        self.stats["all_time_earned"] = max(0.0, self.stats["all_time_earned"] + net)
        self.stats["run_earned"] = max(0.0, self.stats["run_earned"] + net)
        if net > 0:
            self.stats["gamble_won"] += net
            self.stats["biggest_win"] = max(self.stats["biggest_win"], net)
            gs["best"] = max(gs["best"], net)
        else:
            self.stats["gamble_lost"] += -net
            self.stats["biggest_loss"] = max(self.stats["biggest_loss"], -net)
        if bet > 0 and gross > bet:
            self.stats["best_multiplier"] = max(self.stats["best_multiplier"], gross / bet)
        if count_streak:
            if gross > bet:
                gs["won"] += 1
                self.stats["bets_won"] += 1
                self.stats["streak"] = max(0, self.stats["streak"]) + 1
                self.stats["lose_streak"] = 0
                self.stats["best_streak"] = max(self.stats["best_streak"], self.stats["streak"])
            elif gross < bet:
                self.stats["bets_lost"] += 1
                self.stats["streak"] = 0
                self.stats["lose_streak"] += 1
                self.stats["worst_streak"] = max(self.stats["worst_streak"], self.stats["lose_streak"])
        if self.money < 0.01 and self.stats["max_money"] >= 1000:
            self.flags["broke"] = True
        return payout

    def set_flag(self, fid):
        self.flags[fid] = True

    # ------------------------------------------------------------ escudos
    def arm_shield(self):
        if self.shields > 0 and not self.shield_armed:
            self.shield_armed = True
            return True
        return False

    def grant_level_shields(self):
        """Un escudo de regalo al llegar a ciertos niveles. Devuelve cuántos se han dado."""
        lvl = self.player_level()
        given = 0
        for n in SHIELD_LEVELS:
            if lvl >= n > self.stats.get("shield_level_granted", 0):
                self.shields += 1
                self.stats["shield_level_granted"] = n
                given += 1
        return given

    # -------------------------------------------------------- oportunidades
    def opp_active(self):
        return self.opp is not None

    def opp_remaining(self):
        if not self.opp:
            return 0.0
        return max(0.0, self.opp["end"] - self.stats["play_time"])

    def _pick_unique(self, rarity):
        """Elige una mejora única de esa rareza. Las de negocios favorecen los que ya tienes."""
        pool, weights = [], []
        ips = self.income_per_sec()
        for u in UNIQUES:
            if u.rarity != rarity or not self.unique_available(u.id):
                continue
            w = 1.0
            bld = [e for e in u.effects if e[0] == "bld"]
            if bld:
                bid = bld[0][1]
                share = self.building_income(bid) / ips if ips > 0 else 0.0
                w = 0.15 + 3.0 * share if self.buildings.get(bid, 0) else 0.05
            pool.append(u.id)
            weights.append(w)
        return random.choices(pool, weights)[0] if pool else None

    def spawn_opportunity(self, rarity=None):
        weights = {r: OPP_RARITY[r][0] for r in RARITIES}
        weights["legendary"] *= 1 + self.stats.get("opps_since_leg", 0) / 400
        uid = None
        tries = 0
        if self.stats.get("opps_seen", 0) < 2:
            rarity = "common"
        while uid is None and tries < 8:
            r = rarity or random.choices(RARITIES, [weights[k] for k in RARITIES])[0]
            uid = self._pick_unique(r)
            rarity = None if uid is None else r
            tries += 1
        if uid is None:
            return False
        u = UNIQUE_BY_ID[uid]
        _, dur, secs, fort = OPP_RARITY[u.rarity]
        f = self.fx()
        dur += f["opp_dur"]
        ips = max(self.income_per_sec(), self.click_value(0) * 3)
        m = self.money
        # las dos primeras oportunidades de la partida son gangas, para aprender cómo funcionan
        bargain = (u.rarity == "common" and random.random() < OPP_BARGAIN) or self.stats.get("opps_seen", 0) < 2
        if bargain:
            price = max(ips * 60, m * 0.6)
        else:
            price = max(ips * secs, m * fort, (m + ips * dur) * 1.15)
        price *= 1 - f["opp_price"]
        price = max(price, 1.0)
        self.opp = {"uid": uid, "price": price, "end": self.stats["play_time"] + dur, "dur": dur, "bargain": bargain}
        self.stats["opps_seen"] = self.stats.get("opps_seen", 0) + 1
        if u.rarity == "legendary":
            self.stats["opps_since_leg"] = 0
        else:
            self.stats["opps_since_leg"] = self.stats.get("opps_since_leg", 0) + 1
        return True

    def schedule_opportunity(self):
        lo, hi = OPP_GAP
        self.opp_next = self.stats["play_time"] + random.uniform(lo, hi) / (1 + self.fx()["opp_freq"])

    def update_opportunity(self):
        """Llamar cada fotograma. Devuelve 'new', 'expired' o None."""
        pt = self.stats["play_time"]
        if self.opp:
            if pt >= self.opp["end"]:
                self.opp = None
                self.schedule_opportunity()
                return "expired"
            return None
        if not self.games_unlocked or self.stats["all_time_earned"] < 20:
            if self.opp_next < pt + 60:
                self.opp_next = pt + 60
            return None
        if pt >= self.opp_next:
            if self.spawn_opportunity():
                return "new"
            self.schedule_opportunity()
        return None

    def buy_opportunity(self):
        if not self.opp or not self.spend(self.opp["price"]):
            return False
        uid = self.opp["uid"]
        self.uniques.add(uid)
        self.stats["uniques_bought"] = self.stats.get("uniques_bought", 0) + 1
        self.opp = None
        self.schedule_opportunity()
        self.invalidate()
        return uid

    # -------------------------------------------------------- mesa caliente
    def hot_mult(self):
        return HOT_MULT + self.fx()["hot_mult"]

    def hot_remaining(self):
        if not self.hot:
            return 0.0
        return max(0.0, self.hot["end"] - self.stats["play_time"])

    def hot_candidates(self):
        return [g for g in self.games_unlocked if g != "poker"]

    def start_hot(self, gid=None):
        cands = self.hot_candidates()
        if not cands:
            return False
        if gid is None:
            last = self.counters.get("hot_last")
            pool = [g for g in cands if g != last] or cands
            gid = random.choice(pool)
        income = self.income_per_sec() + self.autoclicks_per_sec() * self.autoclick_value()
        pot = max(income * HOT_POT_SECS, self.click_value(0) * 200) * self.fx()["hot_pot"]
        dur = HOT_DURATION + self.fx()["hot_dur"]
        self.hot = {"gid": gid, "end": self.stats["play_time"] + dur, "dur": dur, "pot": pot, "pot0": pot}
        self.counters["hot_last"] = gid
        self.stats["hot_tables"] = self.stats.get("hot_tables", 0) + 1
        return True

    def update_hot(self):
        """Llamar cada fotograma. Devuelve 'new', 'end', 'empty' o None."""
        pt = self.stats["play_time"]
        if self.hot:
            if self.hot["pot"] <= 1e-9:
                self.hot = None
                self.hot_next = pt + random.uniform(*HOT_GAP)
                return "empty"
            if pt >= self.hot["end"]:
                self.hot = None
                self.hot_next = pt + random.uniform(*HOT_GAP)
                return "end"
            return None
        if pt >= self.hot_next:
            if self.start_hot():
                return "new"
            self.hot_next = pt + 60
        return None

    # -------------------------------------------------------- mercado negro
    def bm_unlocked(self):
        return self.vip("alley") > 0

    def bm_ready(self):
        return self.bm_unlocked() and self.stats["play_time"] >= self.bm_next

    def bm_remaining(self):
        return max(0.0, self.bm_next - self.stats["play_time"])

    def bm_make_offer(self):
        """Prepara el trato: 3 trampas posibles y 3 mejoras únicas que el mercader acepta a cambio."""
        cheats = [g for g in data.CHEATS if g in self.games_unlocked]
        sellable = [u for u in self.uniques if UNIQUE_BY_ID[u].rarity != "legendary"]
        if not cheats or not sellable:
            self.bm_offer = {"cheats": [], "price": []}
            return self.bm_offer
        random.shuffle(cheats)
        random.shuffle(sellable)
        self.bm_offer = {"cheats": cheats[:3], "price": sellable[:3]}
        return self.bm_offer

    def bm_deal(self, cheat_gid, unique_id):
        if not self.bm_ready() or unique_id not in self.uniques or cheat_gid not in data.CHEATS:
            return False
        self.uniques.discard(unique_id)
        self.cheat = cheat_gid
        self.bm_offer = None
        self.bm_next = self.stats["play_time"] + BLACK_MARKET_COOLDOWN * (1 - self.fx()["bm_cd"])
        self.stats["bm_deals"] = self.stats.get("bm_deals", 0) + 1
        self.invalidate()
        return True

    # ------------------------------------------------------------ prestige
    CHIP_BASE = 1e9
    CHIP_POW = 4

    @classmethod
    def chips_for(cls, earned):
        return int((earned / cls.CHIP_BASE) ** (1 / cls.CHIP_POW)) if earned > 0 else 0

    def claimable_chips(self):
        return max(0, self.chips_for(self.stats["all_time_earned"]) - self.prestige_level)

    def next_chip_at(self):
        n = self.chips_for(self.stats["all_time_earned"]) + 1
        return (n ** self.CHIP_POW) * self.CHIP_BASE

    def prestige(self):
        chips = self.claimable_chips()
        if chips <= 0:
            return False
        self.prestige_level += chips
        self.vip_chips += chips
        self.stats["prestiges"] += 1
        self.stats["run_earned"] = 0.0
        self.reset_run()
        return True

    def reset_run(self):
        lvl = self.vip("inheritance")
        self.money = float(INHERIT[lvl - 1]) if lvl else 0.0
        self.upgrades = {}
        self.buildings = {}
        if not self.vip("memory"):
            self.games_unlocked = set()
            self.variants = set()
        keep = {u for u in self.uniques if UNIQUE_BY_ID[u].rarity == "legendary"}
        rest = sorted((u for u in self.uniques if u not in keep), key=lambda u: -RARITY_RANK[UNIQUE_BY_ID[u].rarity])
        keep |= set(rest[:self.vip("collector")])
        self.uniques = keep
        self.opp = None
        self.opp_next = self.stats["play_time"] + 300
        self.hot = None
        self.hot_next = self.stats["play_time"] + 600
        self.jackpot = 0.0
        self.buffs = []
        self.combo = 0
        self.cheat = None
        self.invalidate()
        self.check_feats()

    def vip_cost(self, pid):
        p = VIP_BY_ID[pid]
        lvl = self.vip(pid)
        return p.costs[lvl] if lvl < p.max_level else None

    def buy_vip(self, pid):
        cost = self.vip_cost(pid)
        if cost is None or self.vip_chips < cost:
            return False
        self.vip_chips -= cost
        self.vip_perks[pid] = self.vip(pid) + 1
        self.invalidate()
        return True

    # ------------------------------------------------------------ temas
    def theme_unlocked(self, tid, attr="theme_coin"):
        lvl = data.THEME_LEVELS[attr].get(tid)
        return lvl is not None and self.player_level() >= lvl

    # --------------------------------------------------------- achievements
    def check_achievements(self):
        new = []
        for a in data.ACHIEVEMENTS:
            if a.id not in self.achievements:
                try:
                    if a.check(self):
                        self.achievements.add(a.id)
                        new.append(a)
                except Exception:
                    pass
        if new:
            self.invalidate()
        return new

    # -------------------------------------------------------- golden coin
    def golden_interval(self):
        """Segundos medios entre monedas doradas."""
        base = 120.0
        base /= 1 + 0.15 * self.lvl("gold_freq")
        base /= 1 + 0.2 * self.vip("golden_rain")
        base /= 1 + self.fx()["gold_freq"]
        return base

    def golden_reward_mult(self):
        return (1 + 0.2 * self.lvl("gold_dur")) * self.fx()["gold_reward"]

    # ------------------------------------------------------------ offline
    def offline_rate(self):
        return min(1.25, 0.5 + 0.1 * self.vip("offline") + self.fx()["offline"])

    def offline_cap(self):
        return (8 + 4 * self.vip("offline")) * 3600

    # --------------------------------------------------------------- save
    def to_dict(self):
        return {
            "version": SAVE_VERSION,
            "rev": self.rev,
            "money": self.money,
            "upgrades": self.upgrades,
            "buildings": self.buildings,
            "games_unlocked": sorted(self.games_unlocked),
            "achievements": sorted(self.achievements),
            "prestige_level": self.prestige_level,
            "vip_chips": self.vip_chips,
            "vip_perks": self.vip_perks,
            "jackpot": self.jackpot,
            "stats": self.stats,
            "game_stats": self.game_stats,
            "flags": self.flags,
            "counters": self.counters,
            "settings": self.settings,
            "variants": sorted(self.variants),
            "hint_at": self.hint_at,
            "uniques": sorted(self.uniques),
            "opp": self.opp,
            "opp_next": self.opp_next,
            "shields": self.shields,
            "shield_armed": self.shield_armed,
            "bm_next": self.bm_next,
            "cheat": self.cheat,
            "market": self.market,
            "theme_coin": self.theme_coin,
            "theme_felt": self.theme_felt,
            "hot": self.hot,
            "hot_next": self.hot_next,
            "last_time": time.time(),
        }

    def from_dict(self, d):
        self.money = float(d.get("money", 0))
        self.rev = int(d.get("rev", 0))
        self.upgrades = {k: int(v) for k, v in d.get("upgrades", {}).items() if k in UPGRADE_BY_ID}
        self.buildings = {k: int(v) for k, v in d.get("buildings", {}).items() if k in BUILDING_BY_ID}
        self.games_unlocked = {g for g in d.get("games_unlocked", []) if g in GAME_BY_ID}
        self.achievements = {a for a in d.get("achievements", []) if a in data.ACHIEVEMENT_BY_ID}
        self.prestige_level = int(d.get("prestige_level", 0))
        self.vip_chips = int(d.get("vip_chips", 0))
        self.vip_perks = {k: int(v) for k, v in d.get("vip_perks", {}).items() if k in VIP_BY_ID}
        self.jackpot = float(d.get("jackpot", 0))
        stats = _default_stats()
        stats.update(d.get("stats", {}))
        self.stats = stats
        self.game_stats = d.get("game_stats", {})
        self.flags = d.get("flags", {})
        self.counters = d.get("counters", {})
        self.settings.update(d.get("settings", {}))
        self.variants = set(d.get("variants", []))
        self.hint_at = {k: float(v) for k, v in d.get("hint_at", {}).items()}
        raw_uniques = set(d.get("uniques", []))
        self.uniques = {u for u in raw_uniques if u in UNIQUE_BY_ID}
        opp = d.get("opp")
        self.opp = opp if opp and opp.get("uid") in UNIQUE_BY_ID else None
        self.opp_next = float(d.get("opp_next", self.stats["play_time"] + 300))
        self.shields = int(d.get("shields", 0))
        self.shield_armed = bool(d.get("shield_armed", False))
        self.bm_next = float(d.get("bm_next", 0))
        self.cheat = d.get("cheat") if d.get("cheat") in data.CHEATS else None
        self.market = d.get("market", {})
        self.theme_coin = d.get("theme_coin", "cobre")
        self.theme_felt = d.get("theme_felt", "clasico")
        # el antiguo Periódico financiero ahora es un hito; sus mejoras pasan a ser las nuevas
        old = {"newspaper": None, "news_source": "news_inside", "news_wire": "news_inside_2"}
        if any(u in raw_uniques for u in old):
            self.flags["market_x2"] = True
            for u, new in old.items():
                if u in raw_uniques and new:
                    self.uniques.add(new)
            if "news_inside_2" in self.uniques:
                self.uniques.add("news_inside")
        # la moneda clásica y el tapete de cobre ya no existen
        if self.theme_coin not in data.THEME_LEVELS["theme_coin"]:
            self.theme_coin = "cobre"
        if self.theme_felt not in data.THEME_LEVELS["theme_felt"]:
            self.theme_felt = "clasico"
        hot = d.get("hot")
        self.hot = hot if hot and hot.get("gid") in GAME_BY_ID else None
        self.hot_next = float(d.get("hot_next", self.stats["play_time"] + 600))
        for gid in self.games_unlocked:
            g = GAME_BY_ID[gid]
            if g.variants:
                self.variants.add(f"{gid}:{g.variants[0].id}")
        self.last_time = float(d.get("last_time", time.time()))
        self.invalidate()
        self.check_feats()

    def save(self, path):
        if ENCODE_SAVES:
            raw = SAVE_MAGIC + base64.b85encode(zlib.compress(json.dumps(self.to_dict()).encode("utf-8"), 9))
        else:
            raw = json.dumps(self.to_dict(), indent=1).encode("utf-8")
        tmp = path + ".tmp"
        with open(tmp, "wb") as f:
            f.write(raw)
        if os.path.exists(path):
            try:
                os.replace(path, path + ".bak")  # la partida anterior queda de copia por si esta se estropea
            except OSError:
                pass
        os.replace(tmp, path)

    @staticmethod
    def read_save(path):
        """Lee una partida, codificada (ejecutable) o en JSON normal (versiones anteriores, o jugando desde el código)."""
        with open(path, "rb") as f:
            raw = f.read()
        if raw.startswith(SAVE_MAGIC):
            raw = zlib.decompress(base64.b85decode(raw[len(SAVE_MAGIC):].strip()))
        d = json.loads(raw.decode("utf-8"))
        if not isinstance(d, dict):
            raise ValueError("partida no válida")
        return d

    @classmethod
    def load(cls, path):
        s = cls()
        if os.path.exists(path) or os.path.exists(path + ".bak"):
            try:
                try:
                    d = cls.read_save(path)
                except Exception:
                    # partida estropeada: se usa la copia de la anterior
                    d = cls.read_save(path + ".bak")
                    try:
                        os.replace(path, path + ".corrupt")
                    except OSError:
                        pass
                if int(d.get("version", 1)) < SAVE_VERSION:
                    # partida de una versión anterior: se guarda aparte y se empieza de cero
                    old = path.replace(".json", f"_v{int(d.get('version', 1)) + 2}.json")
                    try:
                        os.replace(path, old)
                    except OSError:
                        pass
                    s.settings.update(d.get("settings", {}))
                    s.flags["_migrated"] = True
                    return s
                s.from_dict(d)
            except Exception:
                # partida corrupta: se guarda una copia y se empieza de cero
                try:
                    os.replace(path, path + ".corrupt")
                except OSError:
                    pass
                s = cls()
        return s
