"""Sistema de partículas y efectos (monedas, chispas, confeti, textos flotantes, ondas)."""
import math
import random

import pygame
import pygame.gfxdraw as gd

from . import gfx, art

CONFETTI = [(255, 92, 104), (255, 200, 72), (88, 164, 255), (64, 220, 140), (176, 120, 255), (255, 150, 60),
            (255, 120, 196)]


class FX:
    def __init__(self):
        self.p = []
        self.shake = 0.0

    def clear(self):
        self.p = []

    # -------------------------------------------------------------- emisores
    def coins(self, x, y, n=4, power=1.0, size=16):
        for _ in range(n):
            a = random.uniform(-math.pi * 0.95, -math.pi * 0.05)
            sp = random.uniform(160, 340) * power
            self.p.append({"k": "coin", "x": x, "y": y, "vx": math.cos(a) * sp, "vy": math.sin(a) * sp,
                           "life": random.uniform(0.7, 1.1), "age": 0, "g": 900, "size": size,
                           "spin": random.uniform(6, 14), "ph": random.uniform(0, 6)})

    def sparks(self, x, y, n=10, color=(255, 220, 120), power=1.0, size=10, life=0.6):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            sp = random.uniform(40, 260) * power
            self.p.append({"k": "spark", "x": x, "y": y, "vx": math.cos(a) * sp, "vy": math.sin(a) * sp,
                           "life": random.uniform(life * 0.5, life), "age": 0, "g": 60, "size": size,
                           "col": color, "drag": 2.5})

    def confetti(self, x, y, n=60, spread=1.0, w=None):
        for _ in range(n):
            if w:
                sx = x + random.uniform(-w / 2, w / 2)
                a = random.uniform(-0.3, 0.3) + math.pi / 2
                sp = random.uniform(30, 120)
                sy = y
            else:
                sx, sy = x, y
                a = random.uniform(-math.pi * 0.9, -math.pi * 0.1)
                sp = random.uniform(250, 600) * spread
            self.p.append({"k": "conf", "x": sx, "y": sy, "vx": math.cos(a) * sp, "vy": math.sin(a) * sp,
                           "life": random.uniform(1.6, 2.6), "age": 0, "g": 420, "col": random.choice(CONFETTI),
                           "rot": random.uniform(0, 6), "vr": random.uniform(-10, 10), "drag": 1.4,
                           "w": random.uniform(6, 11), "h": random.uniform(3, 6), "wob": random.uniform(0, 6)})

    def text(self, x, y, s, color=gfx.GOLD, size=22, life=1.1, rise=70, weight="bl"):
        surf = gfx.text_surf(s, size, weight, color)
        self.p.append({"k": "text", "x": x, "y": y, "surf": surf, "sh": None, "life": life, "age": 0,
                       "rise": rise, "y0": y})

    def ring(self, x, y, color=(255, 220, 120), r0=20, r1=120, life=0.5, width=4):
        self.p.append({"k": "ring", "x": x, "y": y, "col": color, "r0": r0, "r1": r1, "life": life, "age": 0,
                       "w": width})

    def flash(self, x, y, radius=120, color=(255, 230, 160), life=0.35):
        self.p.append({"k": "flash", "x": x, "y": y, "r": radius, "col": color, "life": life, "age": 0})

    def add_shake(self, amount):
        self.shake = max(self.shake, amount)

    # ---------------------------------------------------------------- update
    def update(self, dt):
        self.shake = max(0.0, self.shake - dt * 30)
        alive = []
        for q in self.p:
            q["age"] += dt
            if q["age"] >= q["life"]:
                continue
            k = q["k"]
            if k in ("coin", "spark", "conf"):
                drag = q.get("drag", 0)
                if drag:
                    f = math.exp(-drag * dt)
                    q["vx"] *= f
                    q["vy"] *= f
                q["vy"] += q["g"] * dt
                q["x"] += q["vx"] * dt
                q["y"] += q["vy"] * dt
                if k == "conf":
                    q["rot"] += q["vr"] * dt
                    q["vy"] = min(q["vy"], 160)
                    q["x"] += math.sin(q["age"] * 6 + q["wob"]) * 40 * dt
            alive.append(q)
        self.p = alive

    def shake_offset(self):
        if self.shake <= 0:
            return 0, 0
        return random.uniform(-self.shake, self.shake), random.uniform(-self.shake, self.shake)

    # ------------------------------------------------------------------ draw
    def draw(self, surf):
        for q in self.p:
            k = q["k"]
            t = q["age"] / q["life"]
            if k == "coin":
                frames = art.coin_frames(q["size"])
                i = int((q["age"] * q["spin"] + q["ph"]) * 2) % len(frames)
                img = frames[i]
                if t > 0.7:
                    img = img.copy()
                    img.set_alpha(int(255 * (1 - t) / 0.3))
                surf.blit(img, img.get_rect(center=(int(q["x"]), int(q["y"]))))
            elif k == "spark":
                r = max(2, int(q["size"] * 0.6 * (1 - t)) // 2 * 2)
                surf.fill(q["col"], (int(q["x"]) - r // 2, int(q["y"]) - r // 2, r, r))
            elif k == "conf":
                c, s = math.cos(q["rot"]), math.sin(q["rot"])
                w, h = q["w"] / 2, q["h"] / 2 * abs(math.cos(q["age"] * 7 + q["wob"]))
                pts = [(q["x"] + dx * c - dy * s, q["y"] + dx * s + dy * c)
                       for dx, dy in ((-w, -h), (w, -h), (w, h), (-w, h))]
                col = q["col"]
                if t > 0.75:
                    col = (*col, int(255 * (1 - t) / 0.25))
                gfx.aa_poly(surf, col, pts)
            elif k == "text":
                e = gfx.ease_out_cubic(t)
                y = q["y0"] - q["rise"] * e
                a = 255 if t < 0.6 else int(255 * (1 - t) / 0.4)
                sc = 1.0 + 0.25 * max(0, 1 - t * 6)
                img = q["surf"]
                if sc > 1.01:
                    img = gfx.scaled(img, sc)
                gfx.blit_center(surf, img, (q["x"], y), a)
            elif k == "ring":
                e = gfx.ease_out_cubic(t)
                r = int(q["r0"] + (q["r1"] - q["r0"]) * e)
                a = int(220 * (1 - t))
                if r > 1:
                    for wv in range(q["w"]):
                        gd.circle(surf, int(q["x"]), int(q["y"]), r - wv, (*q["col"], a))
            elif k == "flash":
                gfx.glow(surf, (q["x"], q["y"]), int(q["r"] * (0.8 + 0.4 * t)), q["col"], 0.8 * (1 - t))
