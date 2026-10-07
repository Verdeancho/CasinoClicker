# Casino Clicker

Clicker de casino hecho en Python con **pygame-ce** y sonido sintetizado con **numpy**. Tiene estética indie-retro, al estilo de Balatro.

**Descargar:** en la página de [Releases](https://github.com/Verdeancho/CasinoClicker/releases). No hace falta
instalar nada.
- **Windows:** `CasinoClicker.exe`. La partida se guarda en `%APPDATA%\CasinoClicker`.
- **Mac:** `CasinoClicker-mac-arm.zip` para Mac con chip M1 o posterior, o `CasinoClicker-mac-intel.zip` para Mac con
  Intel. Descomprime el zip y arrastra `CasinoClicker.app` a Aplicaciones. La partida se guarda en
  `~/Library/Application Support/CasinoClicker`.
  - La app no está firmada por Apple. La primera vez que la abras, macOS la bloqueará: ve a **Ajustes del Sistema →
    Privacidad y seguridad** y pulsa **Abrir igualmente**.
  - Si dice que la app está dañada, ejecuta `xattr -cr /Applications/CasinoClicker.app` en Terminal.

**Jugar desde el código:** haz doble clic en `Jugar.bat`. La primera vez prepara un entorno `.venv` con las dependencias.
También puedes usar `.venv\Scripts\python main.py`. La partida se guarda sola en `partida.json` (cada 30 s y al cerrar).
Las partidas de versiones anteriores se guardan aparte (`partida_v3.json`) y se empieza de cero.

## La idea
Apostar no da dinero a la larga: todas las apuestas pierden un poco de media. Lo que da es **inmediatez**, y hay cosas
que solo se consiguen juntando mucho dinero de golpe. Quien apuesta con cabeza e invierte lo que gana avanza muchísimo
más rápido; quien solo espera, avanza despacio; y quien apuesta a lo loco sin invertir depende de su suerte.

## Novedades de la versión 4.4
- **Descripciones con título de color:** al dejar el ratón encima, el nombre sale destacado: verde en las mejoras y
  los negocios, el color de su rareza en las oportunidades y dorado brillante y animado en las ventajas VIP.
- **Bolsa:**
  - Cuando llega una noticia, la pestaña Bolsa muestra el aviso **NEWS!** hasta que la abres.
  - La bolsa se guarda entera: al volver a abrir el juego está exactamente como la dejaste (gráficas, tendencias y
    la noticia en curso).
  - Botón **VENDER TODO** para vender todas tus acciones de un valor de golpe.
- **Carreras de caballos:** la meta se ve venir, con postes de distancia, un poste de meta y una barra de progreso.

## Novedades de la versión 4.3
- **Pico Minero** (juego nuevo, inspirado en Falling Pickaxe):
  - Las tiradas se compran por paquetes de 10, 25, 50 o 100: se pagan al comprar y se juegan seguidas (se pueden
    pausar, y si cierras el juego el paquete te espera).
  - Cada tirada gira un rodillo: cruz (no cae nada) o un pico de madera, piedra, hierro o diamante. Tras
    7 cruces seguidas, el siguiente giro da pico seguro. Cae pico más o menos 1 de cada 4 giros.
  - El pico cae por un pozo de 10 columnas con física real, medida en el original: bota, rompe bloques y pica vetas
    de carbón, redstone, oro, diamante y esmeralda. Cada golpe quita 1 de vida al bloque y 1 de durabilidad al pico;
    el material solo cambia la durabilidad, que se ve encima del pico.
  - En los bordes hay bloques de diamante y de esmeralda, que son raros y valen mucho.
  - Bloques especiales:
    - La TNT explota en cadena.
    - La mesa de trabajo repara el pico y lo sube de material.
    - El bloque de expansión ensancha el pico (x1,5, x2 o x2,5).
    - El slime no se rompe y lanza el pico.
  - Hazañas:
    - **Dinamitero:** una carga de TNT que explota donde está el pico, cada 60–30 minutos.
    - **Plus Ultra:** un yunque cada hora, que repara el pico cuando quieras.
  - Mejoras únicas:
    - **Pico de netherita** (épica): cada 2 horas, el próximo pico que salga será de netherita.
    - **Reparación** (legendaria): el pico se repara al romper menas.
  - Mercado negro: **Pico encantado**. Cae pico seguro y da 100 golpes gratis.
  - Texturas propias (`tools/make_ores.py` y `tools/make_pickaxe_assets.py`); los picos y el yunque salen de
    dibujos del autor.
- **Bolsa nueva:**
  - 12 valores: se añaden Agricultura, Automoción, Banca, Farmacéutica, Renovables y Videojuegos.
  - 240 noticias con titular y cuerpo. Llegan de una en una al **buzón**, que abre el periódico **Financial Dimes**,
    y duran 10, 15 o 20 minutos.
  - Las verdaderas marcan una tendencia clara (normal, importante o bombazo) y las falsas solo amagan al principio.
  - Las noticias ya no se compran: se ganan con hitos (**Periódico financiero**: duplica una inversión;
    **Fuentes contrastadas**: acierta 3 noticias seguidas). Están en el botón **MEJORAS** de la bolsa, junto a las
    mejoras únicas **Fuentes internas** y la legendaria **Información privilegiada**.
- **Aspecto:**
  - El botón de monedas y tapetes está ahora junto al de sonido.
  - Solo se ven los aspectos desbloqueados.
  - Monedas y tapetes se desbloquean por separado, alternándose.

## Novedades de la versión 4.2
- **Aspecto** (monedas y tapetes): ahora se abre con el botón de la paleta, junto a la moneda.
- **Tamaño de ventana** en Ajustes: botones − y +, «Ajustar» (lo más grande que cabe en tu pantalla) y pantalla
  completa (también con F11). También puedes estirar la ventana con el ratón y se recuerda el tamaño.
- **Descripciones completas:** deja el ratón un segundo sobre una mejora, una oportunidad, una ventaja VIP, un logro,
  una noticia o una oferta del mercado negro y verás todo el texto.
- **Límite de 25 clics por segundo** en la moneda. Clicar rápido (jitter o butterfly) no llega a ese límite; los
  autoclickers sí.
- **Partida protegida:** en el ejecutable se guarda comprimida y codificada (no se puede editar con el Bloc de
  notas) y se guarda una copia de la anterior por si el archivo se estropea. Las partidas antiguas cargan normal.

## Novedades de la versión 4
- **Oportunidades:** de vez en cuando aparece una oferta temporal (una cada pocos minutos; pasa más tiempo sin oferta
  que con ella). Siempre es una **mejora única y permanente** que no existe en la tienda.
  - Hay cuatro rarezas: común, rara, épica y legendaria.
  - Son caras a propósito: normalmente hace falta apostar para llegar a tiempo.
  - Las legendarias son ventajas fuertes en un juego y salen muy de vez en cuando.
  - En **Mejoras → Colección** ves todas las que existen.
- **Hazañas:** las ventajas grandes de cada juego no se compran, se ganan con hazañas difíciles. Algunos ejemplos:
  - Doblar 7 veces seguidas en Cara o Cruz.
  - Superar la ronda 5 del trilero.
  - Dividir y ganar las dos manos en blackjack.

  Las ventajas se recargan con el tiempo: 1 hora, que baja hasta 30 minutos con el nivel de jugador. Su fiabilidad es
  secreta.
- **Ventajas nuevas:**
  - Seguro y contador de cartas en blackjack.
  - "El trilero enseña uno" (Monty Hall).
  - Ojo de la cúpula en Sic Bo.
  - Carta marcada en Baccarat.
  - Legendarias como la Mano rápida, el Ojo del crupier, la Rueda trucada o la Princesa favorita.
- **Mercado negro:** se desbloquea en la Sala VIP. Cada 2 horas de juego, un mercader te vende una trampa que gana
  seguro una jugada, a cambio de una de tus mejoras únicas.
- **Bolsa:** se abre en el nivel 3. Oro, Petróleo, Naviera, Semiconductores, Turismo y Cripto, con velas japonesas,
  fases de mercado, onda estacional, desplomes y splits. En el nivel 15 se desbloquea la venta en corto.
  Con el «Periódico financiero» (mejora única) llegan noticias: léelas bien, porque anticipan si un valor subirá o
  bajará durante los 15 minutos siguientes (casi siempre).
- **Escudos:** salen muy rara vez de la moneda dorada, y te regalan uno cada 10 niveles. Si pierdes la apuesta
  protegida, te devuelven lo apostado.
- **Mesas calientes:** cada 10–15 minutos de juego, una mesa al azar se enciende con marco dorado durante 2 minutos.
  Tus ganancias en ella valen x1,25 (mejorable hasta x3) y el extra sale de un bote de 1 hora de tus ingresos
  (mejorable). Cuando se acaba el bote o el tiempo, se apaga.
- **Mejoras únicas con niveles (I, II, III...):** 153 en total. Cada nivel solo aparece si tienes el anterior.
- **Sin límite de apuesta:** solo te limita tu dinero.
- **Nivel de jugador:** la experiencia es lo que la casa espera ganarte, igual en todos los juegos. Da recarga de
  ventajas más rápida, títulos, escudos, valores de bolsa y aspectos nuevos.
- **Aspecto:** 10 monedas para el clicker y 10 tapetes con marco temático.
- **Cartas nuevas:** baraja ilustrada (`casino/assets/cartas.png`).
- **Cara o Cruz** con moneda y animación nuevas: la moneda cae siempre en la cara que dice el resultado.
- **Trilero nuevo:** el pañuelo tapa solo dos vasos vecinos y los cruza o no. Siguiendo bien la bola se puede deducir,
  y la mancha te lo asegura.
- **Princesa Estelar:** gira en torno a las 15 tiradas gratis, que salen más a menudo y pagan el doble.
- **Retornos:** ningún juego baja del 95% (ya no se muestran en pantalla).
- **Botón JUEGOS** en cada mesa para saltar a cualquier otro juego.
- **Mejoras → Desglose:** cómo se calcula cada clic y cada euro por segundo, multiplicador a multiplicador.
- **VIP con niveles:** las fichas cuentan solo el beneficio neto, así que apostar mucho ya no las infla.

## Simulador de economía
`tools/sim_economia.py` juega partidas aceleradas con cuatro perfiles: el que espera, el loco, el estratega y el
acaparador. Sirve para ajustar los números.
```
.venv\Scripts\python tools\sim_economia.py 60 4
```

## Generar el ejecutable
```
.venv\Scripts\python -m pip install pyinstaller pillow
.venv\Scripts\python -m PyInstaller --noconfirm CasinoClicker.spec
```
Las versiones de Mac las compila GitHub Actions (`.github/workflows/macos.yml`) al subir una etiqueta `v*`, y las
añade a la release. Para comprobar una build: `CASINO_SELFCHECK=resultado.txt` abre todos los juegos sin ventana y
escribe el resultado.

## Atajos
`Espacio` lanza la acción principal de cada juego. En Blackjack: `H` pedir, `S` plantarse, `D` doblar, `P` dividir.
En Mayor o Menor: flechas ↑ y ↓.

## Estructura
```
main.py                 punto de entrada
casino/state.py         economía, apuestas, oportunidades, hazañas, escudos, mercado negro, prestigio, guardado
casino/data.py          negocios, juegos, mejoras, mejoras únicas, hazañas, trampas, temas, VIP y logros
casino/market.py        la bolsa
casino/news.py          noticias de la bolsa
casino/app.py           ventana principal (clicker, negocios, pestañas, oportunidades, modales)
casino/skins.py         monedas del clicker, tapetes con marco y moneda de Cara o Cruz
casino/gfx.py           primitivas gráficas, pixelizado, fondo y cachés
casino/pixfont.py       fuente pixel art propia
casino/ui.py            interfaz en modo inmediato
casino/icons.py         iconos procedurales
casino/art.py           sprites (moneda, cartas, fichas, símbolos, caballos...)
casino/dice3d.py        dados 3D (d6, d8, d12, d20)
casino/fx.py            partículas y efectos
casino/audio.py         sintetizador de efectos y música
casino/games/*.py       un archivo por juego (más princess_logic.py y poker_engine.py)
tools/sim_economia.py   simulador de la economía
```
