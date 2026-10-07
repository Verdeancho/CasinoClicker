"""Definiciones del juego: negocios, juegos, mejoras de tienda, mejoras únicas (oportunidades), hazañas,
ventajas VIP, temas visuales y logros. No depende de pygame (lo usa también el simulador de economía)."""
from dataclasses import dataclass, field
from typing import Callable, Optional

# Retorno máximo al que pueden llegar las apuestas con todas las mejoras (la banca siempre gana)
RTP_CAP = 0.985

# ----------------------------------------------------------------------------
# Negocios (ingresos pasivos)
# ----------------------------------------------------------------------------


@dataclass
class Building:
    id: str
    name: str
    short: str
    color: str
    base_cost: float
    base_income: float
    desc: str


BUILDINGS = [
    Building("hucha", "Hucha de cerdito", "Hucha", "#f78fb3", 0.15, 0.001, "Alguien echa monedas de vez en cuando."),
    Building("chicles", "Máquina de chicles", "Chicles", "#ff6b81", 1.0, 0.01, "Un céntimo, un chicle. Negocio redondo."),
    Building("limonada", "Puesto de limonada", "Limonada", "#feca57", 11, 0.08, "Limonada casera con margen del 900%."),
    Building("loteria", "Quiosco de lotería", "Lotería", "#48dbfb", 120, 0.47, "Vendes sueños a 2 € el boleto."),
    Building("bar", "Bar con tragaperras", "Bar", "#1dd1a1", 1_300, 2.6, "Café, carajillo y una maquinita al fondo."),
    Building("bingo", "Salón de bingo", "Bingo", "#ff9f43", 14_000, 14, "¡Línea! ¡Bingo! ¡Caja!"),
    Building("clandestino", "Casino clandestino", "Clandestino", "#a29bfe", 200_000, 78,
             "Contraseña en la puerta y humo dentro."),
    Building("barco", "Casino flotante", "Flotante", "#54a0ff", 3_300_000, 440,
             "Aguas internacionales, leyes internacionales."),
    Building("vegas", "Hotel-Casino en Las Vegas", "Las Vegas", "#f5c542", 51_000_000, 2_600,
             "Luces de neón y buffet libre."),
    Building("offshore", "Banco offshore", "Offshore", "#2ecc71", 750_000_000, 16_000,
             "Nadie pregunta de dónde viene el dinero."),
    Building("cripto", "Cripto-exchange", "Cripto", "#f39c12", 10e9, 100_000, "Tokens respaldados por pura fe."),
    Building("petrolera", "Petrolera", "Petrolera", "#576574", 140e9, 650_000, "Oro negro para financiar mesas de oro."),
    Building("orbital", "Casino orbital", "Orbital", "#00d2d3", 1.7e12, 4.3e6, "Ruleta en gravedad cero."),
    Building("dimensional", "Casino interdimensional", "Dimensional", "#e056fd", 21e12, 29e6,
             "Apuestas contra tus otros yos."),
    Building("multiverso", "Multiverso de apuestas", "Multiverso", "#ff4757", 260e12, 210e6,
             "La banca siempre gana. En todos los universos."),
]
BUILDING_BY_ID = {b.id: b for b in BUILDINGS}
BUILDING_COST_GROWTH = 1.15

# Hitos de cada negocio: (cantidad necesaria, nombre). Cada hito comprado duplica su producción.
# Cuestan TIER_COST_K veces lo que vale la unidad número `cantidad` de ese negocio.
BUILDING_TIERS = [(1, "Optimización"), (5, "Franquicia"), (25, "Automatización"), (50, "Monopolio"),
                  (100, "Singularidad"), (150, "Trascendencia")]
TIER_COST_K = 6.0


def tier_cost(b, n):
    return b.base_cost * BUILDING_COST_GROWTH ** n * TIER_COST_K


# ----------------------------------------------------------------------------
# Juegos de casino
# ----------------------------------------------------------------------------


@dataclass
class Variant:
    id: str
    name: str
    cost_mult: float          # coste = coste de desbloqueo del juego * cost_mult (0 = gratis)
    desc: str
    rtp: Optional[float] = None


@dataclass
class GameDef:
    id: str
    name: str
    icon: str
    color: str
    unlock_cost: float
    min_bet: float
    desc: str
    rtp: Optional[float]      # retorno teórico con juego óptimo (None = juego de habilidad, sin bonus)
    variants: list = field(default_factory=list)


BOTE_PAY = {"d6": 5.7, "d8": 7.6, "d12": 11.5, "d20": 19.0}

GAMES = [
    GameDef("coinflip", "Cara o Cruz", "◑", "#f5c542", 0.25, 0.01, "50/50. Paga x1,96. Lo más simple del mundo.", 0.98),
    GameDef("dice", "Dados", "⚄", "#3498db", 2, 0.01, "Elige tu probabilidad. Cuanto más arriesgas, más pagas.", 0.98),
    GameDef("trilero", "El Trilero", "▼", "#d35400", 6, 0.01,
            "Sigue la bolita. Cada ronda hay más vasos y el trilero es más rápido.", 0.97),
    GameDef("slots", "Tragaperras", "7", "#e74c3c", 10, 0.01, "Tres rodillos, cinco líneas, un sueño.", 0.966),
    GameDef("bote", "El Bote", "⚅", "#27ae60", 25, 0.05,
            "Reparte fichas entre las caras del dado. La cara ganadora multiplica.", 0.95, [
                Variant("d6", "Dado de 6", 0, "6 casillas · la ganadora paga x5,7", 5.7 / 6),
                Variant("d8", "Octaedro", 4, "8 casillas · la ganadora paga x7,6", 7.6 / 8),
                Variant("d12", "Dodecaedro", 20, "12 casillas · la ganadora paga x11,5", 11.5 / 12),
                Variant("d20", "Icosaedro", 120, "20 casillas · la ganadora paga x19", 19 / 20),
            ]),
    GameDef("scratch", "Rasca y Gana", "▦", "#bdc3c7", 40, 0.05, "Rasca con el ratón. Tres iguales = premio.", 0.95),
    GameDef("roulette", "Ruleta", "◎", "#c0392b", 150, 0.05, "Ruleta europea. Apuesta en el tapete y gira.", 0.973),
    GameDef("sicbo", "Sic Bo", "⚂", "#8e44ad", 400, 0.10, "Tres dados en una cúpula. Apuesta a totales y combinaciones.",
            0.972),
    GameDef("blackjack", "Blackjack", "♠", "#5d8aa8", 600, 0.10, "Llega a 21 sin pasarte. BJ paga 3:2.", 0.995),
    GameDef("hilo", "Mayor o Menor", "⇅", "#16a085", 2_500, 0.10, "Adivina si la siguiente carta es mayor o menor.", 0.97),
    GameDef("baccarat", "Baccarat", "♦", "#b03a2e", 6_000, 0.25, "Punto o Banca. El clásico de los grandes casinos.",
            0.986, [
                Variant("punto", "Punto y Banca", 0, "Baccarat clásico: Punto x2, Banca x1,95, Empate x9", 0.986),
                Variant("dragon", "Dragón y Tigre", 3, "Una carta cada uno. La más alta gana. x2", 0.963),
                Variant("war", "Guerra de casino", 8, "Tu carta contra la del crupier. Empate: ¡guerra!", 0.971),
            ]),
    GameDef("crash", "Crash", "↗", "#e67e22", 10_000, 0.25, "El multiplicador sube... retírate antes de que explote.", 0.97),
    GameDef("bingo", "Bingo", "◉", "#f39c12", 25_000, 0.50, "Compra cartones, gira el bombo y canta línea y bingo.", 0.95),
    GameDef("mines", "Minas", "✸", "#8e44ad", 50_000, 0.25, "Destapa casillas sin tocar una mina.", 0.97),
    GameDef("plinko", "Plinko", "▼", "#e84393", 250_000, 0.50, "Suelta bolas entre clavos y reza.", 0.99),
    GameDef("princess", "Princesa Estelar", "★", "#fd79a8", 600_000, 0.20,
            "6x5, paga con 8+ iguales en cualquier lugar, cascadas y orbes multiplicadores.", 0.965),
    GameDef("wheel", "Rueda de la Fortuna", "✺", "#fd79a8", 1_000_000, 1, "Gira la rueda. Hasta x50.", 0.975),
    GameDef("pickaxe", "Pico Minero", "⛏", "#8d6e63", 2_500_000, 1,
            "Compra tiradas por paquetes y suelta el pico: pica menas, mejora con mesas de trabajo y explota TNT.",
            0.955),
    GameDef("horses", "Carreras de Caballos", "♞", "#a0522d", 5_000_000, 1, "Seis caballos, una meta. ¿Quién ganará?",
            0.95),
    GameDef("keno", "Keno", "▣", "#0984e3", 25_000_000, 5, "Elige hasta 10 números de 40. Se sortean 10.", 0.95),
    GameDef("poker", "Póker", "♣", "#2d6a4f", 60_000_000, 5, "Siéntate con jugadores virtuales. Elige la modalidad.", None, [
        Variant("holdem", "Texas Hold'em", 0, "2 cartas propias y 5 comunitarias. Límite fijo."),
        Variant("omaha", "Omaha", 3, "4 cartas propias: usas exactamente 2 con 3 de la mesa."),
        Variant("stud7", "Seven-Card Stud", 8, "7 cartas, 4 a la vista. Sin cartas comunitarias."),
        Variant("draw5", "Five-Card Draw", 2, "5 cartas tapadas, un descarte y a por la mejor mano."),
        Variant("caribbean", "Caribbean Stud", 5, "Contra la banca: ante, sube o retírate. Pagos por mano.", 0.955),
    ]),
    GameDef("videopoker", "Video Póker", "♦", "#6c5ce7", 100_000_000, 10, "Jacks or Better. Guarda cartas y cambia.",
            0.995),
]
LASTBET = GameDef("lastbet", "La Última Apuesta", "?", "#c0392b", 0, 0.01, "Solo para los que se lo juegan todo.", None)
GAME_BY_ID = {g.id: g for g in GAMES + [LASTBET]}
POKER_RAKE_EDGE = 0.05      # para la experiencia: lo que "se espera" que pierdas en el póker

# ----------------------------------------------------------------------------
# Ventajas de cada juego (chivatadas). Se desbloquean con hazañas; la fiabilidad nunca se muestra.
# Recarga: 60 min, y el nivel de jugador la baja hasta 30 min.
# ----------------------------------------------------------------------------
HINTS = {
    "coinflip": ("Chivatazo", "Alguien te susurra el próximo resultado. Suele acertar."),
    "dice": ("Dados cargados", "Notas hacia dónde va a caer la próxima tirada."),
    "trilero": ("Vaso manchado", "El vaso de la bola lleva una mancha antes de que empiece a moverlos."),
    "hilo": ("Vistazo", "Ves de reojo si la siguiente carta es alta o baja."),
    "crash": ("Presentimiento", "Intuyes si el cohete pasará de x2."),
    "mines": ("Radar", "El radar te marca una mina al empezar la partida."),
    "horses": ("Soplo del jockey", "Un jockey te cuenta qué caballo está en forma."),
    "bote": ("Dado trucado", "Sabes qué cara tiende a salir en la próxima tirada."),
    "poker": ("Lectura de rivales", "Detectas si un rival tiene buena mano o va de farol."),
    "sicbo": ("Ojo de la cúpula", "Ves uno de los tres dados antes de agitar."),
    "baccarat": ("Carta marcada", "Sabes cuál será la primera carta de Punto (o la tuya)."),
    "pickaxe": ("Carga de TNT", "Durante una ronda, pulsa el botón y la TNT explota justo donde está el pico."),
}
HINT_COOLDOWN_MAX = 60 * 60
HINT_COOLDOWN_MIN = 30 * 60

# Ventajas especiales (también con recarga, cada una con su propia clave)
SPECIAL_COOLDOWNS = {"trilero_monty": 60 * 60, "trilero_peek": 60 * 60, "bj_peek": 60 * 60,
                     "princess_orbs": 90 * 60, "roulette_dozen": 60 * 60, "pick_bench": 60 * 60,
                     "pick_netherite": 2 * 60 * 60}
FEAT_SPECIALS = ("trilero_monty", "pick_bench")   # ventajas con recarga propia que se ganan con una hazaña

# ----------------------------------------------------------------------------
# Mejoras de la tienda
# ----------------------------------------------------------------------------


@dataclass
class Upgrade:
    id: str
    name: str
    desc: str
    category: str          # click | casino | business | golden
    base_cost: float
    growth: float = 1.0
    max_level: int = 1
    requires: Optional[Callable] = None
    game: Optional[str] = None       # mejoras propias de un juego (se ven dentro del juego)
    feat: Optional[str] = None       # si la tiene, no se compra: se gana con esa hazaña
    plays: Optional[list] = None     # jugadas necesarias para cada nivel (por juego o globales)

    def cost(self, level):
        return self.base_cost * (self.growth ** level)


def _has_building(bid, n):
    return lambda s: s.buildings.get(bid, 0) >= n


UPGRADES = []

# ---- Clicker ----
UPGRADES += [
    Upgrade("click_power", "Fuerza de dedo", "+1 céntimo base por clic (por nivel).", "click", 0.10, 1.45, 100),
    Upgrade("synergy", "Clic sinérgico", "Cada clic MANUAL suma un 1% de tus €/s (por nivel).",
            "click", 40, 4.0, 10, requires=lambda s: s.income_per_sec() > 0),
    Upgrade("crit_chance", "Golpe crítico", "+2% de probabilidad de crítico (por nivel).", "click", 2, 2.4, 20),
    Upgrade("crit_mult", "Crítico devastador", "Los críticos multiplican +2x más (base x5).", "click", 20, 3.0, 10,
            requires=lambda s: s.upgrades.get("crit_chance", 0) > 0),
    Upgrade("autoclick", "Auto-clicker", "+1 clic automático por segundo (por nivel).", "click", 5, 1.6, 30),
    Upgrade("combo", "Combo máximo", "+25 al combo máximo (cada punto de combo = +1% al clic).", "click", 10, 6.0, 4,
            requires=lambda s: s.stats["clicks"] >= 150),
]

# ---- Casino (generales) ----
LUCK_PLAYS = [int(20 * 1.55 ** i) for i in range(15)]
UPGRADES += [
    Upgrade("luck", "Suerte", "+1% a los premios de todas las apuestas (por nivel).",
            "casino", 20, 2.8, 15, requires=lambda s: len(s.games_unlocked) > 0, plays=LUCK_PLAYS),
]

# ---- Casino (propias de cada juego) ----
UPGRADES += [
    # se compran
    Upgrade("slots_jackpot", "Bote progresivo", "El 1% de cada apuesta del casino va a un bote. Tres ★ en la "
                                                "línea central se lo llevan.", "casino", 4_000, game="slots"),
    Upgrade("hilo_auto", "Retirada automática", "Retírate solo al alcanzar el multiplicador que elijas.", "casino",
            30_000, game="hilo"),
    Upgrade("crash_auto", "Auto-retiro", "Fija un multiplicador de retirada automática y repite rondas.", "casino",
            40_000, game="crash"),
    Upgrade("mines_detector", "Detector de metales", "Al empezar se revela una casilla segura (el pago se recalcula).",
            "casino", 400_000, game="mines"),
    Upgrade("horses_place", "Apuesta a colocado", "Puedes apostar a que tu caballo queda entre los dos primeros.",
            "casino", 20e6, game="horses"),
    Upgrade("trilero_slow", "Ojo de halcón", "El trilero mueve los vasos un 15% más despacio (por nivel).", "casino",
            30, 6.0, 3, game="trilero"),
    # se ganan con hazañas
    Upgrade("slots_wild", "Comodín", "Añade el símbolo WILD (la tabla de pagos se ajusta).", "casino", 0,
            game="slots", feat="slots_777"),
    Upgrade("scratch_gold", "Boleto dorado", "Boletos de 4x4: más casillas y más emoción.", "casino", 0,
            game="scratch", feat="scratch_top"),
    Upgrade("roulette_partage", "La Partage", "Si sale 0, recuperas la mitad de las apuestas simples.", "casino", 0,
            game="roulette", feat="roulette_straight"),
    Upgrade("bj_counter", "Contador de cartas", "Muestra la cuenta Hi-Lo y la jugada óptima.", "casino", 0,
            game="blackjack", feat="bj_streak8"),
    Upgrade("bj_insurance", "Seguro", "Si el crupier enseña un As, puedes asegurar media apuesta: paga 2:1 si "
                                      "tiene blackjack. Con la cuenta alta, merece la pena.", "casino", 0,
            game="blackjack", feat="bj_split2"),
    Upgrade("plinko_rain", "Lluvia de bolas", "Botón para soltar 10 bolas de golpe.", "casino", 0,
            game="plinko", feat="plinko_edge"),
    Upgrade("wheel_bonus", "Segmento dorado", "En cada giro, un segmento al azar se vuelve dorado y paga el doble.",
            "casino", 0, game="wheel", feat="wheel_top"),
    Upgrade("keno_extra", "Bola extra", "Se sortean 11 números en lugar de 10 (tabla de pagos ajustada).",
            "casino", 0, game="keno", feat="keno_8"),
    Upgrade("vp_double", "Doble o nada", "Tras ganar, puedes arriesgar el premio a doble o nada.", "casino", 0,
            game="videopoker", feat="vp_sflush"),
    Upgrade("princess_ante", "Apuesta extra", "Modo ante: +25% de apuesta y bastante más probabilidad de "
                                              "tiradas gratis.", "casino", 0, game="princess", feat="princess_100x"),
    Upgrade("bingo_cards", "Cartones extra", "Puedes jugar hasta 4 cartones a la vez.", "casino", 0,
            max_level=2, game="bingo", feat="bingo_fast"),
    Upgrade("pick_bench", "Yunque", "Una vez por hora, durante una ronda, sacas un yunque: repara el pico "
                                    "entero esté donde esté.", "casino", 0,
            game="pickaxe", feat="pick_deep"),
    Upgrade("trilero_monty", "El trilero enseña uno", "Señala un vaso y el trilero levanta otro vacío antes de que "
                                                      "elijas. ¿Cambias o te quedas?", "casino", 0,
            game="trilero", feat="trilero_9"),
]
HINT_FEATS = {"coinflip": "coin_ride7", "dice": "dice_sniper3", "trilero": "trilero_5", "hilo": "hilo_10",
              "crash": "crash_50", "mines": "mines_clear10", "horses": "horses_underdog", "bote": "bote_d20_3",
              "poker": "poker_bluff", "sicbo": "sicbo_triple", "baccarat": "baccarat_3ties",
              "pickaxe": "pick_tnt"}
for _gid, (_name, _desc) in HINTS.items():
    UPGRADES.append(Upgrade(f"hint_{_gid}", _name, _desc + " Se recarga con el tiempo.", "casino", 0,
                            game=_gid, feat=HINT_FEATS[_gid]))
MASTERY_PLAYS = [30, 100, 300, 800, 2000]
for _g in GAMES:
    if _g.rtp is not None or _g.id == "poker":
        UPGRADES.append(Upgrade(f"mastery_{_g.id}", "Maestría", "+2% a los premios de este juego (por nivel).",
                                "casino", max(1.0, _g.unlock_cost * 2), 4.0, 5, game=_g.id, plays=MASTERY_PLAYS))

# ---- Negocios ----
UPGRADES += [
    Upgrade("discount", "Contactos en el ayuntamiento", "Negocios un 4% más baratos (por nivel).", "business",
            500, 12.0, 5, requires=lambda s: s.total_buildings() >= 25),
]
for _b in BUILDINGS:
    for _i, (_n, _tname) in enumerate(BUILDING_TIERS):
        UPGRADES.append(Upgrade(f"b_{_b.id}_{_i}", f"{_b.short}: {_tname}",
                                f"{_b.name} produce el doble. (Hito: {_n})", "business",
                                tier_cost(_b, _n), requires=_has_building(_b.id, _n)))

# ---- Moneda dorada ----
UPGRADES += [
    Upgrade("gold_freq", "Trébol de cuatro hojas", "Las monedas doradas aparecen un 15% más a menudo.", "golden",
            300, 8.0, 5, requires=lambda s: s.stats["golden_clicked"] >= 1),
    Upgrade("gold_dur", "Herradura", "Los premios de las monedas doradas son un 20% mayores.", "golden",
            1_000, 8.0, 5, requires=lambda s: s.stats["golden_clicked"] >= 3),
]

UPGRADE_BY_ID = {u.id: u for u in UPGRADES}
CATEGORY_NAMES = {"click": "Clicker", "casino": "Casino", "business": "Negocios", "golden": "Suerte"}

# ----------------------------------------------------------------------------
# Hazañas: logros dentro de cada juego que regalan ventajas
# ----------------------------------------------------------------------------


@dataclass
class Feat:
    id: str            # bandera en state.flags
    game: str
    name: str
    desc: str
    reward: str        # id de la mejora que regala


FEATS = [
    Feat("coin_ride7", "coinflip", "Doble o nada x7", "Gana 7 tiradas seguidas apostando cada vez todo lo que "
                                                     "ganaste en la anterior.", "hint_coinflip"),
    Feat("dice_sniper3", "dice", "Francotirador", "Gana 3 tiradas seguidas con menos de un 10% de probabilidad.",
         "hint_dice"),
    Feat("trilero_5", "trilero", "Ojo rápido", "Supera la ronda 5 del trilero sin retirarte.", "hint_trilero"),
    Feat("trilero_9", "trilero", "Más rápido que el trilero", "Gana la última ronda (10 vasos).", "trilero_monty"),
    Feat("slots_777", "slots", "¡Siete, siete, siete!", "Consigue tres 7 en una línea.", "slots_wild"),
    Feat("bote_d20_3", "bote", "Adivino", "Acierta 3 tiradas seguidas del icosaedro apostando a una sola cara.",
         "hint_bote"),
    Feat("scratch_top", "scratch", "Boleto premiado", "Consigue el premio máximo en un boleto.", "scratch_gold"),
    Feat("roulette_straight", "roulette", "Pleno", "Acierta un número exacto.", "roulette_partage"),
    Feat("sicbo_triple", "sicbo", "Trío", "Acierta un triple concreto.", "hint_sicbo"),
    Feat("bj_split2", "blackjack", "Doble victoria", "Divide una mano y gana las dos.", "bj_insurance"),
    Feat("bj_streak8", "blackjack", "Racha de crupier", "Gana 8 manos seguidas (los empates no rompen la racha).",
         "bj_counter"),
    Feat("hilo_10", "hilo", "Vidente", "Acierta 10 cartas seguidas.", "hint_hilo"),
    Feat("baccarat_3ties", "baccarat", "Tablas", "Acierta 3 empates.", "hint_baccarat"),
    Feat("crash_50", "crash", "Nervios de acero", "Retírate en x50 o más.", "hint_crash"),
    Feat("bingo_fast", "bingo", "Bingo exprés", "Canta bingo antes de la bola 40.", "bingo_cards"),
    Feat("mines_clear10", "mines", "Artificiero", "Limpia un tablero entero con 10 minas o más.", "hint_mines"),
    Feat("plinko_edge", "plinko", "Borde del abismo", "Mete una bola en una casilla del borde.", "plinko_rain"),
    Feat("princess_100x", "princess", "Bendición estelar", "Gana x100 o más en una tirada.", "princess_ante"),
    Feat("wheel_top", "wheel", "Gira, gira", "Consigue el segmento más alto.", "wheel_bonus"),
    Feat("horses_underdog", "horses", "Caballo perdedor", "Gana apostando por el caballo menos favorito.",
         "hint_horses"),
    Feat("keno_8", "keno", "Lotero", "Acierta 8 números o más.", "keno_extra"),
    Feat("poker_bluff", "poker", "Cara de póker", "Gana un bote sin enseñar tus cartas.", "hint_poker"),
    Feat("pick_tnt", "pickaxe", "Dinamitero", "Rompe 250 bloques con explosiones de TNT en una misma ronda.",
         "hint_pickaxe"),
    Feat("pick_deep", "pickaxe", "Plus Ultra", "Baja hasta la fila 110 en una sola ronda.", "pick_bench"),
    Feat("vp_sflush", "videopoker", "Escalera de color", "Consigue una escalera de color.", "vp_double"),
]
FEAT_BY_ID = {f.id: f for f in FEATS}

# ----------------------------------------------------------------------------
# Mejoras únicas: solo aparecen como oportunidades temporales. Son permanentes.
# Efectos: ("bld", id, m) ("passive", m) ("per_game", f) ("per_10b", f) ("per_unique", f) ("click", m)
# ("auto", n) ("crit", p) ("crit_mult", m) ("combo", n) ("gold_freq", f) ("gold_reward", m) ("opp_freq", f)
# ("opp_dur", s) ("opp_price", f) ("bm_cd", f) ("market_fee", m) ("offline", f) ("hint_sure", gid) ("special", key)
# ----------------------------------------------------------------------------
RARITIES = ["common", "rare", "epic", "legendary"]
RARITY_NAME = {"common": "Común", "rare": "Rara", "epic": "Épica", "legendary": "Legendaria"}
RARITY_COL = {"common": (176, 190, 197), "rare": (0, 157, 255), "epic": (190, 110, 255), "legendary": (253, 162, 0)}


@dataclass
class Unique:
    id: str
    name: str
    desc: str
    rarity: str
    effects: tuple
    requires: Optional[str] = None
    icon: str = "star"


ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"]
UNIQUES = []


def _chain(ids, name, icon, tiers):
    """Familia de mejoras con niveles: cada nivel solo aparece si tienes el anterior.
    tiers: lista de (rareza, descripción, efectos)."""
    prev = None
    for k, (uid, (rarity, desc, effects)) in enumerate(zip(ids, tiers)):
        full = name if len(tiers) == 1 else f"{name} {ROMAN[k]}"
        UNIQUES.append(Unique(uid, full, desc, rarity, tuple(effects), requires=prev, icon=icon))
        prev = uid


def _ids(base, n):
    return [base] + [f"{base}_{k}" for k in range(2, n + 1)]


# Cada negocio: 5 niveles (x2 · x1,8 · x1,6 · x1,5 · x1,4 = x12 en total)
_BLD_TIERS = [("common", "Proveedor", 2.0), ("rare", "Exclusiva", 1.8), ("rare", "Distribución", 1.6),
              ("epic", "Monopolio", 1.5), ("epic", "Imperio", 1.4)]
for _b in BUILDINGS:
    _prev = None
    for _k, (_rar, _tn, _m) in enumerate(_BLD_TIERS):
        _uid = [f"prov_{_b.id}", f"excl_{_b.id}", f"dist_{_b.id}", f"mono_{_b.id}", f"imp_{_b.id}"][_k]
        _txt = "el doble" if _m == 2 else f"un {round((_m - 1) * 100)}% más"
        UNIQUES.append(Unique(_uid, f"{_tn}: {_b.short}", f"{_b.name} produce {_txt}.", _rar,
                              (("bld", _b.id, _m),), requires=_prev, icon=_b.id))
        _prev = _uid

_chain(["glove_leather", "glove_silk", "glove_gold", "bionic", "midas", "glove_quantum", "glove_multi"],
       "Guante", "click", [
           ("common", "Guante de cuero: clics x2.", [("click", 2)]),
           ("common", "Guante de seda: clics x2.", [("click", 2)]),
           ("rare", "Guante de oro: clics x3.", [("click", 3)]),
           ("epic", "Mano biónica: clics x4.", [("click", 4)]),
           ("epic", "Toque de Midas: clics x5.", [("click", 5)]),
           ("epic", "Clic cuántico: clics x5.", [("click", 5)]),
           ("epic", "Clic multiversal: clics x8.", [("click", 8)]),
       ])
_chain(["auto_fair", "auto_fair_2", "auto_fair_3", "butler"], "Auto-clicker", "click", [
    ("common", "+3 clics automáticos por segundo.", [("auto", 3)]),
    ("common", "+5 clics automáticos por segundo.", [("auto", 5)]),
    ("rare", "+10 clics automáticos por segundo.", [("auto", 10)]),
    ("epic", "+25 clics automáticos por segundo.", [("auto", 25)]),
])
_chain(_ids("old_calc", 3), "Calculadora vieja", "click", [
    ("common", "+3% de probabilidad de crítico.", [("crit", 0.03)]),
    ("common", "+4% de probabilidad de crítico.", [("crit", 0.04)]),
    ("rare", "+5% de probabilidad de crítico.", [("crit", 0.05)]),
])
_chain(_ids("devastating", 2), "Puño de hierro", "click", [
    ("rare", "Los críticos valen el doble.", [("crit_mult", 2.0)]),
    ("epic", "Los críticos valen el doble otra vez.", [("crit_mult", 2.0)]),
])
_chain(_ids("strong_coffee", 3), "Café cargado", "click", [
    ("common", "+25 al combo máximo.", [("combo", 25)]),
    ("common", "+25 al combo máximo.", [("combo", 25)]),
    ("rare", "+50 al combo máximo.", [("combo", 50)]),
])
_chain(_ids("rabbit_foot", 3), "Pata de conejo", "golden", [
    ("common", "Las monedas doradas salen un 25% más a menudo.", [("gold_freq", 0.25)]),
    ("common", "Las monedas doradas salen un 25% más a menudo.", [("gold_freq", 0.25)]),
    ("rare", "Las monedas doradas salen un 50% más a menudo.", [("gold_freq", 0.5)]),
])
_chain(_ids("gold_clover", 2), "Trébol dorado", "golden", [
    ("rare", "Los premios de las monedas doradas valen el doble.", [("gold_reward", 2.0)]),
    ("epic", "Los premios de las monedas doradas valen el doble otra vez.", [("gold_reward", 2.0)]),
])
_chain(["accounting", "accounting2", "accounting_3", "accounting_4", "accounting_5"], "Contabilidad creativa",
       "business", [
           ("rare", "Ingresos pasivos +25%.", [("passive", 1.25)]),
           ("rare", "Ingresos pasivos +25%.", [("passive", 1.25)]),
           ("epic", "Ingresos pasivos +30%.", [("passive", 1.3)]),
           ("epic", "Ingresos pasivos +30%.", [("passive", 1.3)]),
           ("epic", "Ingresos pasivos +40%.", [("passive", 1.4)]),
       ])
_chain(_ids("fund", 3), "Fondo de inversión", "stats", [
    ("epic", "Ingresos pasivos x1,5.", [("passive", 1.5)]),
    ("epic", "Ingresos pasivos x1,4.", [("passive", 1.4)]),
    ("epic", "Ingresos pasivos x1,3.", [("passive", 1.3)]),
])
_chain(_ids("casino_synergy", 2), "Sinergia de casino", "chip", [
    ("rare", "+3% de ingresos pasivos por cada juego desbloqueado.", [("per_game", 0.03)]),
    ("epic", "+3% más de ingresos pasivos por cada juego desbloqueado.", [("per_game", 0.03)]),
])
_chain(_ids("brand", 2), "Marca registrada", "business", [
    ("epic", "+1% de ingresos pasivos por cada 10 negocios que tengas.", [("per_10b", 0.01)]),
    ("epic", "+1% más por cada 10 negocios que tengas.", [("per_10b", 0.01)]),
])
_chain(_ids("tycoon", 2), "Magnate", "crown", [
    ("epic", "+2% de ingresos pasivos por cada mejora única que tengas.", [("per_unique", 0.02)]),
    ("epic", "+2% más por cada mejora única que tengas.", [("per_unique", 0.02)]),
])
_chain(_ids("night_shift", 2), "Turno de noche", "business", [
    ("rare", "Tus negocios rinden un 15% más mientras no juegas.", [("offline", 0.15)]),
    ("epic", "Tus negocios rinden un 15% más mientras no juegas.", [("offline", 0.15)]),
])
_chain(_ids("agenda", 3), "Agenda de contactos", "business", [
    ("common", "Las oportunidades duran 15 segundos más.", [("opp_dur", 15)]),
    ("common", "Las oportunidades duran 15 segundos más.", [("opp_dur", 15)]),
    ("rare", "Las oportunidades duran 20 segundos más.", [("opp_dur", 20)]),
])
_chain(_ids("nose", 3), "Olfato para los negocios", "business", [
    ("rare", "Las oportunidades aparecen un 15% más a menudo.", [("opp_freq", 0.15)]),
    ("rare", "Las oportunidades aparecen un 15% más a menudo.", [("opp_freq", 0.15)]),
    ("epic", "Las oportunidades aparecen un 20% más a menudo.", [("opp_freq", 0.20)]),
])
_chain(_ids("negotiator", 3), "Negociador", "business", [
    ("rare", "Las oportunidades cuestan un 6% menos.", [("opp_price", 0.06)]),
    ("rare", "Las oportunidades cuestan un 6% menos.", [("opp_price", 0.06)]),
    ("epic", "Las oportunidades cuestan un 8% menos.", [("opp_price", 0.08)]),
])
_chain(_ids("merchant_friend", 2), "Amigo del mercader", "crown", [
    ("rare", "El mercado negro vuelve un 20% antes.", [("bm_cd", 0.20)]),
    ("epic", "El mercado negro vuelve un 20% antes.", [("bm_cd", 0.20)]),
])
_chain(_ids("broker", 2), "Bróker de confianza", "stats", [
    ("rare", "La comisión de la bolsa baja un 40%.", [("market_fee", 0.6)]),
    ("epic", "La comisión de la bolsa baja otro 40%.", [("market_fee", 0.6)]),
])
_chain(_ids("hot_mult", 3), "Mesa caliente", "chip", [
    ("rare", "Las victorias en la mesa caliente ganan x1,5 (en vez de x1,25).", [("hot_mult", 0.25)]),
    ("epic", "Las victorias en la mesa caliente ganan x2.", [("hot_mult", 0.5)]),
    ("epic", "Las victorias en la mesa caliente ganan x3.", [("hot_mult", 1.0)]),
])
_chain(_ids("hot_pot", 3), "Bote caliente", "golden", [
    ("rare", "El bote de la mesa caliente es el doble de grande.", [("hot_pot", 2.0)]),
    ("epic", "El bote de la mesa caliente es el doble de grande otra vez.", [("hot_pot", 2.0)]),
    ("epic", "El bote de la mesa caliente se duplica de nuevo.", [("hot_pot", 2.0)]),
])
_chain(_ids("hot_time", 2), "Reloj de arena", "chip", [
    ("common", "La mesa caliente dura 30 segundos más.", [("hot_dur", 30)]),
    ("rare", "La mesa caliente dura 30 segundos más.", [("hot_dur", 30)]),
])
_chain(_ids("news_inside", 2), "Fuentes internas", "stats", [
    ("epic", "Las noticias de la bolsa que recibes son más fiables.", [("news_rel", 0.05)]),
    ("epic", "Las noticias de la bolsa que recibes son todavía más fiables.", [("news_rel", 0.05)]),
])
# hitos de la bolsa (se consiguen jugando; se guardan en flags y no se pierden al hacer prestigio)
MARKET_MILESTONES = [
    ("market_x2", "Periódico financiero", "Duplica por primera vez una inversión en bolsa: vende por el doble o más "
                                          "de lo que te costó.",
     "Empiezan a llegar noticias de la bolsa al buzón. Léelas bien: anticipan cómo se moverán los valores... "
     "aunque no todas son ciertas."),
    ("news_pro", "Fuentes contrastadas", "Acierta 3 noticias seguidas: abre una posición durante la noticia, en un "
                                         "valor afectado y en la dirección correcta, y ciérrala con beneficio.",
     "Cada noticia te dice a qué valores afecta (no si suben o bajan) y te avisa de las que son puro ruido. "
     "Además, son más fiables."),
]
MARKET_MILESTONE_BY_ID = {m[0]: m for m in MARKET_MILESTONES}
UNIQUES += [
    Unique("pick_netherite", "Pico de netherita", "Cada 2 horas, en el Pico Minero, el próximo pico que salga en el "
           "rodillo será de netherita.", "epic", (("special", "pick_netherite"),), icon="pickaxe"),
    Unique("leg_pickaxe", "Reparación", "Tu pico se repara un poco cada vez que rompe una mena con valor.",
           "legendary", (("special", "pick_mending"),), icon="pickaxe"),
    Unique("leg_news", "Información privilegiada", "Las noticias de la bolsa son siempre ciertas. Hacia dónde "
           "mueven el mercado... eso tienes que deducirlo tú.", "legendary", (("news_true", 1),), icon="stats"),
    # legendarias: ventajas fuertes en los juegos
    Unique("leg_coinflip", "Cara marcada", "El chivatazo de Cara o Cruz no falla nunca.", "legendary",
           (("hint_sure", "coinflip"),), icon="coinflip"),
    Unique("leg_dice", "Dados de plomo", "Los dados cargados no fallan nunca.", "legendary",
           (("hint_sure", "dice"),), icon="dice"),
    Unique("leg_trilero", "Mano rápida", "Cada cierto tiempo puedes levantar un vaso antes de elegir.", "legendary",
           (("special", "trilero_peek"),), icon="trilero"),
    Unique("leg_hilo", "Rayos X", "El vistazo de Mayor o Menor no falla nunca.", "legendary",
           (("hint_sure", "hilo"),), icon="hilo"),
    Unique("leg_crash", "Sismógrafo", "El presentimiento de Crash no falla nunca.", "legendary",
           (("hint_sure", "crash"),), icon="crash"),
    Unique("leg_mines", "Mapa del campo", "El radar de Minas no falla nunca.", "legendary",
           (("hint_sure", "mines"),), icon="mines"),
    Unique("leg_horses", "Jockey comprado", "El soplo del jockey no falla nunca.", "legendary",
           (("hint_sure", "horses"),), icon="horses"),
    Unique("leg_bote", "Dado de plomo", "El dado trucado de El Bote no falla nunca.", "legendary",
           (("hint_sure", "bote"),), icon="bote"),
    Unique("leg_poker", "Doble visión", "La lectura de rivales no falla nunca.", "legendary",
           (("hint_sure", "poker"),), icon="poker"),
    Unique("leg_sicbo", "Cúpula de cristal", "El ojo de la cúpula no falla nunca.", "legendary",
           (("hint_sure", "sicbo"),), icon="sicbo"),
    Unique("leg_baccarat", "Baraja marcada", "La carta marcada no falla nunca.", "legendary",
           (("hint_sure", "baccarat"),), icon="baccarat"),
    Unique("leg_blackjack", "Ojo del crupier", "Cada cierto tiempo ves la carta tapada del crupier.", "legendary",
           (("special", "bj_peek"),), icon="blackjack"),
    Unique("leg_princess", "Princesa favorita", "Cada cierto tiempo, los orbes de tu próximo bonus valen el doble "
                                               "(la máquina no lo sabe).", "legendary",
           (("special", "princess_orbs"),), icon="princess"),
    Unique("leg_roulette", "Rueda trucada", "Cada cierto tiempo sabes en qué docena caerá la bola.", "legendary",
           (("special", "roulette_dozen"),), icon="roulette"),
]
UNIQUE_BY_ID = {u.id: u for u in UNIQUES}

# Oportunidades: (peso de aparición, duración en s, segundos de ingresos, veces tu fortuna)
OPP_RARITY = {
    "common": (45.0, 75, 600, 1.5),
    "rare": (35.0, 90, 1500, 2.0),
    "epic": (19.0, 105, 3600, 3.0),
    "legendary": (1.0, 120, 9000, 8.0),
}
OPP_GAP = (300, 720)          # segundos sin oportunidad entre una y otra (aleatorio en este rango)
OPP_BARGAIN = 0.0             # probabilidad de que una común salga de ganga (se puede comprar sin apostar)

# Mesas calientes: una mesa al azar multiplica las ganancias durante un rato, con un bote que se va gastando
HOT_GAP = (600, 900)          # segundos de juego entre una mesa caliente y la siguiente
HOT_DURATION = 120            # segundos que dura
HOT_MULT = 1.25               # multiplicador base de las ganancias
HOT_POT_SECS = 3600           # el bote equivale a esta cantidad de segundos de ingresos pasivos

# Mercado negro: trampas que garantizan ganar una jugada (requieren tener el juego)
CHEATS = {
    "coinflip": ("Moneda trucada", "Tu próxima tirada sale del lado que elijas."),
    "dice": ("Dados de imán", "Tu próxima tirada de Dados gana seguro."),
    "bote": ("Dado de imán", "En la próxima tirada sale la cara donde más has apostado."),
    "sicbo": ("Cúpula trucada", "Los dados caen en la combinación que más te paga."),
    "roulette": ("Imán en la ruleta", "La bola cae en el número que más te paga."),
    "blackjack": ("As en la manga", "Tu próxima mano es blackjack."),
    "trilero": ("Gafas de rayos X", "Ves la bola a través de los vasos durante una ronda."),
    "hilo": ("Baraja ordenada", "Ves la siguiente carta durante toda una partida."),
    "crash": ("Hack del cohete", "Te retira automáticamente justo antes de que explote."),
    "mines": ("Detector militar", "Ves todas las minas durante una partida."),
    "horses": ("Caballo dopado", "Tu caballo gana la próxima carrera."),
    "pickaxe": ("Pico encantado", "En tu próxima ronda, los primeros 100 golpes no gastan el pico."),
}
BLACK_MARKET_COOLDOWN = 2 * 3600

# ----------------------------------------------------------------------------
# Nivel de jugador (experiencia = lo que la casa espera ganarte)
# ----------------------------------------------------------------------------
XP_BASE = 1.0
XP_GROWTH = 2.6
MAX_PLAYER_LEVEL = 50
TITLES = [(0, "Novato"), (5, "Aficionado"), (10, "Habitual"), (15, "Jugador"), (20, "Tahúr"), (25, "Tiburón"),
          (30, "Ballena"), (35, "Magnate"), (40, "Leyenda"), (45, "Mito"), (50, "Dueño del casino")]
SHIELD_LEVELS = (10, 20, 30, 40, 50)
MARKET_LEVEL = 3              # nivel al que se abre la bolsa
SHORT_LEVEL = 15              # nivel al que se puede vender en corto

# Temas visuales (moneda del clicker + tapete), se desbloquean por nivel
THEMES = [
    ("clasico", "Clásico", 0, (238, 186, 60), (24, 96, 62)),
    ("cobre", "Ficha de cobre", 3, (196, 110, 70), (30, 92, 60)),
    ("bronce", "Dado de bronce", 7, (186, 130, 70), (60, 92, 40)),
    ("plata", "As de plata", 11, (200, 206, 214), (24, 46, 96)),
    ("oro", "Ruleta de oro", 15, (240, 180, 50), (110, 24, 32)),
    ("acero", "777 de acero", 19, (170, 186, 196), (18, 84, 90)),
    ("diamante", "Arlequín de diamante", 23, (120, 210, 255), (22, 40, 104)),
    ("cripto", "Moneda cripto", 28, (245, 168, 40), (34, 30, 26)),
    ("neon", "Siete de neón", 33, (220, 80, 255), (48, 18, 60)),
    ("cosmico", "Palos cósmicos", 38, (80, 170, 255), (14, 18, 52)),
]
THEME_BY_ID = {t[0]: t for t in THEMES}
# monedas y tapetes se desbloquean por separado y alternándose (nivel de jugador)
COIN_THEMES = [("cobre", 0), ("bronce", 3), ("plata", 8), ("oro", 13), ("acero", 18), ("diamante", 23),
               ("cripto", 28), ("neon", 33), ("cosmico", 38)]
FELT_THEMES = [("clasico", 0), ("bronce", 5), ("plata", 10), ("oro", 15), ("acero", 20), ("diamante", 25),
               ("cripto", 30), ("neon", 35), ("cosmico", 40)]
THEME_LEVELS = {"theme_coin": dict(COIN_THEMES), "theme_felt": dict(FELT_THEMES)}


def theme_name(tid, attr):
    if attr == "theme_felt" and tid == "clasico":
        return "Original"
    return THEME_BY_ID[tid][1]

# ----------------------------------------------------------------------------
# Ventajas VIP (prestigio) con niveles
# ----------------------------------------------------------------------------


@dataclass
class VipPerk:
    id: str
    name: str
    desc: Callable           # nivel -> texto
    costs: list              # coste de cada nivel en fichas

    @property
    def max_level(self):
        return len(self.costs)


INHERIT = [100, 10_000, 1e6, 100e6, 10e9]
VIP_PERKS = [
    VipPerk("inheritance", "Herencia", lambda l: f"Empiezas cada partida con {INHERIT[l - 1]:,.0f} €.".replace(",", "."),
            [1, 3, 8, 20, 50]),
    VipPerk("silk", "Dedos de seda", lambda l: f"Clics x{l + 1} para siempre.", [2, 5, 12, 30]),
    VipPerk("memory", "Memoria de jugador", lambda l: "Conservas juegos y modalidades al reiniciar.", [3]),
    VipPerk("offline", "Gerente nocturno", lambda l: f"Sin conexión ganas el {50 + 10 * l}% durante "
                                                     f"{8 + 4 * l} h.", [2, 4, 8, 16, 32]),
    VipPerk("contacts", "Contactos", lambda l: f"Negocios un {5 * l}% más baratos.", [2, 5, 10, 20, 40]),
    VipPerk("angel", "Inversor ángel", lambda l: f"Ingresos pasivos +{25 * l}%.", [3, 6, 12, 24, 48, 96, 192, 384]),
    VipPerk("tiger", "Ojo del tigre", lambda l: f"+{l}% a los premios del casino.",
            [4, 8, 16, 32, 64]),
    VipPerk("golden_rain", "Lluvia dorada", lambda l: f"Monedas doradas un {20 * l}% más a menudo.",
            [3, 6, 12, 24, 48]),
    VipPerk("butler", "Servicio", lambda l: f"+{5 * l} clics automáticos por segundo.", [2, 5, 10, 20, 40, 80]),
    VipPerk("alley", "Contacto en el callejón", lambda l: "Desbloquea el mercado negro.", [5]),
    VipPerk("collector", "Coleccionista", lambda l: f"Conservas tus {l} mejores mejoras únicas al reiniciar "
                                                    f"(las legendarias se conservan siempre).", [6, 15, 40]),
    VipPerk("whale", "Ballena", lambda l: "Ingresos y clics x2.", [60]),
]
VIP_BY_ID = {p.id: p for p in VIP_PERKS}

# ----------------------------------------------------------------------------
# Logros
# ----------------------------------------------------------------------------


@dataclass
class Achievement:
    id: str
    name: str
    desc: str
    check: Callable = field(repr=False)


ACHIEVEMENTS = []


def _ach(aid, name, desc, check):
    ACHIEVEMENTS.append(Achievement(aid, name, desc, check))


for _n, _name in [(1, "Primer clic"), (100, "Calentando dedos"), (1_000, "Tendinitis"), (10_000, "Martillo humano"),
                  (50_000, "Ratón en llamas"), (100_000, "Clic infinito")]:
    _ach(f"clicks_{_n}", _name, f"Haz {_n:,} clics.".replace(",", "."), lambda s, n=_n: s.stats["clicks"] >= n)

for _n, _name in [(1, "Primer euro"), (100, "Calderilla"), (10_000, "Clase media"), (1e6, "Millonario"),
                  (100e6, "Multimillonario"), (10e9, "Magnate"), (1e12, "Billonario"), (1e15, "Dueño del mundo"),
                  (1e18, "Más allá del dinero")]:
    _ach(f"earned_{_n:g}", _name, f"Gana {_n:,.0f} € en total.".replace(",", "."),
         lambda s, n=_n: s.stats["all_time_earned"] >= n)

for _n, _name in [(1, "Sueldo mínimo"), (100, "Rentista"), (10_000, "Inversor"), (1e6, "Capitalista"),
                  (100e6, "Fondo de inversión"), (10e9, "Banco central")]:
    _ach(f"ips_{_n:g}", _name, f"Alcanza {_n:,.0f} €/s de ingresos pasivos.".replace(",", "."),
         lambda s, n=_n: s.income_per_sec() >= n)

for _n, _name in [(10, "Emprendedor"), (50, "Empresario"), (100, "Holding"), (250, "Conglomerado"),
                  (500, "Corporación"), (1000, "Imperio")]:
    _ach(f"bld_{_n}", _name, f"Ten {_n} negocios en total.", lambda s, n=_n: s.total_buildings() >= n)

for _b in BUILDINGS:
    _ach(f"bld50_{_b.id}", f"Rey de: {_b.short}", f"Ten 50 de «{_b.name}».",
         lambda s, b=_b.id: s.buildings.get(b, 0) >= 50)

for _n, _name in [(1, "Bienvenido al casino"), (5, "Jugador habitual"), (10, "Ludópata profesional"),
                  (15, "Coleccionista de mesas"), (len(GAMES), "Lo he probado todo")]:
    _ach(f"games_{_n}", _name, f"Desbloquea {_n} juegos.", lambda s, n=_n: len(s.games_unlocked) >= n)

for _n, _name in [(5, "Socio del club"), (10, "Cliente preferente"), (20, "Habitual de la sala VIP"),
                  (30, "Leyenda del casino")]:
    _ach(f"club_{_n}", _name, f"Alcanza el nivel de jugador {_n}.", lambda s, n=_n: s.player_level() >= n)

for _n, _name in [(1, "Buen ojo"), (5, "Coleccionista"), (15, "Inversor de raza"), (30, "Museo privado")]:
    _ach(f"uniq_{_n}", _name, f"Consigue {_n} mejoras únicas.", lambda s, n=_n: len(s.uniques) >= n)
_ach("uniq_leg", "Leyenda viva", "Consigue una mejora legendaria.",
     lambda s: any(UNIQUE_BY_ID[u].rarity == "legendary" for u in s.uniques if u in UNIQUE_BY_ID))
for _n, _name in [(1, "Primera hazaña"), (5, "Hazañoso"), (12, "Héroe del casino"), (len(FEATS), "Leyenda de las mesas")]:
    _ach(f"feats_{_n}", _name, f"Consigue {_n} hazañas.",
         lambda s, n=_n: sum(1 for f in FEATS if s.flags.get(f.id)) >= n)

_ach("first_win", "Principiante con suerte", "Gana tu primera apuesta.", lambda s: s.stats["bets_won"] >= 1)
for _n, _name in [(100, "Apostador"), (1e6, "High roller"), (1e9, "Ballena"), (1e12, "Leviatán")]:
    _ach(f"wager_{_n:g}", _name, f"Apuesta {_n:,.0f} € en total.".replace(",", "."),
         lambda s, n=_n: s.stats["wagered"] >= n)
_ach("streak_5", "En racha", "Gana 5 apuestas seguidas.", lambda s: s.stats["best_streak"] >= 5)
_ach("streak_10", "Imparable", "Gana 10 apuestas seguidas.", lambda s: s.stats["best_streak"] >= 10)
_ach("lose_10", "Mala racha", "Pierde 10 apuestas seguidas.", lambda s: s.stats["worst_streak"] >= 10)
_ach("big_100x", "Golpe maestro", "Gana una apuesta con multiplicador x100 o más.",
     lambda s: s.stats["best_multiplier"] >= 100)
_ach("big_1000x", "Milagro", "Gana una apuesta con multiplicador x1000 o más.",
     lambda s: s.stats["best_multiplier"] >= 1000)
_ach("broke", "Ludopatía", "Quédate sin dinero después de haber tenido 1.000 €.", lambda s: s.flags.get("broke"))
_ach("golden_1", "¡Brilla!", "Atrapa una moneda dorada.", lambda s: s.stats["golden_clicked"] >= 1)
_ach("golden_10", "Buscador de oro", "Atrapa 10 monedas doradas.", lambda s: s.stats["golden_clicked"] >= 10)
_ach("golden_50", "Rey Midas", "Atrapa 50 monedas doradas.", lambda s: s.stats["golden_clicked"] >= 50)
_ach("prestige_1", "Nuevo comienzo", "Reinicia con prestigio por primera vez.", lambda s: s.stats["prestiges"] >= 1)
_ach("prestige_5", "Eterno retorno", "Reinicia con prestigio 5 veces.", lambda s: s.stats["prestiges"] >= 5)
_ach("combo_max", "Combo frenético", "Llega a un combo de 100.", lambda s: s.stats["best_combo"] >= 100)
_ach("hint_used", "Información privilegiada", "Usa una ventaja.", lambda s: s.stats.get("hints_used", 0) >= 1)
_ach("black_market", "Trato en el callejón", "Haz un trato en el mercado negro.",
     lambda s: s.stats.get("bm_deals", 0) >= 1)
_ach("shield", "Paraguas", "Usa un escudo.", lambda s: s.stats.get("shields_used", 0) >= 1)
_ach("market_1", "Accionista", "Haz tu primera operación en la bolsa.", lambda s: s.stats.get("trades", 0) >= 1)
_ach("market_x2", "Lobo de Wall Street", "Dobla tu dinero en una sola operación de bolsa.",
     lambda s: s.flags.get("market_x2"))

for _fid, _name, _desc in [
    ("coin_streak10", "Telépata", "Acierta 10 Cara o Cruz seguidos."),
    ("dice_sniper", "Francotirador novato", "Gana en Dados con menos de un 5% de probabilidad."),
    ("slots_jackpot", "¡BOTE!", "Gana el bote progresivo."),
    ("bote_d20", "Dados de rol", "Gana en El Bote con el icosaedro."),
    ("bj_natural", "Blackjack natural", "Consigue un blackjack con las dos primeras cartas."),
    ("bj_five", "Cinco cartas", "Gana una mano de blackjack con 5 o más cartas."),
    ("baccarat_tie", "Empate", "Acierta un empate en Baccarat."),
    ("crash_10", "Cohete", "Retírate en Crash a x10 o más."),
    ("crash_100", "A la Luna", "Retírate en Crash a x100 o más."),
    ("bingo_line", "¡Línea!", "Canta línea en el Bingo."),
    ("bingo_full", "¡BINGO!", "Completa un cartón de Bingo."),
    ("mines_clear", "Desactivador", "Limpia un tablero de Minas entero con 3 o más minas."),
    ("princess_bonus", "Lluvia de estrellas", "Entra en las tiradas gratis de la Princesa Estelar."),
    ("princess_retrigger", "¡Más tiradas!", "Consigue tiradas extra dentro del bonus de la Princesa."),
    ("horses_long", "Tiro largo", "Gana una carrera apostando por un caballo con cuota x10 o más."),
    ("poker_win", "Tiburón", "Gana un bote de póker en el enfrentamiento final."),
    ("vp_quads", "Póker", "Consigue un póker en Video Póker."),
    ("vp_royal", "Escalera real", "Consigue una escalera real en Video Póker."),
]:
    _ach(_fid, _name, _desc, lambda s, f=_fid: s.flags.get(f, False))

ACHIEVEMENT_BY_ID = {a.id: a for a in ACHIEVEMENTS}
