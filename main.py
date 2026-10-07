"""Casino Clicker — clicker de casino hecho con pygame-ce.

Ejecutar:  python main.py   (o doble clic en Jugar.bat)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from casino import state  # noqa: E402
from casino.app import App  # noqa: E402

# en el ejecutable la partida se guarda codificada (para que no se edite a mano); desde el código, en JSON legible
state.ENCODE_SAVES = getattr(sys, "frozen", False) or bool(os.environ.get("CASINO_ENCODE"))


def save_path():
    """Junto al código al jugar desde Python. En el ejecutable empaquetado: %APPDATA%\\CasinoClicker en Windows,
    ~/Library/Application Support/CasinoClicker en macOS y ~/.local/share/CasinoClicker en Linux."""
    if getattr(sys, "frozen", False):
        home = os.path.expanduser("~")
        if sys.platform == "win32":
            root = os.environ.get("APPDATA") or home
        elif sys.platform == "darwin":
            root = os.path.join(home, "Library", "Application Support")
        else:
            root = os.environ.get("XDG_DATA_HOME") or os.path.join(home, ".local", "share")
        base = os.path.join(root, "CasinoClicker")
        os.makedirs(base, exist_ok=True)
        return os.path.join(base, "partida.json")
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "partida.json")


def self_check(out):
    """Abre todos los juegos y pestañas sin ventana y escribe el resultado en `out` (para comprobar las builds)."""
    import tempfile
    import traceback
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    from casino.games import _MODULES
    lines, ok = [], True
    try:
        app = App(os.path.join(tempfile.mkdtemp(), "partida.json"), headless=True)
        for tab in ("casino", "upgrades", "market", "vip", "achievements", "stats"):
            app.tab = tab
            for _ in range(3):
                app.step([], 1 / 60)
        app.tab = "casino"
        for gid in _MODULES:
            try:
                app.open_game(gid)
                for _ in range(5):
                    app.step([], 1 / 60)
                lines.append(f"ok {gid}")
            except Exception:
                ok = False
                lines.append(f"FALLO {gid}\n{traceback.format_exc()}")
    except Exception:
        ok = False
        lines.append(traceback.format_exc())
    lines.append(f"{'OK' if ok else 'FALLO'} {sum(l.startswith('ok ') for l in lines)} juegos")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return 0 if ok else 1


SAVE_PATH = save_path()

if __name__ == "__main__":
    if os.environ.get("CASINO_SELFCHECK"):
        sys.exit(self_check(os.environ["CASINO_SELFCHECK"]))
    App(SAVE_PATH).run()
