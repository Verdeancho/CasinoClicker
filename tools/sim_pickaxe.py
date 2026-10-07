"""Simulador del Pico Minero: valor de cada caída por material, rodillo, precios de compra, ventajas y hazañas.

    .venv\\Scripts\\python tools\\sim_pickaxe.py [rondas] [modo] [riqueza]
      modos: tiers (valor y reparto de cada material y retorno con el rodillo actual)
             extras (ventajas: TNT, yunque, trampa, reparación)
"""
import multiprocessing as mp
import os
import random
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from casino.games import pickaxe_logic as L  # noqa: E402


def tnt_policy(run):
    """Usa la carga de TNT al tener cerca una mena buena (o antes de romperse)."""
    if getattr(run, "_tnt_used", False):
        return
    rad = L.TNT_ABILITY_RADIUS
    val = 0.0
    for r in range(max(0, int(run.y - rad)), int(run.y + rad) + 1):
        for c in range(L.COLS):
            b = run.cell(c, r)
            if b and (c + 0.5 - run.x) ** 2 + (r + 0.5 - run.y) ** 2 <= rad * rad:
                val += L.BLOCKS[b[0]][2]
    if val >= 0.2 or run.dur <= 1:
        run._tnt_used = True
        run.use_tnt()


def anvil_policy(run):
    """Usa el yunque justo antes de romperse."""
    if not getattr(run, "_anvil_used", False) and run.dur <= 1:
        run._anvil_used = True
        run.use_anvil()


POLICIES = {None: None, "tnt": tnt_policy, "anvil": anvil_policy}


def work(args):
    seed, n, tier, mending, enchanted, rich, pol = args
    if isinstance(mending, float):
        L.MEND_SCALE, mending = mending, True
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        r = L.simulate(rng, tier, mending, enchanted, rich, policy=POLICIES[pol])
        out.append((r.win, r.tnt_broken, r.max_row, r.t))
    return out


def run_many(n, tier=0, mending=False, enchanted=False, rich=None, pol=None, seed=1, procs=None):
    procs = procs or max(1, os.cpu_count() - 1)
    chunk = max(1, n // (procs * 4))
    jobs = [(seed * 100003 + i, chunk, tier, mending, enchanted, rich, pol) for i in range(max(1, n // chunk))]
    with mp.Pool(procs) as pool:
        return [x for part in pool.map(work, jobs) for x in part]


def ev(res):
    return st.mean(r[0] for r in res)


def describe(res):
    w = sorted(r[0] for r in res)
    n = len(w)
    return (f"vale x{st.mean(w):.3f} · gana algo (>x1) {sum(x > 1 for x in w) / n * 100:.0f}% · "
            f"mediana x{w[n // 2]:.2f} · p90 x{w[int(n * .9)]:.1f} · p99 x{w[int(n * .99)]:.1f} · "
            f"tiempo medio {st.mean(r[3] for r in res):.0f}s")


if __name__ == "__main__":
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 200_000
    mode = sys.argv[2] if len(sys.argv) > 2 else "tiers"
    rich = float(sys.argv[3]) if len(sys.argv) > 3 else None
    if mode == "tiers":
        evs = {}
        for t in range(5):
            res = run_many(N if t < 3 else N // 3, tier=t, rich=rich)
            evs[t] = ev(res)
            print(f"{L.TIERS[t][0]:9s} {describe(res)}", flush=True)
            if t == 0:
                for q in (0.99, 0.995, 0.998):
                    print(f"   TNT rotos p{q*100:g}: {sorted(r[1] for r in res)[int(len(res)*q)]}   "
                          f"profundidad p{q*100:g}: {sorted(r[2] for r in res)[int(len(res)*q)]}")
        per_drop = sum(w * evs[t] for t, w in L.TIER_W)
        tot = L.drop_rate() * per_drop
        print(f"Cae pico en {L.drop_rate()*100:.1f}% de los giros · una caída vale x{per_drop:.3f} · "
              f"retorno total {tot:.4f}")
    elif mode == "extras":
        for name, kw in (("TNT", {"pol": "tnt"}), ("yunque", {"pol": "anvil"}), ("trampa", {"enchanted": True}),
                         ("reparación", {"mending": L.MEND_SCALE})):
            print(f"{name:10s} {describe(run_many(N, rich=rich, **kw))}", flush=True)
