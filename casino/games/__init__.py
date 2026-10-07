"""Registro de juegos. Se importan bajo demanda."""
import importlib

_MODULES = {
    "coinflip": ("coinflip", "CoinFlip"), "dice": ("dice", "Dice"), "slots": ("slots", "Slots"),
    "scratch": ("scratch", "Scratch"), "roulette": ("roulette", "Roulette"), "blackjack": ("blackjack", "Blackjack"),
    "hilo": ("hilo", "HiLo"), "crash": ("crash", "Crash"), "mines": ("mines", "Mines"), "plinko": ("plinko", "Plinko"),
    "wheel": ("wheel", "Wheel"), "horses": ("horses", "Horses"), "keno": ("keno", "Keno"),
    "videopoker": ("videopoker", "VideoPoker"), "princess": ("princess", "Princess"),
    "trilero": ("trilero", "Trilero"), "bote": ("bote", "Bote"), "sicbo": ("sicbo", "SicBo"),
    "bingo": ("bingo", "Bingo"), "baccarat": ("baccarat", "Baccarat"), "poker": ("poker", "Poker"),
    "pickaxe": ("pickaxe", "Pickaxe"), "lastbet": ("lastbet", "LastBet"),
}


class _Registry(dict):
    def __missing__(self, gid):
        mod, cls = _MODULES[gid]
        c = getattr(importlib.import_module(f"{__name__}.{mod}"), cls)
        self[gid] = c
        return c


GAME_CLASSES = _Registry()
