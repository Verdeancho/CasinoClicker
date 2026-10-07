"""Lógica pura de la Princesa Estelar (sin gráficos), basada en las reglas de Starlight Princess.

- Rejilla 6x5, «paga en cualquier lugar»: 8+ símbolos iguales en pantalla dan premio.
- Cascadas: los símbolos ganadores desaparecen, los demás caen y entran nuevos. Sin límite.
- Orbes multiplicadores (x2 a x500): al acabar una secuencia ganadora se suman y multiplican el premio.
- 4+ scatters: 15 tiradas gratis (paga 3x / 5x / 100x con 4 / 5 / 6).
- En las tiradas gratis los orbes se acumulan en un multiplicador total que persiste y todo paga el doble.
- 3+ scatters durante las gratis: +5 tiradas.
- Compra del bonus por 100x la apuesta. Ante: +25% de apuesta, ~45% más probabilidad de bonus.
- Las tiradas normales son secas a propósito: el juego gira en torno a las tiradas gratis (~1 de cada 140).
"""
import bisect
import random

COLS, ROWS = 6, 5
SYMBOLS = ["sun", "heart", "moon", "star", "red", "blue", "green", "teal", "yellow"]
PAY = {  # 8-9, 10-11, 12+   (x apuesta total; en las tiradas gratis se paga el doble)
    "sun": (6.1, 15.25, 30.5),
    "heart": (1.52, 6.1, 15.25),
    "moon": (1.22, 3.05, 9.15),
    "star": (0.92, 1.22, 7.32),
    "red": (0.61, 0.92, 6.1),
    "blue": (0.49, 0.73, 4.88),
    "green": (0.3, 0.61, 3.05),
    "teal": (0.24, 0.55, 2.44),
    "yellow": (0.15, 0.46, 1.22),
}
SCATTER_PAY = {4: 3, 5: 5, 6: 100}
FREE_SPINS = 15
FS_MULT = 2.0          # en las tiradas gratis todo paga el doble
RETRIGGER = 5
BUY_COST = 100
MAX_WIN = 5000
ORB_VALUES = [2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 50, 100, 250, 500]
ORB_WEIGHTS = [260, 200, 160, 130, 100, 75, 58, 42, 30, 22, 16, 8, 3, 0.6, 0.15]

# Pesos ajustados por simulación (tune_princess3.py) para un retorno del ~96,5% en los tres modos
PARAMS = {
    "base": {"w": [2.2483, 3.2768, 3.7484, 4.1997, 5.0548, 5.4632, 6.2494, 6.6294, 7.3673], "scatter": 0.02409,
             "orb": 0.006},
    "ante": {"w": [2.2483, 3.2768, 3.7484, 4.1997, 5.0548, 5.4632, 6.2494, 6.6294, 7.3673], "scatter": 0.0264,
             "orb": 0.006},
    "fs": {"w": [3.0, 5.0, 6.0, 7.0, 9.0, 10.0, 12.0, 13.0, 15.0], "scatter": 0.016, "orb": 0.0286},
}


def pay_for(sym, n):
    p = PAY[sym]
    return p[2] if n >= 12 else (p[1] if n >= 10 else p[0])


class Gen:
    """Generador de celdas con pesos (símbolos + scatter + orbe)."""

    def __init__(self, params, rng):
        self.rng = rng
        items = list(SYMBOLS) + ["scatter", "orb"]
        total_sym = sum(params["w"])
        ws = list(params["w"]) + [params["scatter"] * total_sym, params["orb"] * total_sym]
        self.items = items
        acc = 0.0
        self.cum = []
        for w in ws:
            acc += w
            self.cum.append(acc)
        self.total = acc
        oacc = 0.0
        self.ocum = []
        for w in ORB_WEIGHTS:
            oacc += w
            self.ocum.append(oacc)
        self.ototal = oacc

    def cell(self):
        r = self.rng.random() * self.total
        s = self.items[bisect.bisect_right(self.cum, r)]
        if s == "orb":
            v = ORB_VALUES[bisect.bisect_right(self.ocum, self.rng.random() * self.ototal)]
            return (s, v)
        return (s, 0)


def new_grid(gen):
    return [[gen.cell() for _ in range(ROWS)] for _ in range(COLS)]


def find_wins(grid):
    pos = {}
    for c in range(COLS):
        for r in range(ROWS):
            s = grid[c][r][0]
            if s in PAY:
                pos.setdefault(s, []).append((c, r))
    return {s: p for s, p in pos.items() if len(p) >= 8}


def tumble(grid, wins, gen):
    """Quita los ganadores y rellena. Devuelve (nueva_rejilla, info_de_caida)."""
    remove = set(p for ps in wins.values() for p in ps)
    new = []
    falls = []   # por columna: lista de (fila_origen o None si es nueva, fila_destino)
    for c in range(COLS):
        survivors = [(r, grid[c][r]) for r in range(ROWS) if (c, r) not in remove]
        n_new = ROWS - len(survivors)
        col = [gen.cell() for _ in range(n_new)] + [cell for _, cell in survivors]
        info = [(None, i) for i in range(n_new)] + [(r0, n_new + k) for k, (r0, _) in enumerate(survivors)]
        new.append(col)
        falls.append(info)
    return new, falls


def scatters(grid):
    return sum(1 for c in range(COLS) for r in range(ROWS) if grid[c][r][0] == "scatter")


def orb_sum(grid):
    return sum(grid[c][r][1] for c in range(COLS) for r in range(ROWS) if grid[c][r][0] == "orb")


def play_spin(gen, record=False):
    """Una tirada completa con cascadas. Devuelve dict con premio base, orbes, scatters y pasos."""
    grid = new_grid(gen)
    steps = [{"grid": grid}] if record else None
    seq = 0.0
    while True:
        wins = find_wins(grid)
        if not wins:
            break
        amt = sum(pay_for(s, len(p)) for s, p in wins.items())
        seq += amt
        new, falls = tumble(grid, wins, gen)
        if record:
            steps.append({"wins": wins, "amount": amt, "grid": new, "falls": falls, "prev": grid})
        grid = new
    return {"win": seq, "orbs": orb_sum(grid), "scatters": scatters(grid), "steps": steps, "grid": grid}


def base_result(spin):
    """Premio de una tirada normal (x apuesta) y si activa las gratis."""
    win = spin["win"]
    if win > 0 and spin["orbs"] > 0:
        win *= spin["orbs"]
    trig = spin["scatters"] >= 4
    if trig:
        win += SCATTER_PAY[min(6, spin["scatters"])]
    return min(win, MAX_WIN), trig


def fs_result(spin, total_mult):
    """Premio de una tirada gratis. Devuelve (premio, nuevo multiplicador total, tiradas extra)."""
    win = spin["win"] * FS_MULT
    if win > 0 and spin["orbs"] > 0:
        total_mult += spin["orbs"]
        win *= total_mult
    extra = RETRIGGER if spin["scatters"] >= 3 else 0
    return win, total_mult, extra


def simulate_bonus(rng, params=None):
    params = params or PARAMS["fs"]
    gen = Gen(params, rng)
    left, total, mult = FREE_SPINS, 0.0, 0
    retrig = 0
    while left > 0 and total < MAX_WIN:
        left -= 1
        sp = play_spin(gen)
        w, mult, extra = fs_result(sp, mult)
        total += w
        if extra:
            left += extra
            retrig += 1
    return min(total, MAX_WIN), retrig


def simulate_base(n, mode="base", seed=1):
    rng = random.Random(seed)
    gen = Gen(PARAMS[mode], rng)
    total, trig = 0.0, 0
    for _ in range(n):
        w, t = base_result(play_spin(gen))
        total += w
        trig += t
    return total / n, trig / n
