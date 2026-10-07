"""Dibuja las texturas del Pico Minero en casino/assets/pickaxe (16x16). Todas son propias:
piedra y minerales (tools/make_ores.py), tierra, césped, hierba, roca madre, bloques de gema, TNT, mesa de trabajo,
slime, bloque de expansión, grietas y picos. El yunque y los picos salen de imágenes del autor (fotos referencias/).

    .venv\\Scripts\\python tools\\make_ores.py
    .venv\\Scripts\\python tools\\make_pickaxe_assets.py
"""
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "casino", "assets", "pickaxe")


def tnt():
    red, red2, white, ink = (212, 52, 40), (168, 32, 26), (236, 230, 220), (34, 26, 26)
    im = Image.new("RGBA", (16, 16), (*red, 255))
    px = im.load()
    for x in range(16):
        for y in range(16):
            if x % 3 == 0:
                px[x, y] = (*red2, 255)
    for x in range(16):
        for y in range(5, 11):
            px[x, y] = (*white, 255)
    letters = {"T": ["###", ".#.", ".#.", ".#."], "N": ["#..#", "##.#", "#.##", "#..#"]}
    x0 = 2
    for ch in "TNT":
        for j, row in enumerate(letters[ch]):
            for i, c in enumerate(row):
                if c == "#":
                    px[x0 + i, 6 + j] = (*ink, 255)
        x0 += len(letters[ch][0]) + 1
    for x in range(16):                                   # bordes del papel
        px[x, 5] = (196, 190, 180, 255)
        px[x, 10] = (196, 190, 180, 255)
    return im


def arrow_block():
    """Bloque de expansión (inventado): cristal violeta con chevrones que empujan hacia los lados."""
    frame, frame2, bg, bg2 = (64, 40, 110), (44, 26, 80), (110, 70, 190), (128, 88, 210)
    glow, core, hi = (236, 200, 255), (200, 140, 255), (255, 255, 255)
    im = Image.new("RGBA", (16, 16), (*bg, 255))
    px = im.load()
    for y in range(16):
        for x in range(16):
            if (x + y) % 4 == 0:
                px[x, y] = (*bg2, 255)
    for i in range(16):
        px[i, 0] = px[0, i] = (*frame, 255)
        px[i, 15] = px[15, i] = (*frame2, 255)
    # chevrones hacia fuera: < a la izquierda, > a la derecha
    for d in range(4):
        for (x, y) in ((4 - d, 4 + d), (4 - d, 11 - d), (11 + d, 4 + d), (11 + d, 11 - d)):
            px[x, y] = (*glow, 255)
    for (x, y) in ((1, 7), (1, 8), (14, 7), (14, 8)):
        px[x, y] = (*glow, 255)
    # núcleo
    for (x, y) in ((7, 6), (8, 6), (6, 7), (7, 7), (8, 7), (9, 7), (6, 8), (7, 8), (8, 8), (9, 8), (7, 9), (8, 9)):
        px[x, y] = (*core, 255)
    px[7, 7] = (*hi, 255)
    return im


def bench():
    """Mesa de trabajo propia: encimera de tablones, cuerpo de tablas y herramientas colgadas."""
    top, top2, edge = (204, 160, 104), (178, 134, 82), (96, 62, 34)
    plank, plank2, seam, leg = (158, 110, 64), (176, 126, 76), (110, 74, 42), (92, 60, 32)
    iron, iron2, handle = (176, 180, 188), (120, 124, 132), (62, 38, 20)
    im = Image.new("RGBA", (16, 16), (*plank, 255))
    px = im.load()
    for y in range(16):
        for x in range(16):
            if y < 3:
                px[x, y] = (*(top if (x // 5 + y) % 2 == 0 else top2), 255)
            elif y == 3:
                px[x, y] = (*edge, 255)
            else:
                c = plank if (x // 4) % 2 == 0 else plank2
                if x % 4 == 0:
                    c = seam
                if x in (0, 15):
                    c = leg
                px[x, y] = (*c, 255)
    for x in range(1, 15, 3):                       # vetas de la encimera
        px[x, 1] = (*top2, 255)
    # martillo (izquierda)
    for y in range(6, 13):
        px[4, y] = (*handle, 255)
    for x in range(2, 7):
        px[x, 5] = (*iron, 255)
        px[x, 6] = (*iron2, 255)
    # tenazas (derecha)
    for y in range(5, 13):
        px[10, y] = (*iron2, 255)
        px[12, y] = (*iron2, 255)
    px[11, 9] = (*iron, 255)
    px[10, 5] = px[12, 5] = (*iron, 255)
    # cajón
    for x in range(6, 10):
        px[x, 13] = (*edge, 255)
        px[x, 14] = (*top2, 255)
    px[7, 14] = px[8, 14] = (*iron, 255)
    return im


def slime():
    """Slime propio: cubo verde con manchas, brillo arriba, sombra abajo y núcleo oscuro."""
    import random
    rng = random.Random(5)
    greens = [(120, 210, 96), (132, 222, 106), (110, 196, 88), (144, 230, 120)]
    im = Image.new("RGBA", (16, 16))
    px = im.load()
    for by in range(0, 16, 2):
        for bx in range(0, 16, 2):
            c = rng.choice(greens)
            for y in range(by, by + 2):
                for x in range(bx, bx + 2):
                    px[x, y] = (*c, 255)
    for i in range(16):
        px[i, 0] = px[0, i] = (176, 246, 150, 255)
        px[i, 15] = px[15, i] = (78, 150, 62, 255)
    for x, y in ((3, 3), (4, 3), (3, 4), (11, 5), (6, 10), (12, 11), (9, 2)):   # brillos
        px[x, y] = (196, 255, 176, 255)
    return im


def bedrock():
    """Roca madre propia: grises muy contrastados en manchas horizontales cortas."""
    import random
    rng = random.Random(23)
    greys = [(30, 30, 30), (50, 50, 50), (84, 84, 84), (99, 99, 99), (154, 154, 154)]
    weights = [7, 33, 22, 15, 18]
    im = Image.new("RGBA", (16, 16))
    px = im.load()
    for y in range(16):
        x = 0
        while x < 16:
            run = rng.choice((1, 2, 2, 3, 3, 4))
            c = rng.choices(greys, weights)[0]
            for k in range(run):
                if x + k < 16:
                    px[x + k, y] = (*c, 255)
            x += run
    # algunas manchas de dos filas, como bloques sueltos
    for _ in range(10):
        x, y = rng.randrange(15), rng.randrange(15)
        c = px[x, y]
        px[x + 1, y] = px[x, y + 1] = px[x + 1, y + 1] = c
    return im


# ---------------------------------------------------------------- dibujos propios
DIRT = [(134, 96, 67), (121, 85, 58), (148, 106, 74), (108, 75, 50), (160, 118, 84)]
GRASS_G = [(98, 162, 56), (112, 180, 64), (86, 142, 48), (128, 198, 76)]


def own_dirt():
    import random
    rng = random.Random(31)
    im = Image.new("RGBA", (16, 16))
    px = im.load()
    for y in range(16):
        x = 0
        while x < 16:
            run = rng.choice((1, 2, 2, 3))
            c = rng.choices(DIRT, [30, 25, 20, 12, 13])[0]
            for k in range(run):
                if x + k < 16:
                    px[x + k, y] = (*c, 255)
            x += run
    for _ in range(5):                                   # piedrecitas
        x, y = rng.randrange(15), rng.randrange(15)
        px[x, y] = (170, 160, 150, 255)
        px[x + 1, y] = (120, 112, 104, 255)
    return im


def own_grass(dirt):
    """Lateral del césped: la misma tierra debajo y hierba que cae en flecos irregulares."""
    import random
    rng = random.Random(41)
    im = dirt.copy()
    px = im.load()
    for x in range(16):
        depth = rng.choice((3, 3, 4, 4, 5, 6))
        for y in range(depth):
            px[x, y] = (*rng.choice(GRASS_G[:3]), 255)
        px[x, 0] = (*rng.choice((GRASS_G[1], GRASS_G[3])), 255)
        px[x, depth] = (*GRASS_G[2], 255)               # sombra bajo el fleco
    return im


def own_block(dark, base, light, shine, edge):
    """Bloque de gema biselado: borde, brillo arriba-izquierda, sombra abajo-derecha y destellos."""
    im = Image.new("RGBA", (16, 16), (*base, 255))
    px = im.load()
    for i in range(16):
        px[i, 0] = px[0, i] = px[i, 15] = px[15, i] = (*edge, 255)
    for i in range(1, 15):
        px[i, 1] = px[1, i] = (*light, 255)
        px[i, 14] = px[14, i] = (*dark, 255)
    for i in range(2, 14):                              # marco interior
        px[i, 2] = px[2, i] = (*shine, 255) if i < 6 else (*light, 255)
        px[i, 13] = px[13, i] = (*dark, 255)
    for k in range(4, 10):                              # destellos diagonales
        px[k, 13 - k + 1 - 4 + 4] = (*light, 255)
    for k in range(6, 13):
        px[k, 18 - k] = (*light, 255)
    for (x, y) in ((4, 4), (5, 4), (4, 5), (11, 9), (10, 11)):
        px[x, y] = (*shine, 255)
    return im


# pico propio: cabezal en L simétrico respecto al mango (se dibuja la barra de arriba y se refleja
# sobre la diagonal del mango, x + y = 15), fino en las puntas; mango de madera con atadura y remate.
PICK_MATERIALS = {
    # (contorno/sombra, medio, claro, brillo, motas)
    0: ((110, 76, 42), (176, 130, 78), (206, 162, 104), (230, 196, 140), (132, 92, 52)),    # madera
    1: ((70, 70, 74), (112, 112, 116), (146, 146, 150), (178, 178, 182), (86, 86, 90)),     # piedra
    2: ((150, 152, 162), (208, 210, 218), (236, 238, 244), (255, 255, 255), None),           # hierro
    3: ((0, 140, 152), (40, 216, 208), (150, 252, 240), (226, 255, 250), None),             # diamante
    4: ((40, 34, 44), (72, 62, 76), (104, 92, 108), (150, 130, 162), (56, 48, 60)),          # netherita
}


def _mirror(x, y):
    return 15 - y, 15 - x


def own_pickaxe(tier):
    shadow, mid, light, shine, speck = PICK_MATERIALS[tier]
    im = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    px = im.load()

    def put(x, y, c):
        px[x, y] = (*c, 255)

    # mango de 3 píxeles en diagonal (claro, medio, oscuro), con tiras de cuero y remate
    wl, wm, wd, wcap = (160, 116, 70), (128, 90, 54), (92, 62, 34), (60, 40, 22)
    for x in range(0, 11):
        y = 15 - x
        put(x, y, wm)
        if y - 1 >= 0:
            put(x, y - 1, wl) if x > 0 else None
        if x + 1 < 16:
            put(x + 1, y, wd)
    for x in (3, 6):
        put(x, 15 - x, (196, 152, 98))
        put(x + 1, 15 - x, (156, 114, 66))
        put(x, 14 - x, (214, 176, 120))
    put(0, 15, wcap)
    put(1, 15, wcap)
    put(0, 14, wcap)
    # cabezal: barra de arriba (y su reflejo, la barra derecha) + bloque central sobre el mango
    def both(x, y, top, side):
        put(x, y, top)
        mx, my = _mirror(x, y)
        put(mx, my, side)
    def lerp(c1, c2, t):
        return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))
    # fila exterior: degradado de brillo (centro) a sombra (punta)
    for x in range(5, 12):
        t = (11 - x) / 6
        both(x, 1, lerp(light, mid, t * 0.8), lerp(shadow, mid, 0.25 * (1 - t)))
    # fila interior: algo más corta; se oscurece hacia la punta
    for x in range(8, 12):
        t = (11 - x) / 3
        both(x, 2, lerp(mid, shadow, t * 0.6), lerp(mid, shadow, 0.2 + t * 0.4))
    # punta curvada hacia el mango
    both(4, 1, lerp(mid, shadow, 0.5), shadow)
    for x in range(7, 10):                     # brillo cerca del centro
        put(x, 1, shine)
    for x in range(10, 13):                    # bloque central, más estrecho (simétrico: [10..12] x [3..5])
        for y in range(3, 6):
            put(x, y, mid)
    for (x, y) in ((10, 3), (11, 3)):           # brillo
        put(x, y, shine)
    for (x, y) in ((12, 5), (12, 4)):
        put(x, y, shadow)
    # el mango atraviesa el cabezal (2 píxeles) y asoma por la esquina
    for x in range(10, 15):
        y = 15 - x
        put(x, y, wm)
        if x + 1 <= 14 and y > 1:
            put(x + 1, y, wd)
    put(14, 1, wcap)
    # collar: abrazadera oscura del material alrededor del mango, en el centro del cabezal
    collar = lerp(shadow, (0, 0, 0), 0.25)
    for (x, y) in ((11, 3), (12, 4), (10, 4), (11, 5), (13, 3), (12, 2), (9, 5), (10, 6)):
        put(x, y, collar)
    put(11, 3, lerp(shadow, light, 0.5))        # brillo del collar
    put(12, 2, lerp(shadow, light, 0.35))
    if speck:
        for (x, y) in ((8, 2), (5, 1), (13, 8), (14, 10)):
            put(x, y, speck)
    return im


def own_cracks(stages=10):
    """Grietas propias, centradas: fisuras cortas desde el centro con zigzag y ramas, esquirlas sueltas alrededor
    y opacidad variable (más marcado en el centro, tenue en las puntas). Cada fase revela más."""
    import math
    import random
    rng = random.Random(77)
    pts = {}                                   # (x, y) -> (momento de aparición, opacidad)
    min_r = [0.0]                              # en la oleada final no se dibuja cerca del centro

    def add(x, y, t, a):
        if (x - 7) ** 2 + (y - 7) ** 2 < min_r[0] ** 2:
            return
        if 0 <= x < 16 and 0 <= y < 16 and ((x, y) not in pts or pts[(x, y)][0] > t):
            pts[(x, y)] = (t, a)

    def ray(x, y, ang, length, depth, t0):
        fx, fy = x + 0.5, y + 0.5
        for step in range(length):
            ang += rng.uniform(-0.5, 0.5)
            fx += math.cos(ang)
            fy += math.sin(ang)
            cx, cy = int(fx), int(fy)
            fade = step / max(1, length)
            add(cx, cy, t0 + step * (1.4 + depth), int(225 - 110 * fade - 40 * depth + rng.randint(-15, 15)))
            if depth == 0 and step >= 1 and rng.random() < 0.3:
                ray(cx, cy, ang + rng.choice((-1, 1)) * rng.uniform(0.8, 1.3), rng.randint(1, 3), 1,
                    t0 + step + 4)

    n_rays = 5
    base = rng.uniform(0, math.tau)
    for k in range(n_rays):
        ang = base + k * math.tau / n_rays + rng.uniform(-0.15, 0.15)
        ray(7, 7, ang, rng.randint(4, 6), 0, rng.uniform(0, 1.5))
    add(7, 7, 0, 235)                                       # núcleo
    # fases finales: las fisuras siguen hasta casi los bordes (aparecen tarde)
    late = max(t for t, _ in pts.values()) + 2
    min_r[0] = 4.5
    for k in range(n_rays):
        ang = base + k * math.tau / n_rays + rng.uniform(-0.2, 0.2)
        ray(7, 7, ang, rng.randint(8, 10), 0, late)
    for _ in range(3):                                      # alguna fisura nueva desde el borde de las viejas
        ang = rng.uniform(0, math.tau)
        sx, sy = 7 + int(4 * math.cos(ang)), 7 + int(4 * math.sin(ang))
        ray(sx, sy, ang + rng.uniform(-0.6, 0.6), rng.randint(3, 5), 1, late + 3)
    # esquirlas sueltas cerca de las fisuras
    crack = list(pts.items())
    for _ in range(34):
        (x, y), (t, a) = rng.choice(crack)
        dx, dy = rng.choice(((2, 0), (-2, 0), (0, 2), (0, -2), (2, 2), (-2, 2), (2, -2), (-2, -2),
                             (3, 1), (-1, 3), (1, -3), (-3, -1)))
        add(x + dx, y + dy, t + rng.uniform(1, 6), rng.randint(70, 170))
    min_r[0] = 3.5
    last = max(t for t, _ in pts.values())
    for _ in range(22):                                     # esquirlas por todo el bloque al final
        add(rng.randrange(1, 15), rng.randrange(1, 15), last * rng.uniform(0.75, 1.0), rng.randint(45, 130))
    order = sorted(pts.items(), key=lambda kv: kv[1][0])
    out = []
    for k in range(stages):
        n = max(4, int(len(order) * (k + 1) / stages))
        im = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
        px = im.load()
        shown = dict(order[:n])
        for (x, y), (_, a) in shown.items():
            px[x, y] = (20, 18, 22, max(40, min(240, a)))
        for (x, y), (_, a) in shown.items():                  # filo claro (relieve) en las fisuras marcadas
            ex, ey = x + 1, y + 1
            if a > 150 and ex < 16 and ey < 16 and (ex, ey) not in shown:
                px[ex, ey] = (255, 255, 255, 38)
        out.append(im)
    return out


def own_tall_grass():
    """Hierba alta propia: briznas de varios verdes, de distintas alturas y algo inclinadas."""
    greens = [(84, 140, 46), (102, 164, 56), (122, 188, 70), (146, 206, 92)]
    blades = [(2, 9, 1), (4, 13, -1), (6, 7, 0), (8, 14, 1), (10, 10, -1), (12, 12, 1), (13, 6, 0)]
    im = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    px = im.load()
    for i, (x0, h, lean) in enumerate(blades):
        for k in range(h):
            y = 15 - k
            x = x0 + (lean * k) // 5
            if 0 <= x < 16:
                c = greens[min(3, k * 4 // max(1, h))] if k < h - 1 else greens[3]
                px[x, y] = (*c, 255)
                if k < h // 2 and 0 <= x + 1 < 16 and px[x + 1, y][3] == 0:
                    px[x + 1, y] = (*greens[0], 255)
    return im


def pickaxe_from_ref(path):
    """Pico del autor (imagen grande con fondo transparente, dibujo de 16x16) -> textura de 16x16."""
    import numpy as np
    a = np.asarray(Image.open(path).convert("RGBA")).astype(int)
    fg = a[..., 3] > 128
    ys, xs = np.where(fg)
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    cw, ch = (x1 - x0) / 16, (y1 - y0) / 16
    out = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    for gy in range(16):
        for gx in range(16):
            cx, cy = int(x0 + (gx + 0.5) * cw), int(y0 + (gy + 0.5) * ch)
            if fg[cy, cx]:
                col = np.median(a[cy - 3:cy + 4, cx - 3:cx + 4, :3].reshape(-1, 3), axis=0).astype(int)
                out.putpixel((gx, gy), (*map(int, col), 255))
    return out


def from_grid(src):
    """Imagen de referencia en cuadrícula de 16x16 (cualquier tamaño) -> textura de 16x16."""
    im = Image.open(src).convert("RGB")
    s = im.width / 16
    out = Image.new("RGBA", (16, 16))
    for y in range(16):
        for x in range(16):
            out.putpixel((x, y), (*im.getpixel((int((x + 0.5) * s), int((y + 0.5) * im.height / 16))), 255))
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    save = lambda img, name: img.save(os.path.join(OUT, name + ".png"))  # noqa: E731
    dirt = own_dirt()
    save(dirt, "dirt")
    save(own_grass(dirt), "grass")
    save(own_tall_grass(), "tall_grass")
    save(bedrock(), "bedrock")
    save(own_block((16, 150, 160), (60, 226, 214), (160, 255, 240), (236, 255, 252), (8, 104, 116)),
         "diamond_block")
    save(own_block((40, 176, 92), (108, 236, 150), (190, 255, 208), (240, 255, 244), (22, 120, 60)),
         "emerald_block")
    for k, im in enumerate(own_cracks()):
        save(im, f"crack_{k}")
    for tier in range(5):
        ref = os.path.join(ROOT, "fotos referencias", f"pico_{tier}.webp")
        if os.path.exists(ref):
            save(pickaxe_from_ref(ref), f"pickaxe_{tier}")
        elif not os.path.exists(os.path.join(OUT, f"pickaxe_{tier}.png")):   # sin la referencia, se conserva el PNG
            save(own_pickaxe(tier), f"pickaxe_{tier}")
    save(tnt(), "tnt")
    save(arrow_block(), "arrow")
    save(bench(), "bench")
    save(slime(), "slime")
    print("assets en", OUT)


if __name__ == "__main__":
    main()
