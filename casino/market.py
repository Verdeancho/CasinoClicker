"""La bolsa del casino: activos con velas japonesas, fases de mercado, estacionalidad y caídas repentinas.

El precio sigue un paseo aleatorio con:
  - fases (alcista, bajista, lateral) que cambian sin avisar,
  - una onda estacional (periodo y fase cambian con cada fase de mercado): a veces se intuye, a veces engaña,
  - desplomes repentinos (más probables tras subidas largas) y algún subidón,
  - una atracción muy lenta hacia un valor de referencia, para que nada suba o baje para siempre,
  - una diferencia entre precio de compra y de venta (la casa siempre gana un poco),
  - noticias (desde el hito «Periódico financiero»), de una en una:
      * verdaderas: el valor sigue una tendencia muy marcada durante toda la noticia (10, 15 o 20 minutos),
      * falsas: se mueven un poco los primeros 2-3 minutos y luego vuelven a donde estaban,
      * ruido: no mueven nada.
    Lo que se puede ganar con una noticia verdadera tiene un tope oculto (unas horas de tus ingresos): si tienes
    mucho dinero dentro, el valor deja de subir antes.
"""
import math
import random

TICK = 0.5            # segundos por paso de precio
CANDLE = 10           # pasos por vela (5 s)
MAX_CANDLES = 72
SPREAD = 0.012        # diferencia compra/venta (1,2%)

ASSETS = [
    # símbolo, nombre, nivel, precio inicial, volatilidad por paso
    ("ORO", "Oro", 3, 180.0, 0.0028),
    ("PTR", "Petróleo", 3, 80.0, 0.0045),
    ("NAV", "Naviera Atlántica", 3, 24.0, 0.0060),
    ("AGR", "Agricultura", 6, 45.0, 0.0035),
    ("AUT", "Automoción", 8, 70.0, 0.0050),
    ("SEMI", "Semiconductores", 10, 60.0, 0.0072),
    ("BAN", "Banca", 12, 30.0, 0.0040),
    ("FAR", "Farmacéutica", 18, 120.0, 0.0055),
    ("TUR", "Turismo y Casinos", 20, 40.0, 0.0050),
    ("VRD", "Energías renovables", 25, 35.0, 0.0080),
    ("BTC", "Cripto", 30, 900.0, 0.0115),
    ("VID", "Videojuegos", 40, 55.0, 0.0085),
]
ASSET_BY_SYM = {a[0]: a for a in ASSETS}
REGIMES = {"bull": 0.07, "bear": -0.07, "side": 0.0}   # deriva en volatilidades por paso
REVERT = math.log(2) / (2 * 3600 / TICK)              # vuelta al valor de referencia: media vida de 2 horas

# ---- noticias
NEWS_DURATIONS = (600, 900, 1200)        # cuánto dura una noticia
NEWS_GAP = (180, 900)                    # tiempo sin noticias entre una y la siguiente (nunca más de 25 min)
NEWS_FIRST = (45, 120)                   # la primera tras abrir el juego
NEWS_SIZES = {"N": (1.10, 1.30), "I": (1.8, 2.3), "B": (4.0, 5.5), "S": (1.05, 1.12)}
SMALLER = {"B": "I", "I": "N", "N": "S"}  # los valores secundarios se mueven un tamaño menos
NEWS_POT_H = {"N": 0.5, "I": 1.0, "B": 2.0}   # tope oculto de lo que se gana con una noticia (horas de ingresos)
NEWS_REL = 0.65                          # fiabilidad (oculta) con el Periódico financiero
NEWS_REL_PRO = 0.75                      # con Fuentes contrastadas
NEWS_DAMP = 0.45                         # el ruido se calma mientras manda la noticia: la tendencia se ve clara
NEWS_SHAPE = 1.6                         # la tendencia arranca fuerte y se va suavizando (premia entrar pronto)
FAKE_BUMP = (120, 180)                   # una noticia falsa mueve el valor unos 2-3 minutos...
FAKE_BACK = 180                          # ...y luego vuelve en 3 minutos a donde estaba
NEWS_STREAK = 3                          # aciertos seguidos para «Fuentes contrastadas»


def news_curve(u):
    """Fracción del movimiento total de la noticia hecha en la fracción u de su duración."""
    u = min(1.0, max(0.0, u))
    return 1.0 - (1.0 - u) ** NEWS_SHAPE


class Asset:
    def __init__(self, sym, rng, d=None):
        _, self.name, self.level, p0, self.vol = ASSET_BY_SYM[sym]
        self.sym = sym
        self.rng = rng
        self.anchor = math.log(p0)
        d = d or {}
        self.x = d.get("x", self.anchor)
        self.t = d.get("t", 0.0)
        self.regime = d.get("regime", "side")
        self.reg_left = d.get("reg_left", 0.0)
        self.season = d.get("season", (0.0, 30.0, 0.0))
        self.season = tuple(self.season)
        self.crash = d.get("crash", 0)                # pasos de desplome que quedan
        self.split = 1.0
        self.crash_rate = d.get("crash_rate", 0.0)
        self.bull_run = d.get("bull_run", 0.0)
        self.news = d.get("news")                     # efecto de la noticia activa sobre este valor
        self.candles = [tuple(c) for c in d.get("candles", [])]   # (abre, máx, mín, cierra)
        self.cur = d.get("cur")
        self.n_in = d.get("n_in", 0)
        self.price0 = self.price()

    def to_dict(self):
        """Todo el estado: al volver a abrir el juego la bolsa está exactamente como la dejaste."""
        r6 = lambda v: float(f"{v:.6g}")
        return {"x": self.x, "t": self.t, "regime": self.regime, "reg_left": self.reg_left, "season": self.season,
                "crash": self.crash, "crash_rate": self.crash_rate, "bull_run": self.bull_run, "news": self.news,
                "candles": [[r6(v) for v in c] for c in self.candles], "cur": self.cur, "n_in": self.n_in}

    def build_history(self):
        """Partidas antiguas sin velas guardadas: se dibuja un histórico que acaba justo en el precio guardado."""
        keep = (self.x, self.t, self.regime, self.reg_left, self.season)
        for _ in range(CANDLE * MAX_CANDLES):
            self.step()
        k = math.exp(keep[0] - self.x)
        self.candles = [tuple(v * k for v in c) for c in self.candles]
        self.cur = [v * k for v in self.cur] if self.cur else None
        self.x, self.t, self.regime, self.reg_left, self.season = keep
        self.crash, self.crash_rate, self.bull_run, self.news = 0, 0.0, 0.0, None

    def price(self):
        return math.exp(self.x)

    def bid(self):
        return self.price() * (1 - SPREAD / 2)

    def ask(self):
        return self.price() * (1 + SPREAD / 2)

    def new_regime(self):
        r = self.rng
        self.regime = r.choices(["bull", "bear", "side"], [0.35, 0.35, 0.30])[0]
        self.reg_left = r.expovariate(1 / 30.0)
        amp = self.vol * r.uniform(0.8, 3.0)
        self.season = (amp, r.uniform(16, 50), r.uniform(0, math.tau))

    def set_news(self, direction, size, real, dur):
        """Empieza el efecto de una noticia sobre este valor."""
        target = math.log(self.rng.uniform(*NEWS_SIZES[size]))
        bump = self.rng.uniform(*FAKE_BUMP)
        self.news = {"dir": direction, "target": target, "t0": self.t, "dur": dur, "real": real, "bump": bump,
                     "bump_move": target * news_curve(bump / dur), "cap": None}

    def news_phase(self):
        """'trend' (verdadera, o falsa al principio), 'back' (falsa volviendo) o None."""
        n = self.news
        if not n:
            return None
        e = self.t - n["t0"]
        if n["real"]:
            return "trend" if e < n["dur"] else None
        if e < n["bump"]:
            return "trend"
        return "back" if e < n["bump"] + FAKE_BACK else None

    def step(self):
        r = self.rng
        self.t += TICK
        self.reg_left -= TICK
        if self.reg_left <= 0:
            self.new_regime()
        n = self.news
        phase = self.news_phase()
        calm = phase == "trend"
        v = self.vol * (NEWS_DAMP if calm else 1.0)
        amp, per, ph = self.season
        season = 0.0 if calm else amp * (math.sin(math.tau * self.t / per + ph) -
                                         math.sin(math.tau * (self.t - TICK) / per + ph))
        # paseo aleatorio "justo" (martingala) menos una pequeña ventaja de la casa
        drift = 0.0 if calm else REGIMES[self.regime] * v
        dx = drift + r.gauss(0, v) - 0.5 * v * v - 0.002 * v + season - REVERT * (self.x - self.anchor)
        if phase == "trend":
            e = self.t - n["t0"]
            dx += n["dir"] * n["target"] * (news_curve(e / n["dur"]) - news_curve((e - TICK) / n["dur"]))
            if n["real"] and n["cap"] is not None:
                # tope oculto: con mucho dinero dentro, el valor deja de moverse a tu favor
                if n["dir"] > 0:
                    dx = min(dx, n["cap"] - self.x)
                else:
                    dx = max(dx, n["cap"] - self.x)
        elif phase == "back":
            dx -= n["dir"] * n["bump_move"] / (FAKE_BACK / TICK)
        if self.regime == "bull":
            self.bull_run += TICK
        else:
            self.bull_run = max(0.0, self.bull_run - TICK * 2)
        if self.crash > 0:
            self.crash -= 1
            dx -= self.crash_rate
        elif not calm and r.random() < 0.00006 + 0.000001 * min(self.bull_run, 120):
            # desplome: entre un 15% y un 40% en unos segundos
            self.crash = r.randint(4, 10)
            self.crash_rate = -math.log(1 - r.uniform(0.15, 0.40)) / self.crash
            self.regime = "bear"
            self.reg_left = r.uniform(10, 30)
            self.bull_run = 0.0
        elif not calm and r.random() < 0.00008:
            dx += r.uniform(0.08, 0.20)          # subidón
        self.x += dx
        # contrasplits / splits para que el precio no se vaya a cero ni al infinito
        self.split = 1.0
        if self.x < self.anchor - math.log(8):
            self.split = 0.1
        elif self.x > self.anchor + math.log(8):
            self.split = 10.0
        if self.split != 1.0:
            k = math.log(1 / self.split)
            self.x += k
            if n and n["cap"] is not None:
                n["cap"] += k
            self.candles = [tuple(c / self.split for c in cd) for cd in self.candles]
            if self.cur:
                self.cur = [c / self.split for c in self.cur]
        p = self.price()
        if self.cur is None:
            self.cur = [p, p, p, p]
            self.n_in = 0
        self.cur[1] = max(self.cur[1], p)
        self.cur[2] = min(self.cur[2], p)
        self.cur[3] = p
        self.n_in += 1
        if self.n_in >= CANDLE:
            self.candles.append(tuple(self.cur))
            del self.candles[:-MAX_CANDLES]
            self.cur = None

    def change(self):
        """Variación desde la primera vela visible."""
        if not self.candles:
            return 0.0
        return self.price() / self.candles[0][0] - 1


class Market:
    def __init__(self, state, seed=None):
        self.state = state
        self.rng = random.Random(seed)
        d = state.market or {}
        self.assets = {}
        for sym, *_ in ASSETS:
            a = self.assets[sym] = Asset(sym, self.rng, d.get("assets", {}).get(sym))
            if not a.candles:
                a.build_history()
        self.pos = d.get("pos", {})      # sym -> {"qty", "cost", "sq", "sentry", "coll", "tag_l", "tag_s"}
        for sym in list(self.pos):
            if sym not in ASSET_BY_SYM:      # valores antiguos: se devuelve lo invertido
                p = self.pos.pop(sym)
                state.money += p.get("cost", 0.0) + p.get("coll", 0.0)
        self.selected = d.get("selected", "ORO")
        if self.selected not in ASSET_BY_SYM:
            self.selected = "ORO"
        self.clock = d.get("clock", 0.0)
        self.acc = d.get("acc", 0.0)
        self.active = d.get("active")                 # la noticia en curso
        self.unread = d.get("unread", False)          # hay una noticia que no has abierto en el buzón
        self.recent = d.get("recent", [])             # titulares recientes, para no repetir
        self.news_next = d.get("news_next", self.clock + self.rng.uniform(*NEWS_FIRST))
        self.counted = set(d.get("counted", []))      # noticias que ya has acertado (cuentan una vez)

    def save(self):
        self.state.market = {"assets": {s: a.to_dict() for s, a in self.assets.items()}, "pos": self.pos,
                             "selected": self.selected, "clock": self.clock, "acc": self.acc, "active": self.active,
                             "unread": self.unread, "recent": self.recent, "news_next": self.news_next,
                             "counted": sorted(self.counted)}

    # ------------------------------------------------------------- noticias
    def news_enabled(self):
        from .data import MARKET_LEVEL
        return bool(self.state.flags.get("market_x2")) and self.state.player_level() >= MARKET_LEVEL

    def news_pro(self):
        """Con «Fuentes contrastadas» ves a qué valores afecta cada noticia."""
        return bool(self.state.flags.get("news_pro"))

    def reliability(self):
        f = self.state.fx()
        if f["news_true"]:
            return 1.0
        return min(0.95, (NEWS_REL_PRO if self.news_pro() else NEWS_REL) + f["news_rel"])

    def news_remaining(self):
        a = self.active
        return max(0.0, a["t0"] + a["dur"] - self.clock) if a else 0.0

    def publish_news(self):
        from .news import NEWS
        avail = [sym for sym in NEWS if self.unlocked(sym)]
        if not avail:
            return
        sym = self.rng.choice(avail)
        options = [n for n in NEWS[sym] if n["title"] not in self.recent] or NEWS[sym]
        n = self.rng.choice(options)
        self.recent = (self.recent + [n["title"]])[-60:]
        real = self.rng.random() < self.reliability()
        dur = self.rng.choice(NEWS_DURATIONS)
        size = n["size"]
        pot = max(100.0, self.state.total_passive() * 3600 * NEWS_POT_H[size]) if size else 0.0
        p0 = {}
        for k, (target, direction) in enumerate(n["effects"].items()):
            a = self.assets[target]
            a.set_news(direction, size if k == 0 else SMALLER[size], real, dur)
            p0[target] = a.price()
        self.active = {"id": self.rng.getrandbits(40), "sym": sym, "title": n["title"], "body": n["body"],
                       "effects": dict(n["effects"]), "real": real, "t0": self.clock, "dur": dur, "pot": pot,
                       "realized": 0.0, "p0": p0}
        self.unread = True
        self.state.events.append(("news", n["title"], (150, 200, 255)))

    def end_news(self):
        a = self.active
        if a:
            for sym in a["effects"]:
                self.assets[sym].news = None
        self.active = None
        self.unread = False
        self.news_next = self.clock + self.rng.uniform(*NEWS_GAP)

    def _news_gain(self, sym, ref_long, ref_short):
        p = self.pos.get(sym)
        if not p:
            return 0.0
        price = self.assets[sym].price()
        return p["qty"] * max(0.0, price - ref_long) + p["sq"] * max(0.0, ref_short - price)

    def update_caps(self):
        """Tope oculto: lo que ganes con la noticia (realizado o no) no pasa del bote."""
        a = self.active
        if not a or not a["real"]:
            return
        refs = {}
        for sym in a["effects"]:
            p = self.pos.get(sym) or {}
            p0 = a["p0"][sym]
            rl = max(p0, p["cost"] / p["qty"]) if p.get("qty", 0) > 1e-12 else p0
            rs = min(p0, p["sentry"]) if p.get("sq", 0) > 1e-12 else p0
            refs[sym] = (rl, rs)
        gains = {sym: self._news_gain(sym, *refs[sym]) for sym in a["effects"]}
        left = a["pot"] - a["realized"]
        for sym, d in a["effects"].items():
            asset = self.assets[sym]
            if not asset.news:
                continue
            p = self.pos.get(sym) or {}
            room = max(0.0, left - sum(g for k, g in gains.items() if k != sym))
            cap = None
            if d > 0 and p.get("qty", 0) > 1e-12:
                cap = math.log(refs[sym][0] + room / p["qty"])
            elif d < 0 and p.get("sq", 0) > 1e-12:
                cap = math.log(max(refs[sym][1] * 0.02, refs[sym][1] - room / p["sq"]))
            asset.news["cap"] = cap

    def _tag(self, sym, direction):
        """Apunta que abriste esta posición durante la noticia (para la racha de aciertos)."""
        a = self.active
        if a and sym in a["effects"]:
            return [a["id"], a["effects"][sym] * direction]
        return None

    def _score(self, tag, profit):
        """Al cerrar una posición abierta durante una noticia: acierto si ibas a favor y ganas."""
        if not tag:
            return
        s = self.state
        nid, agree = tag
        if agree > 0 and profit > 0:
            if nid not in self.counted:
                self.counted.add(nid)
                s.flags["news_streak"] = s.flags.get("news_streak", 0) + 1
                if s.flags["news_streak"] >= NEWS_STREAK and not s.flags.get("news_pro"):
                    s.flags["news_pro"] = True
                    s.events.append(("milestone", "news_pro", (150, 200, 255)))
        else:
            s.flags["news_streak"] = 0

    # ---------------------------------------------------------------- tiempo
    def update(self, dt):
        self.clock += dt
        if self.news_enabled():
            if self.active and self.clock >= self.active["t0"] + self.active["dur"]:
                self.end_news()
            elif not self.active and self.clock >= self.news_next:
                self.publish_news()
        elif self.active:
            self.end_news()
        self.acc += dt
        while self.acc >= TICK:
            self.acc -= TICK
            self.update_caps()
            for sym, a in self.assets.items():
                a.step()
                if a.split != 1.0:
                    self.apply_split(sym, a.split)
            self.check_liquidations()

    def apply_split(self, sym, f):
        """f=10: cada acción vale 10 veces menos y tienes 10 veces más (y al revés)."""
        p = self.p(sym)
        p["qty"] *= f
        p["sq"] *= f
        p["sentry"] /= f
        a = self.active
        if a and sym in a["p0"]:
            a["p0"][sym] /= f
        word = "split" if f > 1 else "contrasplit"
        self.state.events.append(("log", f"Bolsa: {sym} hace un {word} ({'1x10' if f > 1 else '10x1'}).",
                                  (150, 200, 255)))

    def unlocked(self, sym):
        return self.state.player_level() >= ASSET_BY_SYM[sym][2]

    def p(self, sym):
        return self.pos.setdefault(sym, {"qty": 0.0, "cost": 0.0, "sq": 0.0, "sentry": 0.0, "coll": 0.0})

    def fee(self):
        return self.state.fx()["market_fee"]

    def bid(self, sym):
        a = self.assets[sym]
        return a.price() * (1 - SPREAD / 2 * self.fee())

    def ask(self, sym):
        a = self.assets[sym]
        return a.price() * (1 + SPREAD / 2 * self.fee())

    def _xp(self, notional):
        self.state.stats["xp"] = self.state.stats.get("xp", 0.0) + notional * SPREAD / 2 * self.fee()
        self.state.stats["trades"] = self.state.stats.get("trades", 0) + 1

    # ---------------------------------------------------------------- largo
    def buy(self, sym, qty):
        cost = qty * self.ask(sym)
        if qty <= 0 or not self.state.spend(cost):
            return False
        p = self.p(sym)
        p["qty"] += qty
        p["cost"] += cost
        tag = self._tag(sym, 1)
        if tag:
            p["tag_l"] = tag
        self.state.stats["wagered"] += cost
        self._xp(cost)
        return True

    def sell(self, sym, qty):
        p = self.p(sym)
        qty = min(qty, p["qty"])
        if qty <= 0:
            return None
        proceeds = qty * self.bid(sym)
        frac = qty / p["qty"]
        basis = p["cost"] * frac
        p["qty"] -= qty
        p["cost"] -= basis
        tag = p.get("tag_l")
        if p["qty"] < 1e-9:
            p["qty"] = p["cost"] = 0.0
            p.pop("tag_l", None)
        self.realize(sym, basis, proceeds)
        self._score(tag, proceeds - basis)
        return proceeds - basis

    # ---------------------------------------------------------------- corto
    def short(self, sym, qty):
        """Vende en corto: bloquea como garantía el valor de lo vendido."""
        price = self.bid(sym)
        coll = qty * price
        if qty <= 0 or not self.state.spend(coll):
            return False
        p = self.p(sym)
        tot = p["sq"] + qty
        p["sentry"] = (p["sentry"] * p["sq"] + price * qty) / tot
        p["sq"] = tot
        p["coll"] += coll
        tag = self._tag(sym, -1)
        if tag:
            p["tag_s"] = tag
        self.state.stats["wagered"] += coll
        self._xp(coll)
        return True

    def short_value(self, sym):
        p = self.p(sym)
        if p["sq"] <= 0:
            return 0.0
        return max(0.0, p["coll"] + p["sq"] * (p["sentry"] - self.ask(sym)))

    def cover(self, sym):
        p = self.p(sym)
        if p["sq"] <= 0:
            return None
        val = self.short_value(sym)
        basis = p["coll"]
        p["sq"] = p["sentry"] = p["coll"] = 0.0
        tag = p.pop("tag_s", None)
        self.realize(sym, basis, val)
        self._score(tag, val - basis)
        return val - basis

    def check_liquidations(self):
        for sym, p in self.pos.items():
            if p.get("sq", 0) > 0 and self.short_value(sym) <= p["coll"] * 0.02:
                self.cover(sym)
                self.state.events.append(("log", f"Bolsa: tu corto en {sym} se ha liquidado.", (254, 95, 85)))

    def realize(self, sym, basis, proceeds):
        s = self.state
        s.money += proceeds
        net = proceeds - basis
        s.stats["all_time_earned"] = max(0.0, s.stats["all_time_earned"] + net)
        s.stats["run_earned"] = max(0.0, s.stats["run_earned"] + net)
        if net > 0:
            s.stats["gamble_won"] += net
        else:
            s.stats["gamble_lost"] += -net
        a = self.active
        if a and a["real"] and sym in a["effects"] and net > 0:
            a["realized"] += net
        if basis > 0 and proceeds >= basis * 2 and not s.flags.get("market_x2"):
            s.flags["market_x2"] = True
            s.events.append(("milestone", "market_x2", (150, 200, 255)))

    def position_value(self, sym):
        p = self.p(sym)
        return p["qty"] * self.bid(sym) + self.short_value(sym)

    def total_value(self):
        return sum(self.position_value(s) for s in self.assets)
