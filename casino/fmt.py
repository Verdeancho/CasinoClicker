"""Formato de números y cantidades."""
import math
import re

_SUFFIXES = ["", "K", "M", "B", "T", "Qa", "Qi", "Sx", "Sp", "Oc", "No", "Dc",
             "UDc", "DDc", "TDc", "QaDc", "QiDc", "SxDc", "SpDc", "OcDc", "NoDc", "Vg"]


def fmt_num(x, decimals=2):
    """Número con sufijos (K, M, B...)."""
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "∞"
    neg = x < 0
    x = abs(x)
    if x < 1000:
        if x == int(x) and decimals <= 2 and x >= 100:
            s = f"{x:.0f}"
        else:
            s = f"{x:.{decimals}f}"
    else:
        exp = int(math.log10(x) // 3)
        if exp >= len(_SUFFIXES):
            s = f"{x:.3e}"
        else:
            val = x / (1000 ** exp)
            if val >= 999.995:  # evitar "1000.00K"
                exp += 1
                val /= 1000
            if exp < len(_SUFFIXES):
                s = f"{val:.2f}{_SUFFIXES[exp]}"
            else:
                s = f"{x:.3e}"
    return ("-" if neg else "") + s


def fmt_money(x):
    ax = abs(x)
    if 0 < ax < 0.1:
        dec = 4 if ax < 0.01 else 3
        return f"{'-' if x < 0 else ''}{ax:.{dec}f} €".replace(".", ",")
    if ax < 1000:
        return f"{'-' if x < 0 else ''}{abs(x):,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
    return fmt_num(x) + " €"


def fmt_int(x):
    if abs(x) < 1_000_000:
        return f"{int(x):,}".replace(",", ".")
    return fmt_num(x)


def fmt_time(seconds):
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    m, s = divmod(seconds, 60)
    if m < 60:
        return f"{m}m {s:02d}s"
    h, m = divmod(m, 60)
    if h < 24:
        return f"{h}h {m:02d}m"
    d, h = divmod(h, 24)
    return f"{d}d {h}h"


_PARSE_SUFFIX = {"k": 1e3, "m": 1e6, "b": 1e9, "t": 1e12, "qa": 1e15, "qi": 1e18}


def parse_amount(text):
    """Convierte '1,5k', '2m', '0.25' en float. Devuelve None si no es válido."""
    t = text.strip().lower().replace("€", "").replace(" ", "")
    if not t:
        return None
    t = t.replace(",", ".")
    m = re.fullmatch(r"([0-9]*\.?[0-9]+)(qa|qi|k|m|b|t)?", t)
    if not m:
        return None
    val = float(m.group(1))
    if m.group(2):
        val *= _PARSE_SUFFIX[m.group(2)]
    return val


def _expand(c):
    return "#" + "".join(ch * 2 for ch in c[1:]) if len(c) == 4 else c
