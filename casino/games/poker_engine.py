"""Motor de póker: evaluación de manos, equidad por Monte Carlo y decisiones de los bots."""
import random
from collections import Counter
from itertools import combinations

CAT_NAMES = ["Carta alta", "Pareja", "Doble pareja", "Trío", "Escalera", "Color", "Full", "Póker",
             "Escalera de color"]


def hi(r):
    return 14 if r == 1 else r


def _straight_high(ranks):
    """ranks: conjunto de rangos (2..14). Devuelve la carta alta de la mejor escalera o 0."""
    rs = set(ranks)
    if 14 in rs:
        rs.add(1)
    run = 0
    best = 0
    for r in range(1, 15):
        if r in rs:
            run += 1
            if run >= 5:
                best = r
        else:
            run = 0
    return best


def evaluate(cards):
    """Mejor mano de 5 entre 5..7 cartas. Devuelve una tupla comparable (categoría, desempates...)."""
    ranks = [hi(r) for r, _ in cards]
    suits = {}
    for r, s in cards:
        suits.setdefault(s, []).append(hi(r))
    flush = None
    for s, rs in suits.items():
        if len(rs) >= 5:
            flush = sorted(rs, reverse=True)
    if flush:
        sf = _straight_high(flush)
        if sf:
            return (8, sf)
    cnt = Counter(ranks)
    groups = sorted(cnt.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)
    if groups[0][1] == 4:
        q = groups[0][0]
        kick = max(r for r in ranks if r != q)
        return (7, q, kick)
    trips = sorted([r for r, c in cnt.items() if c >= 3], reverse=True)
    pairs = sorted([r for r, c in cnt.items() if c >= 2], reverse=True)
    if trips:
        t = trips[0]
        rest = [p for p in pairs if p != t]
        if rest:
            return (6, t, rest[0])
    if flush:
        return (5,) + tuple(flush[:5])
    st = _straight_high(ranks)
    if st:
        return (4, st)
    if trips:
        t = trips[0]
        kick = sorted([r for r in ranks if r != t], reverse=True)[:2]
        return (3, t) + tuple(kick)
    if len(pairs) >= 2:
        a, b = pairs[0], pairs[1]
        kick = max(r for r in ranks if r != a and r != b)
        return (2, a, b, kick)
    if pairs:
        p = pairs[0]
        kick = sorted([r for r in ranks if r != p], reverse=True)[:3]
        return (1, p) + tuple(kick)
    return (0,) + tuple(sorted(ranks, reverse=True)[:5])


def evaluate_omaha(hole, board):
    best = None
    for h in combinations(hole, 2):
        for b in combinations(board, 3):
            v = evaluate(list(h) + list(b))
            if best is None or v > best:
                best = v
    return best


def hand_name(v):
    return CAT_NAMES[v[0]]


def full_deck():
    return [(r, s) for s in range(4) for r in range(1, 14)]


# ----------------------------------------------------------------------------
# Equidad por Monte Carlo
# ----------------------------------------------------------------------------
def equity(variant, hole, board, opp_known, n_opp, sims=120, rng=random):
    """Probabilidad de ganar (los empates cuentan proporcionalmente).
    opp_known: lista (por rival) de cartas visibles (stud); board: comunitarias conocidas."""
    if n_opp <= 0:
        return 1.0
    known = list(hole) + list(board) + [c for k in opp_known for c in k]
    deck = [c for c in full_deck() if c not in known]
    wins = 0.0
    for _ in range(sims):
        rng.shuffle(deck)
        i = 0
        if variant in ("holdem", "omaha"):
            need_board = 5 - len(board)
            full_board = list(board) + deck[i:i + need_board]
            i += need_board
            hsz = 2 if variant == "holdem" else 4
            if variant == "holdem":
                mine = evaluate(list(hole) + full_board)
            else:
                mine = evaluate_omaha(hole, full_board)
            best_opp = None
            for _o in range(n_opp):
                oh = deck[i:i + hsz]
                i += hsz
                v = evaluate(oh + full_board) if variant == "holdem" else evaluate_omaha(oh, full_board)
                if best_opp is None or v > best_opp:
                    best_opp = v
        elif variant == "stud7":
            need = 7 - len(hole)
            mine = evaluate(list(hole) + deck[i:i + need])
            i += need
            best_opp = None
            for o in range(n_opp):
                kn = list(opp_known[o]) if o < len(opp_known) else []
                need_o = 7 - len(kn)
                v = evaluate(kn + deck[i:i + need_o])
                i += need_o
                if best_opp is None or v > best_opp:
                    best_opp = v
        else:  # draw5: mano actual contra manos aleatorias de 5
            mine = evaluate(list(hole))
            best_opp = None
            for _o in range(n_opp):
                v = evaluate(deck[i:i + 5])
                i += 5
                if best_opp is None or v > best_opp:
                    best_opp = v
        if mine > best_opp:
            wins += 1
        elif mine == best_opp:
            wins += 0.5
    return wins / sims


# ----------------------------------------------------------------------------
# Bots
# ----------------------------------------------------------------------------
BOT_STYLES = {
    "cauto": {"tight": 0.08, "aggr": 0.6, "bluff": 0.03},
    "agresivo": {"tight": -0.02, "aggr": 1.4, "bluff": 0.10},
    "pasivo": {"tight": 0.03, "aggr": 0.5, "bluff": 0.02},
    "loco": {"tight": -0.10, "aggr": 1.2, "bluff": 0.16},
}


def bot_decide(style, eq, to_call, pot, n_opp, can_raise, rng=random):
    """Devuelve 'fold' | 'call' | 'raise' (call con to_call=0 es pasar)."""
    st = BOT_STYLES[style]
    fair = 1.0 / (n_opp + 1)
    strength = eq - fair
    pot_odds = to_call / (pot + to_call) if to_call > 0 else 0.0
    r = rng.random()
    if can_raise and (strength > 0.18 / st["aggr"] or (eq > 0.7)) and r < 0.55 + 0.25 * min(1.0, st["aggr"] - 0.5):
        return "raise"
    if can_raise and r < st["bluff"]:
        return "raise"
    if to_call <= 0:
        return "call"
    if eq + 0.02 >= pot_odds + st["tight"]:
        return "call"
    return "fold"


def draw5_discards(hand):
    """Qué cartas descarta un bot en Five-Card Draw (índices)."""
    ranks = [hi(r) for r, _ in hand]
    cnt = Counter(ranks)
    keep = set()
    for i, r in enumerate(ranks):
        if cnt[r] >= 2:
            keep.add(i)
    if not keep:
        suits = Counter(s for _, s in hand)
        s, n = suits.most_common(1)[0]
        if n >= 4:
            keep = {i for i, (_, ss) in enumerate(hand) if ss == s}
        elif _straight_high(ranks) == 0:
            order = sorted(range(5), key=lambda i: ranks[i], reverse=True)
            keep = set(order[:2]) if ranks[order[0]] >= 12 else set(order[:1])
        else:
            keep = set(range(5))
    disc = [i for i in range(5) if i not in keep]
    return disc[:3]
