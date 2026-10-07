"""Simulador de la economía de Casino Clicker.

Juega partidas aceleradas con varios perfiles de jugador usando el GameState real (sin pygame):
  espera      -> compra negocios y mejoras, no apuesta nunca
  loco        -> apuesta a lo grande sin parar e invierte poco
  estratega   -> invierte, guarda una reserva y apuesta con objetivo (oportunidades, ventajas)
  acaparador  -> guarda la mitad de su dinero y lo apuesta entero cada vez que tiene una ventaja

Uso:  python tools/sim_economia.py [horas] [semillas]
"""
import math
import os
import random
import statistics
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import casino.state as st          # noqa: E402
from casino import data             # noqa: E402
from casino.data import BUILDINGS, BUILDING_TIERS, GAMES, HINTS, UNIQUE_BY_ID, UPGRADE_BY_ID  # noqa: E402


class Clock:
    t = 1_000_000.0

    def time(self):
        return self.t


CLOCK = Clock()
st.time = CLOCK

DT = 2.0
CLICKS_PER_SEC = 1.0
HINT_P = float(os.environ.get('HINT_P', 0.68))
RESERVE = float(os.environ.get('RESERVE', 240))
NOHINTS = bool(os.environ.get('NOHINTS'))
NOOPP = bool(os.environ.get('NOOPP'))
NOHOT = bool(os.environ.get('NOHOT'))
MILESTONES = [1e1, 1e3, 1e5, 1e7, 1e9, 1e11, 1e13]


class Bot:
    def __init__(self, kind, seed):
        self.kind = kind
        self.rng = random.Random(seed)
        random.seed(seed * 7919 + hash(kind) % 1000)
        self.s = st.GameState()
        self.t = 0.0
        self.next_buy = 0.0
        self.next_gold = 120.0
        self.next_bet = 0.0
        self.feat_at = {}
        self.reached = {}
        self.uniq_log = []
        self.bets = 0
        self.hot_won = 0.0
        self.hot_seen = 0.0

    # ------------------------------------------------------------ apuestas
    def coin_bet(self, amount, p=0.5, mult=1.96):
        s = self.s
        amount = min(amount, s.money)
        if amount < 0.01:
            return False
        s.place_bet("coinflip", amount)
        win = random.random() < p
        s.settle("coinflip", amount, amount * mult if win else 0.0)
        self.bets += 1
        return win

    def wild_bet(self, amount):
        """Apuesta del jugador loco: juegos variados con retorno ~96%."""
        s = self.s
        amount = min(amount, s.money)
        if amount < 0.01:
            return
        p, m = random.choice([(0.5, 1.92), (0.25, 3.84), (0.1, 9.6), (0.02, 48.0)])
        s.place_bet("slots", amount)
        s.settle("slots", amount, amount * m if random.random() < p else 0.0)
        self.bets += 1

    def bold_play(self, target, budget):
        """Intenta llegar a `target` arriesgando como mucho `budget` (apuestas a cara o cruz)."""
        s = self.s
        floor = s.money - budget
        while s.money < target and s.money > floor + 0.01:
            need = (target - s.money) / 0.96 + 0.01
            stake = min(need, s.money - floor)
            self.coin_bet(stake)
        return s.money >= target

    # ------------------------------------------------------------- compras
    def reserve(self):
        ips = self.s.income_per_sec()
        if self.kind == "estratega":
            return ips * RESERVE
        if self.kind == "acaparador":
            return self.s.money * 0.5
        return 0.0

    def buy_greedy(self, budget):
        s = self.s
        rate = CLICKS_PER_SEC
        bought = 0
        for _ in range(400):
            pm = s.passive_mult()
            cands = []
            for b in BUILDINGS:
                n = s.buildings.get(b.id, 0)
                cost = s.building_cost(b.id)
                gain = s.building_unit_income(b.id) * pm
                cands.append((cost / gain, cost, ("b", b.id)))
                for i, (need, _) in enumerate(BUILDING_TIERS):
                    uid = f"b_{b.id}_{i}"
                    if not s.lvl(uid) and n >= need:
                        c = s.upgrade_cost(uid)
                        g = s.building_income(b.id)
                        if g > 0:
                            cands.append((c / g, c, ("u", uid)))
                        break
            cv = s.click_value(10)
            u = UPGRADE_BY_ID["click_power"]
            if s.lvl("click_power") < u.max_level:
                c = s.upgrade_cost("click_power")
                g = rate * cv / (1 + s.lvl("click_power"))
                cands.append((c / g, c, ("u", "click_power")))
            if s.lvl("autoclick") < 30:
                c = s.upgrade_cost("autoclick")
                cands.append((c / max(1e-9, s.autoclick_value()), c, ("u", "autoclick")))
            if s.lvl("synergy") < 10 and s.income_per_sec() > 0:
                c = s.upgrade_cost("synergy")
                cands.append((c / max(1e-12, 0.01 * s.income_per_sec() * rate), c, ("u", "synergy")))
            cands.sort()
            best = cands[0][0]
            pick = None
            for roi, cost, act in cands:
                if roi > best * 1.3:
                    break
                if cost <= budget:
                    pick = (cost, act)
                    break
            if not pick:
                break
            cost, (k, x) = pick
            ok = s.buy_building(x) if k == "b" else s.buy_upgrade(x)
            if not ok:
                break
            budget -= cost
            bought += 1
        for g in GAMES:
            if g.id not in s.games_unlocked and g.unlock_cost <= s.money * 0.02:
                s.unlock_game(g.id)
                if self.kind != "espera" and g.id in HINTS and not NOHINTS:
                    mean = 60 if self.kind == "loco" else 90
                    self.feat_at[g.id] = self.t + self.rng.expovariate(1 / (mean * 60))
        return bought

    # ------------------------------------------------------------- ventajas
    def play_hot(self):
        """Mesa caliente: el estratega y el acaparador apuestan para vaciar el bote (unas 60 tiradas en 2 min)."""
        s = self.s
        if not s.hot:
            return
        if self.kind not in ("estratega", "acaparador"):
            s.hot["end"] = 0.0
            s.update_hot()
            return
        s.hot["gid"] = "coinflip"
        m = s.hot_mult()
        frac = 0.25 if self.kind == "estratega" else 0.5
        for _ in range(60):
            if not s.hot or s.hot["pot"] <= 0 or s.money < 0.01:
                break
            stake = min(s.money * frac, s.hot["pot"] / (0.96 * (m - 1)) + 0.01)
            self.coin_bet(stake)
        self.hot_won += s.stats.get("hot_earned", 0.0) - self.hot_seen
        self.hot_seen = s.stats.get("hot_earned", 0.0)
        if s.hot:
            s.hot["end"] = 0.0
        s.update_hot()           # cierra la mesa y programa la siguiente

    def use_hints(self):
        s = self.s
        for gid, at in list(self.feat_at.items()):
            if self.t >= at:
                s.upgrades[f"hint_{gid}"] = 1
                del self.feat_at[gid]
        if self.kind not in ("estratega", "acaparador"):
            return
        for gid in HINTS:
            if s.hint_ready(gid):
                s.consume_hint(gid)
                p = 1.0 if s.hint_sure(gid) else HINT_P
                frac = 1.0 if (self.kind == "acaparador" or p >= 1) else 0.45
                self.coin_bet(s.money * frac, p=p)

    # -------------------------------------------------------- oportunidades
    def handle_opp(self, ev):
        s = self.s
        if not s.opp:
            return
        price = s.opp["price"]
        uid = s.opp["uid"]
        rar = UNIQUE_BY_ID[uid].rarity
        if s.money >= price:
            s.buy_opportunity()
            self.uniq_log.append((self.t, uid))
            return
        if ev != "new":
            return
        if self.kind in ("estratega", "acaparador"):
            budget = s.money * {"common": 0.6, "rare": 0.8, "epic": 0.9, "legendary": 1.0}[rar]
            if self.bold_play(price, budget):
                s.buy_opportunity()
                self.uniq_log.append((self.t, uid))

    # ----------------------------------------------------------------- paso
    def step(self):
        s = self.s
        self.t += DT
        CLOCK.t += DT
        s.stats["play_time"] += DT
        ips = s.income_per_sec()
        s.earn(ips * DT, "passive")
        s.earn((CLICKS_PER_SEC * s.click_value(10) + s.autoclicks_per_sec() * s.autoclick_value()) * DT, "click")
        if self.t >= self.next_gold:
            self.next_gold = self.t + random.uniform(0.6, 1.4) * s.golden_interval()
            amount = max(s.click_value(0) * 30, min(ips * 30, s.money * 0.03)) * s.golden_reward_mult()
            s.earn(amount * 0.7, "golden")
        if not NOHOT and s.update_hot() == "new":
            self.play_hot()
        if not NOOPP:
            ev = s.update_opportunity()
            self.handle_opp(ev)
        self.use_hints()
        if self.kind == "loco" and self.t >= self.next_bet:
            self.next_bet = self.t + 10
            self.wild_bet(s.money * 0.4)
        if self.t >= self.next_buy:
            self.next_buy = self.t + 10
            if self.kind == "loco":
                if self.rng.random() < 0.08:
                    self.buy_greedy(s.money)
            else:
                self.buy_greedy(max(0.0, s.money - self.reserve()))
        for m in MILESTONES:
            if m not in self.reached and s.income_per_sec() >= m:
                self.reached[m] = self.t


def run(kind, hours, seed):
    b = Bot(kind, seed)
    steps = int(hours * 3600 / DT)
    for _ in range(steps):
        b.step()
    s = b.s
    leg = sum(1 for _, u in b.uniq_log if UNIQUE_BY_ID[u].rarity == "legendary")
    return {"reached": b.reached, "ips": s.income_per_sec(), "uniq": len(s.uniques), "leg": leg,
            "level": s.player_level(), "bets": b.bets, "chips": s.chips_for(s.stats["all_time_earned"]),
            "bld": s.total_buildings()}


def fmt_h(t):
    return "   -  " if t is None else f"{t / 3600:6.1f}"


def main():
    hours = float(sys.argv[1]) if len(sys.argv) > 1 else 40
    seeds = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    kinds = sys.argv[3].split(",") if len(sys.argv) > 3 else ["espera", "loco", "estratega", "acaparador"]
    res = {k: [run(k, hours, sd) for sd in range(seeds)] for k in kinds}
    print(f"Horas: {hours}, semillas: {seeds}")
    print("Horas (mediana) hasta alcanzar X €/s de ingresos pasivos:")
    print("perfil       " + "".join(f"{m:>8.0e}" for m in MILESTONES) + "   nivel  únicas  leg  fichas  negocios")
    base_t = {}
    for k in kinds:
        row = []
        for m in MILESTONES:
            ts = [r["reached"].get(m) for r in res[k]]
            ok = [t for t in ts if t is not None]
            med = statistics.median(ok) if len(ok) >= (len(ts) + 1) // 2 else None
            row.append(med)
            if k == "espera":
                base_t[m] = med
        lv = statistics.median(r["level"] for r in res[k])
        un = statistics.median(r["uniq"] for r in res[k])
        lg = sum(r["leg"] for r in res[k]) / len(res[k])
        ch = statistics.median(r["chips"] for r in res[k])
        bl = statistics.median(r["bld"] for r in res[k])
        print(f"{k:12s} " + "".join(f"{fmt_h(t):>8s}" for t in row) + f"   {lv:5.0f}  {un:6.0f}  {lg:3.1f}  {ch:6.0f}  {bl:8.0f}")
    print("\nVelocidad relativa al que espera (tiempo del que espera / tiempo del perfil):")
    for k in kinds:
        out = []
        for m in MILESTONES:
            ts = [r["reached"].get(m) for r in res[k]]
            ok = [t for t in ts if t is not None]
            if base_t.get(m) and len(ok) >= (len(ts) + 1) // 2:
                out.append(f"{base_t[m] / statistics.median(ok):8.2f}")
            else:
                out.append("     -  ")
        print(f"{k:12s} " + "".join(out))
    print("\nIngresos finales (mediana): " + ", ".join(
        f"{k}={statistics.median(r['ips'] for r in res[k]):.3g}" for k in kinds))


if __name__ == "__main__":
    main()
