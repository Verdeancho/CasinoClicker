"""Genera las texturas de piedra y minerales (16x16) del Pico Minero, al estilo de la referencia:
piedra de grises en manchas horizontales cortas y vetas de mineral en tres tonos.

    .venv\\Scripts\\python tools\\make_ores.py
"""
import os
import random

from PIL import Image

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "casino", "assets", "pickaxe")
GREYS = [(100, 100, 100), (108, 108, 108), (116, 116, 116), (124, 124, 124), (132, 132, 132), (140, 140, 140)]
DEEP = [(54, 54, 62), (60, 60, 68), (66, 66, 74), (72, 72, 80), (78, 78, 86), (84, 84, 92)]
# mineral: (oscuro, medio, claro)
ORES = {
    "coal": ((24, 24, 26), (44, 44, 48), (70, 70, 76)),
    "copper": ((150, 70, 38), (214, 112, 64), (244, 170, 120)),
    "iron": ((168, 128, 98), (210, 170, 140), (236, 214, 196)),
    "redstone": ((190, 0, 0), (255, 34, 34), (255, 140, 120)),
    "gold": ((196, 142, 16), (250, 210, 40), (255, 244, 150)),
    "lapis": ((20, 56, 160), (40, 92, 222), (116, 156, 255)),
    "diamond": ((20, 226, 236), (110, 255, 255), (214, 255, 255)),
    "emerald": ((0, 170, 66), (40, 236, 104), (170, 255, 200)),
}
# formas de las vetas (casillas relativas)
SHAPES = [
    [(0, 0), (1, 0), (0, 1), (1, 1), (2, 1)],
    [(1, 0), (0, 1), (1, 1), (2, 1), (1, 2)],
    [(0, 0), (1, 0), (1, 1), (2, 1), (2, 2)],
    [(0, 0), (1, 0), (2, 0), (1, 1)],
    [(0, 0), (1, 1), (2, 1), (1, 0)],
    [(0, 0), (0, 1), (1, 1)],
    [(0, 0), (1, 0)],
]


def stone(rng, greys):
    img = [[None] * 16 for _ in range(16)]
    for y in range(16):
        x = 0
        while x < 16:
            run = rng.choice((1, 2, 2, 3))
            col = rng.choice(greys)
            for k in range(run):
                if x + k < 16:
                    img[y][x + k] = col
            x += run
    return img


def ore(rng, base, pal, n_veins=11, specks=8):
    img = [row[:] for row in base]
    used = set()
    placed = 0
    tries = 0
    while placed < n_veins and tries < 200:
        tries += 1
        shape = rng.choice(SHAPES[:5] if placed < 3 else SHAPES)
        ox, oy = rng.randrange(1, 13), rng.randrange(1, 13)
        cells = [(ox + dx, oy + dy) for dx, dy in shape]
        if any(not (0 <= x < 16 and 0 <= y < 16) for x, y in cells):
            continue
        near = {(x + i, y + j) for x, y in cells for i in (-1, 0, 1) for j in (-1, 0, 1)}
        if near & used:
            continue
        used |= set(cells)
        for x, y in cells:
            # arriba a la izquierda, más claro; abajo a la derecha, más oscuro
            k = (x - ox) + (y - oy)
            img[y][x] = pal[2] if k == 0 else (pal[1] if k <= 2 and rng.random() < 0.7 else pal[0])
        placed += 1
    # motas sueltas de mineral
    for _ in range(specks * 10):
        if specks <= 0:
            break
        x, y = rng.randrange(16), rng.randrange(16)
        near = {(x + i, y + j) for i in (-1, 0, 1) for j in (-1, 0, 1)}
        if near & used:
            continue
        used.add((x, y))
        img[y][x] = rng.choice((pal[1], pal[2]))
        specks -= 1
    return img


def save(img, name):
    im = Image.new("RGBA", (16, 16))
    for y in range(16):
        for x in range(16):
            im.putpixel((x, y), (*img[y][x], 255))
    im.save(os.path.join(OUT, name + ".png"))


def main():
    os.makedirs(OUT, exist_ok=True)
    rng = random.Random(7)
    base = stone(rng, GREYS)
    save(base, "stone")
    deep = stone(random.Random(11), DEEP)
    save(deep, "deep_stone")
    for i, (name, pal) in enumerate(ORES.items()):
        save(ore(random.Random(100 + i), base, pal), name + "_ore")
        save(ore(random.Random(200 + i), deep, pal), "deep_" + name + "_ore")
    print("texturas en", OUT)


if __name__ == "__main__":
    main()
