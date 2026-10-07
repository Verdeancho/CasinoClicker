"""Pico minero: física y reglas (sin pygame, la usan el juego y el simulador).

Antes de cada ronda gira un rodillo que decide si cae pico y de qué material (o nada). Si cae, el pico baja por un
pozo de bloques que se genera al azar: como en el original, cada bloque que toca pierde 1 de vida y gasta 1 de
durabilidad del pico (el material solo cambia la durabilidad). Cada impacto da varios golpes seguidos a lo que toca
(una mena aguanta varios; tierra y piedra se rompen al primero) y el pico bota alto, como en el original. Las menas pagan al romperse (en veces la apuesta). Especiales: TNT (explota), bloque de
expansión (pico más ancho unos segundos), mesa de trabajo (repara y sube de material) y slime (lanza el pico). La ronda
acaba cuando el pico se rompe. Nada está decidido de antemano: el pozo es aleatorio y el pico rebota con física.

Unidades: casillas. y crece hacia abajo. El pozo mide COLS casillas de ancho, con paredes de roca madre a los lados.
"""
import math
import random

COLS = 10
GRAVITY = 56.0               # medida en el original (~56 casillas/s²)
MAX_SPEED = 24.0
RADIUS = 0.5                 # el sprite mide 1,3 casillas: a menudo toca dos bloques a la vez
BOUNCE_H = (0.08, 1.8)       # altura de cada bote en casillas, repartida en escala logarítmica como en el original
                             # (medido: mediana 0,33, p75 0,9, p90 1,5; 1 de cada 5 botes pasa de una casilla)
MULTI_HIT = (1, 4)           # golpes por impacto a cada bloque tocado (el original gasta ~3 de vida por impacto)
KICK = 1.4                   # empujón lateral aleatorio en cada golpe
WIDEN_STEP = 0.5             # cada bloque de expansión ensancha el pico +0,5 (x1,5, x2, x2,5)...
WIDEN_TIME = 3.0             # ...durante 3 segundos (se acumula)
WIDEN_MAX = 2.5
TNT_RADIUS = 2.8
TNT_ABILITY_RADIUS = 2.6     # la carga de TNT del jugador (hazaña Dinamitero)
MAX_WIN = 10000.0            # tope de seguridad: en la práctica no se alcanza
MAX_TIME = 900.0             # tope de seguridad de una ronda (segundos de juego)
ENCHANT_HITS = 100           # trampa del mercado negro: golpes gratis
DEEP_ROW = 45                # a partir de aquí, piedra profunda (solo cambia el aspecto y el carbón)

# material: nombre, durabilidad (como en el original, todos quitan 1 de vida por golpe)
TIERS = [
    ("Madera", 100),
    ("Piedra", 150),
    ("Hierro", 200),
    ("Diamante", 400),
    ("Netherita", 600),
]
MAX_BENCH_TIER = 3           # la mesa de trabajo sube hasta diamante (la netherita solo se consigue aparte)

# bloque: nombre, vida, premio (veces la apuesta)
BLOCKS = {
    "grass": ("Césped", 1, 0.0),
    "dirt": ("Tierra", 1, 0.0),
    "stone": ("Piedra", 1, 0.0),
    "coal": ("Carbón", 5, 0.01),
    "redstone": ("Redstone", 10, 0.05),
    "gold": ("Oro", 15, 0.2),
    "diamond": ("Diamante", 20, 1.0),
    "emerald": ("Esmeralda", 30, 5.0),
    "diamond_block": ("Bloque de diamante", 40, 6.0),
    "emerald_block": ("Bloque de esmeralda", 80, 30.0),
    "tnt": ("TNT", 1, 0.0),
    "arrow": ("Expansión", 1, 0.0),
    "bench": ("Mesa de trabajo", 1, 0.0),
    "slime": ("Slime", 1, 0.0),
}
ORES = ("coal", "redstone", "gold", "diamond", "emerald", "diamond_block", "emerald_block")
# reparación (legendaria) al romper cada mena; MEND_SCALE la ajusta para que el juego rinda ~105%
MEND = {"coal": 1, "redstone": 3, "gold": 6, "diamond": 18, "emerald": 45, "diamond_block": 80,
        "emerald_block": 200}
MEND_SCALE = 0.09

# El pozo se genera por tramos de CHUNK filas. En cada tramo se colocan vetas (manchas de un mismo mineral que
# crecen bloque a bloque). RICH escala el número de vetas para fijar el retorno.
RICH = 2.0
CHUNK = 12
# vetas por tramo (a profundidad "rica") y tamaño (mín, máx) de cada una
VEINS = {"coal": (1.4, (4, 9)), "redstone": (2.4, (5, 12)), "gold": (1.7, (4, 10)), "diamond": (0.5, (3, 6)),
         "emerald": (0.14, (2, 5))}
GEM_BLOCK_P = {"diamond_block": 0.0040, "emerald_block": 0.0008}    # sueltos, en las columnas del borde
EDGE_W = [1.0, 0.55, 0.06, 0.03, 0.03, 0.03, 0.03, 0.06, 0.55, 1.0]      # peso de cada columna para los bloques de gema
SPECIAL_P = {"tnt": 0.038, "arrow": 0.020, "bench": 0.006, "slime": 0.004}
AIR_P = 0.04
DIRT_ROWS = 4                # filas de tierra de la superficie (sin menas buenas todavía)


MIN_ROW = {"coal": 1, "redstone": 2, "gold": 4, "diamond": 6, "emerald": 10}   # profundidad mínima


def depth_factor(row):
    """Como en el original, la riqueza no depende de la profundidad (pasada la superficie): así cada material vale
    casi en proporción a su durabilidad y la mayor parte del premio llega de las cadenas de TNT."""
    return 1.0


def _poisson(rng, lam):
    k, p, l = 0, 1.0, math.exp(-lam)
    while True:
        p *= rng.random()
        if p <= l:
            return k
        k += 1


def gen_chunk(rng, k, rich=None):
    """Genera las filas [k*CHUNK, (k+1)*CHUNK) del pozo."""
    rich = RICH if rich is None else rich
    r0 = k * CHUNK
    rows = []
    for i in range(CHUNK):
        row = r0 + i
        if row == 0:
            rows.append([["grass", 1] for _ in range(COLS)])
            continue
        rows.append([None if rng.random() < AIR_P else
                     (["dirt", 1] if (row < DIRT_ROWS or rng.random() < 0.12) else ["stone", 1]) for _ in range(COLS)])
    g = depth_factor(r0 + CHUNK // 2)
    weight = {"coal": 1.0 if r0 < DEEP_ROW else 0.3, "redstone": 0.5 + g, "gold": g, "diamond": g,
              "emerald": g ** 1.5}
    for ore, (n, (lo, hi)) in VEINS.items():
        for _ in range(_poisson(rng, n * rich * weight[ore])):
            size = rng.randint(lo, hi)
            cx, cy = rng.randrange(COLS), rng.randrange(CHUNK)
            cells = {(cx, cy)}
            frontier = [(cx, cy)]
            while len(cells) < size and frontier:
                x, y = rng.choice(frontier)
                dx, dy = rng.choice(((1, 0), (-1, 0), (0, 1), (0, -1)))
                nx, ny = x + dx, y + dy
                if 0 <= nx < COLS and 0 <= ny < CHUNK and (nx, ny) not in cells:
                    cells.add((nx, ny))
                    frontier.append((nx, ny))
                elif rng.random() < 0.3:
                    frontier.remove((x, y))
            for x, y in cells:
                if r0 + y < MIN_ROW[ore] or r0 + y == 0:
                    continue
                b = rows[y][x]
                if b is None or b[0] in ("stone", "dirt"):
                    rows[y][x] = [ore, BLOCKS[ore][1]]
    # bloques especiales y bloques de gema (sueltos)
    for i in range(CHUNK):
        row = r0 + i
        if row == 0:
            continue
        gg = depth_factor(row)
        for c in range(COLS):
            u = rng.random()
            acc = 0.0
            for kind, p in (("tnt", SPECIAL_P["tnt"]), ("arrow", SPECIAL_P["arrow"]), ("bench", SPECIAL_P["bench"]),
                            ("slime", SPECIAL_P["slime"]),
                            ("diamond_block", GEM_BLOCK_P["diamond_block"] * rich * gg * EDGE_W[c]),
                            ("emerald_block", GEM_BLOCK_P["emerald_block"] * rich * gg ** 1.5 * EDGE_W[c])):
                acc += p
                if u < acc:
                    rows[i][c] = [kind, BLOCKS[kind][1]]
                    break
    return rows


class Run:
    """Una caída del pico. Se avanza con step(dt) y deja eventos en self.events para la parte visual."""

    def __init__(self, rng=None, tier=0, mending=False, enchanted=False, rich=None):
        self.rng = rng or random.Random()
        self.rich = rich
        self.tier = tier
        self.dur = TIERS[tier][1]
        self.max_dur = self.dur
        self.mending = mending
        self.free_hits = ENCHANT_HITS if enchanted else 0
        self.x = COLS / 2
        self.y = -2.5
        self.vx = self.rng.uniform(-0.5, 0.5)
        self.vy = 0.0
        self.angle = self.rng.uniform(0, 360)
        self.spin = self.rng.uniform(-200, 200)
        self.rows = {}
        self.widen = 1.0
        self.widen_t = 0.0
        self.win = 0.0              # premio acumulado (veces la apuesta)
        self.hits = 0
        self.t = 0.0
        self.done = False
        self.max_row = 0
        self.tnt_broken = 0         # bloques rotos por explosiones (hazaña Dinamitero)
        self.ores = {k: 0 for k in ORES}
        self.events = []            # (tipo, datos) para efectos y sonidos

    # ------------------------------------------------------------- mundo
    def row(self, r):
        rw = self.rows.get(r)
        if rw is None:
            if r < 0:
                rw = [None] * COLS
                self.rows[r] = rw
            else:
                k = r // CHUNK
                for i, cells in enumerate(gen_chunk(self.rng, k, self.rich)):
                    self.rows[k * CHUNK + i] = cells
                rw = self.rows[r]
        return rw

    def cell(self, c, r):
        if c < 0 or c >= COLS:
            return None
        return self.row(r)[c]

    def radius(self):
        return RADIUS * self.widen

    # ------------------------------------------------------------- bloques
    def collect(self, kind, c, r):
        v = BLOCKS[kind][2]
        if v:
            self.win = min(MAX_WIN, self.win + v)
            self.ores[kind] += 1
            if self.mending:
                self.dur = min(self.max_dur, self.dur + MEND[kind] * MEND_SCALE)
        self.events.append(("break", (kind, c, r, v)))

    def break_cell(self, c, r, by_tnt=False):
        rw = self.row(r)
        b = rw[c]
        if not b:
            return
        rw[c] = None
        kind = b[0]
        if by_tnt:
            self.tnt_broken += 1
        self.collect(kind, c, r)
        if kind == "tnt":
            self.explode(c + 0.5, r + 0.5, TNT_RADIUS)
        elif kind == "arrow":
            self.widen = min(WIDEN_MAX, self.widen + WIDEN_STEP)
            self.widen_t = WIDEN_TIME
            self.events.append(("arrow", None))
        elif kind == "bench":
            self.upgrade()


    def upgrade(self):
        """Mesa de trabajo: repara del todo y sube un material (hasta diamante)."""
        if self.tier < MAX_BENCH_TIER:
            self.tier += 1
        self.max_dur = TIERS[self.tier][1]
        self.dur = self.max_dur
        self.events.append(("bench", self.tier))

    def explode(self, cx, cy, rad):
        self.events.append(("boom", (cx, cy, rad)))
        r0, r1 = int(math.floor(cy - rad)), int(math.floor(cy + rad))
        for r in range(max(0, r0), r1 + 1):
            for c in range(COLS):
                if (c + 0.5 - cx) ** 2 + (r + 0.5 - cy) ** 2 <= rad * rad and self.cell(c, r):
                    self.break_cell(c, r, by_tnt=True)
        self.vy = min(self.vy, -self.rng.uniform(9, 13))
        self.vx += self.rng.uniform(-3, 3)

    def use_tnt(self):
        """Carga de TNT del jugador: explota donde está el pico."""
        if not self.done:
            self.explode(self.x, self.y, TNT_ABILITY_RADIUS)

    def use_anvil(self):
        """Yunque del jugador (hazaña Plus Ultra): repara el pico entero, sin cambiar de material."""
        if not self.done:
            self.dur = self.max_dur
            self.events.append(("anvil", None))

    # ------------------------------------------------------------- física
    def contacts(self):
        rad = self.radius()
        out = []
        for r in range(int(math.floor(self.y - rad)), int(math.floor(self.y + rad)) + 1):
            if r < 0:
                continue
            for c in range(int(math.floor(self.x - rad)), int(math.floor(self.x + rad)) + 1):
                if not self.cell(c, r):
                    continue
                px = min(max(self.x, c), c + 1)
                py = min(max(self.y, r), r + 1)
                dx, dy = self.x - px, self.y - py
                d2 = dx * dx + dy * dy
                if d2 < rad * rad:
                    out.append((c, r, dx, dy, d2))
        return out

    def step(self, dt):
        if self.done:
            return
        self.t += dt
        if self.widen_t > 0:
            self.widen_t -= dt
            if self.widen_t <= 0:
                self.widen = 1.0
        self.vy = min(MAX_SPEED, self.vy + GRAVITY * dt)
        self.vx *= 0.995
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.angle += self.spin * dt
        rad = self.radius()
        # paredes de roca madre
        if self.x < rad:
            self.x, self.vx = rad, abs(self.vx) * 0.6
        elif self.x > COLS - rad:
            self.x, self.vx = COLS - rad, -abs(self.vx) * 0.6
        cs = self.contacts()
        if cs:
            self.hit(cs)
        self.max_row = max(self.max_row, int(self.y))
        if self.dur <= 0 or self.t > MAX_TIME:
            self.done = True
            self.events.append(("end", None))

    def bounce_v(self):
        h = math.exp(self.rng.uniform(math.log(BOUNCE_H[0]), math.log(BOUNCE_H[1])))
        return -math.sqrt(2 * GRAVITY * h)

    def hit(self, cs):
        """Un impacto: da k golpes a cada bloque tocado (cada golpe quita 1 de vida al bloque y 1 de durabilidad) y bota."""
        slime = [s_ for s_ in cs if (self.cell(s_[0], s_[1]) or [None])[0] == "slime"]
        if slime:                                     # el slime no gasta el pico: lo lanza
            c, r = slime[0][0], slime[0][1]
            self.vy = -self.rng.uniform(13, 16)
            self.vx = (1 if self.x > c + 0.5 else -1) * self.rng.uniform(4, 6.5)
            self.y = min(self.y, r - self.radius() - 1e-3) if self.y < r + 0.5 else self.y
            self.events.append(("slime", (c, r)))
            return
        survivors = []
        k = self.rng.randint(*MULTI_HIT)
        for c, r, dx, dy, d2 in cs:
            b = self.cell(c, r)
            if not b:
                continue
            n = min(k, b[1])                          # tierra y piedra se rompen al primer golpe
            self.hits += n
            free = min(n, self.free_hits)
            self.free_hits -= free
            self.dur -= n - free
            b[1] -= n
            self.events.append(("hit", (b[0], c, r)))
            if b[1] <= 0:
                self.break_cell(c, r)
            else:
                survivors.append((c, r, dx, dy, d2))
        self.spin = self.rng.uniform(-420, 420)
        if not survivors:
            # rompe y bota igualmente, luego cae por el hueco
            if self.vy > 0:
                self.vy = self.bounce_v()
            self.vx = self.vx * 0.7 + self.rng.uniform(-KICK, KICK) * 0.6
            return
        # empuja fuera del bloque más metido y rebota
        c, r, dx, dy, d2 = min(survivors, key=lambda s: s[4])
        d = math.sqrt(d2) if d2 > 1e-12 else 0.0
        rad = self.radius()
        if d > 1e-6:
            nx, ny = dx / d, dy / d
        else:
            nx, ny = 0.0, -1.0
        self.x += nx * (rad - d + 1e-3)
        self.y += ny * (rad - d + 1e-3)
        if ny < -0.5:                                 # cae encima: rebota hacia arriba
            self.vy = self.bounce_v()
            self.vx = self.vx * 0.7 + self.rng.uniform(-KICK, KICK)
        elif ny > 0.5:                                # golpe con el techo
            self.vy = abs(self.vy) * 0.3
        else:                                         # golpe lateral
            self.vx = nx * max(1.0, abs(self.vx) * 0.5)
            self.vy = min(self.vy, -self.rng.uniform(1.5, 2.5))


# ---------------------------------------------------------------- rodillo
# Como el original: en cada giro hay P_DROP de que salga pico (si no, cruz) y tras PITY cruces seguidas el siguiente
# giro da pico seguro (en la práctica cae pico ~1 de cada 5 giros). El material sale de TIER_W.
P_DROP = 0.212
PITY = 7
TIER_W = [(0, 0.50), (1, 0.44), (2, 0.05), (3, 0.01)]


def drop_rate():
    """Fracción de giros en los que cae pico, contando la garantía."""
    q = 1 - P_DROP
    return P_DROP / (1 - q ** (PITY + 1))


def spin_reel(rng, crosses=0):
    """Resultado del rodillo: 'nothing' (cruz) o el material del pico. `crosses`: cruces seguidas hasta ahora."""
    if crosses < PITY and rng.random() >= P_DROP:
        return "nothing"
    u = rng.random()
    acc = 0.0
    for tier, w in TIER_W:
        acc += w
        if u < acc:
            return tier
    return TIER_W[-1][0]


def simulate(rng, tier=0, mending=False, enchanted=False, rich=None, dt=1 / 60, policy=None):
    """Juega una caída entera sin pantalla. policy(run) puede usar la TNT o el yunque del jugador."""
    run = Run(rng, tier, mending, enchanted, rich)
    while not run.done:
        run.step(dt)
        if policy:
            policy(run)
        run.events.clear()
    return run
