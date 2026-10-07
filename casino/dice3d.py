"""Dados poliédricos en 3D (d6, d8, d12, d20) con sombreado plano y aspecto retro.

La animación termina siempre con la cara del resultado mirando a la cámara."""
import math
import random

import pygame

from . import gfx, pixfont

PHI = (1 + 5 ** 0.5) / 2


# ----------------------------------------------------------------------------
# Álgebra mínima
# ----------------------------------------------------------------------------
def v_add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def v_sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def v_mul(a, k):
    return (a[0] * k, a[1] * k, a[2] * k)


def v_dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def v_cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def v_norm(a):
    L = math.sqrt(v_dot(a, a)) or 1.0
    return (a[0] / L, a[1] / L, a[2] / L)


def q_mul(a, b):
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return (w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2)


def q_axis(axis, ang):
    ax = v_norm(axis)
    s = math.sin(ang / 2)
    return (math.cos(ang / 2), ax[0] * s, ax[1] * s, ax[2] * s)


def q_rot(q, v):
    w, x, y, z = q
    vq = (0.0, v[0], v[1], v[2])
    r = q_mul(q_mul(q, vq), (w, -x, -y, -z))
    return (r[1], r[2], r[3])


def q_between(a, b):
    """Cuaternión que lleva el vector a al vector b."""
    a, b = v_norm(a), v_norm(b)
    d = v_dot(a, b)
    if d > 0.999999:
        return (1.0, 0.0, 0.0, 0.0)
    if d < -0.999999:
        perp = v_cross((1, 0, 0), a)
        if v_dot(perp, perp) < 1e-6:
            perp = v_cross((0, 1, 0), a)
        return q_axis(perp, math.pi)
    c = v_cross(a, b)
    q = (1 + d, c[0], c[1], c[2])
    L = math.sqrt(sum(x * x for x in q))
    return tuple(x / L for x in q)


# ----------------------------------------------------------------------------
# Poliedros
# ----------------------------------------------------------------------------
def _vertices(kind):
    if kind == 6:
        return [(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
    if kind == 8:
        return [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
    if kind == 12:
        p, ip = PHI, 1 / PHI
        vs = [(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
        for a in (-1, 1):
            for b in (-1, 1):
                vs += [(0, a * ip, b * p), (a * ip, b * p, 0), (a * p, 0, b * ip)]
        return vs
    if kind == 20:
        vs = []
        for a in (-1, 1):
            for b in (-1, 1):
                vs += [(0, a, b * PHI), (a, b * PHI, 0), (a * PHI, 0, b)]
        return vs
    raise ValueError(kind)


DUAL = {6: 8, 8: 6, 12: 20, 20: 12}


class Poly:
    def __init__(self, kind):
        self.kind = kind
        verts = [v_norm(v) for v in _vertices(kind)]
        expect = {6: 4, 8: 3, 12: 5, 20: 3}[kind]
        base_normals = [v_norm(v) for v in _vertices(DUAL[kind])]
        normals = base_normals
        for perm in ((0, 1, 2), (1, 2, 0), (2, 0, 1), (0, 2, 1), (2, 1, 0), (1, 0, 2)):
            cand = [(n[perm[0]], n[perm[1]], n[perm[2]]) for n in base_normals]
            ok = True
            for n in cand:
                dots = [v_dot(v, n) for v in verts]
                m = max(dots)
                if sum(1 for d in dots if d > m - 2e-3) != expect:
                    ok = False
                    break
            if ok:
                normals = cand
                break
        faces = []
        for n in normals:
            dots = [v_dot(v, n) for v in verts]
            m = max(dots)
            idx = [i for i, d in enumerate(dots) if d > m - 2e-3]
            # ordenar alrededor de la normal
            c = v_mul(v_add((0, 0, 0), tuple(sum(verts[i][k] for i in idx) for k in range(3))), 1 / len(idx))
            ref = v_norm(v_sub(verts[idx[0]], c))
            ref2 = v_cross(n, ref)
            idx.sort(key=lambda i: math.atan2(v_dot(v_sub(verts[i], c), ref2), v_dot(v_sub(verts[i], c), ref)))
            faces.append({"n": n, "v": idx, "c": c})
        # numeración: caras opuestas suman N+1, como en los dados reales
        order = list(range(len(faces)))
        used = set()
        num = 1
        labels = [0] * len(faces)
        for i in order:
            if i in used:
                continue
            opp = min((j for j in order if j not in used and j != i),
                      key=lambda j: v_dot(faces[i]["n"], faces[j]["n"]))
            labels[i] = num
            labels[opp] = kind + 1 - num
            used |= {i, opp}
            num += 1
        for f, lab in zip(faces, labels):
            f["num"] = lab
        self.verts = verts
        self.faces = faces
        self.by_num = {f["num"]: f for f in faces}


_POLYS = {}


def poly(kind):
    if kind not in _POLYS:
        _POLYS[kind] = Poly(kind)
    return _POLYS[kind]


PIP_POS = {1: [(0, 0)], 2: [(-1, -1), (1, 1)], 3: [(-1, -1), (0, 0), (1, 1)],
           4: [(-1, -1), (1, -1), (-1, 1), (1, 1)], 5: [(-1, -1), (1, -1), (0, 0), (-1, 1), (1, 1)],
           6: [(-1, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (1, 1)]}


# ----------------------------------------------------------------------------
# Dado animado
# ----------------------------------------------------------------------------
class Die:
    COLORS = {6: (246, 244, 236), 8: (90, 170, 255), 12: (176, 120, 230), 20: (255, 120, 90)}

    def __init__(self, kind=6, color=None, ink=None):
        self.kind = kind
        self.poly = poly(kind)
        self.color = color or self.COLORS.get(kind, (240, 240, 240))
        self.ink = ink or ((200, 40, 50) if kind == 6 else (255, 255, 255))
        self.q = q_axis((1, 1, 0), random.uniform(0, 6))
        self.result = None
        self.anim = None
        self.hop = 0.0

    def roll(self, result, dur=1.6):
        """Empieza una tirada que acaba mostrando `result`."""
        self.result = result
        n = self.poly.by_num[result]["n"]
        roll_z = random.uniform(-0.6, 0.6)
        q_final = q_mul(q_axis((0, 0, 1), roll_z), q_between(n, (0, 0, 1)))
        # inclinación final para que se vea el volumen sin perder la cara ganadora
        q_final = q_mul(q_axis((1, 0.55, 0), 0.42), q_final)
        axis = v_norm((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-0.4, 0.4)))
        turns = random.uniform(3.5, 5.5) * math.tau
        self.anim = {"t": 0.0, "dur": dur, "qf": q_final, "axis": axis, "turns": turns, "bounces": 0}

    @property
    def rolling(self):
        return self.anim is not None

    def update(self, dt, on_bounce=None):
        a = self.anim
        if not a:
            return False
        a["t"] += dt
        u = min(1.0, a["t"] / a["dur"])
        e = 1 - (1 - u) ** 3
        ang = a["turns"] * (1 - e)
        self.q = q_mul(q_axis(a["axis"], ang), a["qf"])
        # botes
        k = u * 3.2
        b = int(k)
        frac = k - b
        amp = [1.0, 0.45, 0.18, 0.06][min(3, b)]
        self.hop = abs(math.sin(frac * math.pi)) * amp
        if b > a["bounces"] and b <= 3:
            a["bounces"] = b
            if on_bounce:
                on_bounce(amp)
        if u >= 1.0:
            self.q = a["qf"]
            self.hop = 0.0
            self.anim = None
            return True
        return False

    def render(self, size):
        """Devuelve una superficie pixelada con el dado (size en píxeles finales)."""
        k = 2
        n = max(16, size // k)
        surf = pygame.Surface((n, n), pygame.SRCALPHA)
        c = n / 2
        scale = n * (0.6 if self.kind == 6 else 0.42)
        light = v_norm((-0.4, -0.6, 1.0))
        P = self.poly
        rv = [q_rot(self.q, v) for v in P.verts]
        faces = []
        for f in P.faces:
            nn = q_rot(self.q, f["n"])
            if nn[2] <= 0.02:
                continue
            depth = sum(rv[i][2] for i in f["v"]) / len(f["v"])
            faces.append((depth, nn, f))
        faces.sort(key=lambda x: x[0])
        for depth, nn, f in faces:
            pts = [(c + rv[i][0] * scale, c - rv[i][1] * scale) for i in f["v"]]
            shade = 0.5 + 0.5 * max(0.0, v_dot(nn, light))
            col = gfx.mul_col(self.color, shade)
            pygame.draw.polygon(surf, col, pts)
            pygame.draw.polygon(surf, gfx.mul_col(self.color, 0.35), pts, 1)
            if nn[2] > (0.45 if size >= 120 else 0.86):
                cx = sum(p[0] for p in pts) / len(pts)
                cy = sum(p[1] for p in pts) / len(pts)
                if self.kind == 6:
                    # pips en la cara: base de la cara proyectada
                    a0, a1, a2 = pts[0], pts[1], pts[2]
                    ux, uy = (a1[0] - a0[0]) * 0.28, (a1[1] - a0[1]) * 0.28
                    vx, vy = (a2[0] - a1[0]) * 0.28, (a2[1] - a1[1]) * 0.28
                    pr = max(1, int(n * 0.045 * (0.6 + 0.4 * nn[2])))
                    for gx, gy in PIP_POS[f["num"]]:
                        px, py = cx + ux * gx + vx * gy, cy + uy * gx + vy * gy
                        pygame.draw.circle(surf, self.ink, (int(px), int(py)), pr)
                else:
                    sc = 1
                    t = pixfont.render(str(f["num"]), self.ink if nn[2] > 0.7 else gfx.mul_col(self.ink, 0.8), sc)
                    surf.blit(t, t.get_rect(center=(int(cx), int(cy))))
        return pygame.transform.scale(surf, (n * k, n * k))
