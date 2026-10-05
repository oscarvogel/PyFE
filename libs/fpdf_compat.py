# coding=utf-8
"""Compatibilidad entre las plantillas de pyfepdf y fpdf2.

Por que existe
--------------
Las plantillas de pyfepdf (factura_qr.csv, factura_marca.csv, etc.) usan dos
codigos de alineacion que no son de fpdf: "D" y "I".

En fpdf 1.7, del que deriva pyfepdf, la traduccion estaba explicita en el
renderizador de plantillas:

    align = {'L':'L','R':'R','I':'L','D':'R','C':'C','':''}.get(align)
    # D/I in spanish

O sea: D es "derecha" y I es "izquierda", en castellano. fpdf2 elimino esa
traduccion y pasa el valor directo a cell(), que solo acepta el enum Align.
El resultado es:

    ValueError: I is not a valid Align

y el PDF no se genera. Como la factura ya quedo autorizada en ARCA para
entonces, el usuario se queda sin el documento que tiene que entregar.

Por que se arregla aca y no en pyafipws
---------------------------------------
pyafipws/ esta en .gitignore: es una copia local, no versionada. Un arreglo
dentro de ella no llega a nadie mas y se pierde en la proxima clonacion. Ademas
arreglarlo en el renderizador obligaria a retocar 500 campos de cada
plantilla; hacerlo sobre los elementos ya cargados es lo mismo con tres lineas
y sirve para cualquier plantilla, propia o descargada.
"""

import functools
import logging
import unicodedata

# Traduccion de los codigos de pyfepdf a los que fpdf2 entiende.
ALIGN_PYAFIPWS = {
    "D": "R",   # "derecha", en castellano. Se usa en importes y alicuotas.
    "I": "L",   # "izquierda", en castellano. Se usa en CAE, CUIT y direcciones.
    "L": "L",
    "R": "R",
    "C": "C",
    "J": "J",
    "": "",
}

# fpdf 1.7 reemplazaba "arial black" por "arial" antes de dibujar, y seguia
# drawing en negrita. fpdf2 no lo hace y lanza:
#     FPDFException: Undefined font: arial black
# Sin este mapeo, la plantilla no se dibuja entera. Todas las plantillas de
# factura lo usan en el titulo del comprobante.
FUENTES_COMPATIBLES = {
    "arial black": "arial",
    "arialblack": "arial",
    "arial narrow": "arial",
}


def normalizar_fuentes(elementos):
    """Reemplaza las fuentes que fpdf2 no trae incorporadas."""
    cambiados = 0
    for elemento in elementos or []:
        nombre = elemento.get("font")
        if isinstance(nombre, str):
            reemplazo = FUENTES_COMPATIBLES.get(nombre.strip().lower())
            if reemplazo:
                elemento["font"] = reemplazo
                cambiados += 1
    return cambiados


# Los fondos que en fpdf 1.7 significaban 'sin relleno' y que fpdf2 pinta.
# 0x00FFFF es cian y 0x000000 es negro: con fpdf2 la factura salia con la
# pagina negra y los textos cian.
FONDOS_HEREDADOS_SIN_RELLENO = (0x000000, 0x00FFFF)
FONDO_BLANCO = 0xFFFFFF

# Solo los campos de TEXTO. Las imagenes, las lineas y los codigos de barras
# necesitan fondo transparente: pintarles encima tapa justo lo que tienen que
# mostrar. En las plantillas, los campos de texto son tipo 'T' (o 't' minuscula
# en factura_qr.csv, que tiene una fila asi).
TIPOS_DE_TEXTO = ("T", "t")


def normalizar_fondos(elementos):
    """Los fondos heredados de fpdf 1.7 dejan de pintarse con fpdf2.

    Las plantillas viejas ponen en la columna de fondo 65535 (cian) y 0 (negro)
    para casi todo, y en fpdf 1.7 esos valores no se pintaban: eran la manera
    de decir 'sin relleno'. fpdf2 los pinta, porque su plantilla declara

        background: Optional[int] = None    # None = sin relleno
        if background is None: fill = False
        else:                 fill = True

    o sea que CUALQUIER entero se pinta, incluido el 0. Con eso la factura
    salia con la pagina negra (el marco 'Cuadro', de 200 x 278 mm, relleno de
    negro) y los textos cian.

    Que se ponga depende del tipo, porque no es lo mismo:

    - Texto: va a BLANCO. Es lo que ya usa factura_marca.csv, que es la
      plantilla escrita para fpdf2 y por lo tanto la que se sabe que dibuja
      bien. Un texto sin relleno tambien andaria, pero el blanco es el valor
      probado.
    - Marcos, lineas, imagenes y codigos de barras: SIN RELLENO. Un marco
      pintado tapa la pagina entera, una linea pintada tapa la linea, y una
      imagen pintada tapa la imagen.
    """
    cambiados = 0
    for elemento in elementos or []:
        fondo = elemento.get("background")
        # En las plantillas el color llega como int ya convertido, pero puede
        # llegar como texto si el campo se cargo a mano.
        if isinstance(fondo, str):
            try:
                fondo = int(fondo, 16)
            except ValueError:
                continue
        if fondo not in FONDOS_HEREDADOS_SIN_RELLENO:
            continue
        if elemento.get("type") in TIPOS_DE_TEXTO:
            elemento["background"] = FONDO_BLANCO
        else:
            elemento["background"] = None
        cambiados += 1
    return cambiados


def normalizar_align(elementos):
    """Traduce los align de una lista de elementos de plantilla.

    Devuelve cuantos cambio, para poder avisar si una plantilla usa codigos
    viejos (que es util cuando se acaba de cambiar una plantilla a mano).
    """
    cambiados = 0
    for elemento in elementos or []:
        valor = elemento.get("align")
        if valor in ALIGN_PYAFIPWS and ALIGN_PYAFIPWS[valor] != valor:
            elemento["align"] = ALIGN_PYAFIPWS[valor]
            cambiados += 1
    return cambiados


def _instalar_has_key():
    """Vuelve a poner Template.has_key(), que fpdf2 elimino.

    pyfepdf lo usa 17 veces dentro de ProcesarPlantilla para preguntar si la
    plantilla tiene determinado campo antes de llenarlo. En fpdf 1.7 era:

        def has_key(self, name):
            return name.lower() in self.keys

    Sin esto, ProcesarPlantilla revienta en la linea 1110 con

        AttributeError: 'Template' object has no attribute 'has_key'

    y devuelve False. El PDF se escribe igual, pero VACIO de los datos de la
    factura: un comprobante sin importe ni cliente es peor que no tener
    ninguno, porque parece valido.
    """
    try:
        from fpdf.template import Template
    except ImportError:
        return False
    if hasattr(Template, "has_key"):
        return False

    def has_key(self, name):
        return str(name).lower() in self.keys

    Template.has_key = has_key
    return True


def _relajar_setitem():
    """Devuelve el comportamiento de fpdf 1.7 al asignar un campo que no existe.

    fpdf 1.7:
        def __setitem__(self, name, value):
            if name.lower() in self.keys:
                ...lo guarda...

    o sea, si la plantilla NO tiene ese campo, lo ignoraba en silencio.

    fpdf 2.x lanza FPDFException: Element not loaded, cannot set item: hoja.
    pyfepdf asigna muchos campos que existen en sus plantillas originales pero
    no en las nuestras (por ejemplo "hoja", que es de un formato con paginas
    multiple). Con fpdf2, el primero que falta aborta ProcesarPlantilla entero
    y el PDF sale sin los datos de la factura.

    Aca se vuelve al comportamiento de antes: los campos desconocidos se
    cuentan y se ignoran, y los que la plantilla si tiene se escriben igual.

    De paso se restaura la conversion a texto, que fpdf 1.2 hacia y fpdf2 no:

        if value is None: value = ""
        else:             value = str(value)

    Sin eso, un campo numerico (por ejemplo "IVA21") queda como int y el
    render revienta con:
        AttributeError: 'int' object has no attribute 'startswith'
    """
    try:
        from fpdf.template import Template
    except ImportError:
        return False
    if getattr(Template, "_pyfe_ignora_campos_desconocidos", False):
        return False

    original = Template.__setitem__
    ignorados = set()

    def __setitem__(self, name, value):
        if not isinstance(name, str) or name.lower() not in self.keys:
            ignorados.add(str(name))
            return
        if value is None:
            value = ""
        else:
            value = str(value)
        original(self, name, value)

    Template.__setitem__ = __setitem__
    Template.set = __setitem__          # en fpdf2 `set` es un alias
    Template._pyfe_ignora_campos_desconocidos = True
    Template._campos_ignorados = ignorados
    return True


def campos_ignorados():
    """Nombres de campos que se pidieron y la plantilla no tiene."""
    try:
        from fpdf.template import Template
    except ImportError:
        return set()
    return set(getattr(Template, "_campos_ignorados", ()))


# -- Caracteres que la fuente no tiene -------------------------------------
#
# Que se rompe
# ------------
# Las plantillas de comprobante usan core fonts (helvetica, courier, times), que
# cubren latin-1 y nada mas. fpdf2, al escribir con una de ellas, hace:
#
#     def normalize_text(self, text):
#         if not self.is_ttf_font and self.core_fonts_encoding:
#             try:
#                 return text.encode(self.core_fonts_encoding).decode("latin-1")
#             except UnicodeEncodeError as error:
#                 raise FPDFUnicodeEncodingException(...)
#
# y revienta con el primer caracter por encima de U+00FF. El caso real: la
# descripcion del renglon de la factura 000300000459 traia un EN DASH (U+2013)
# en "... logistica RND – Septiembre 2026." y la factura no se pudo imprimir.
#
# El detalle incomodo: el error no venia de la plantilla, que es 100% ASCII,
# sino del DATO. Recorridas las 538 descripciones de la base, era la unica con
# un caracter fuera de latin-1. O sea que el sistema se cae por una letra que
# escribio el usuario.
#
# Con fpdf 1.7.2 eso no pasaba: el mismo caracter salia como un cuadrito de
# reemplazo, en silencio. El salto a fpdf2 no introdujo el bug, lo destapo.
#
# Que se hace
# -----------
# Se sustituye el CARACTER al escribir, no en la base. La descripcion guardada
# queda con su en dash, que es lo que dice el dato, y lo unico que cambia es el
# glifo que sale impreso. Tocar la base seria peor: un comprobante ya autorizado
# en ARCA tiene su descripcion registrada alla, y cambiarla localmente deja los
# dos copias distintas.
#
# Con una fuente TTF no se sustituye nada: ahi no hay problema, y cambiar el
# texto de un comprobante que se puede imprimir bien no tiene sentido.

SUSTITUCIONES = {
    # Guiones: todos se imprimen como guion corto.
    "\u2010": "-",  # hyphen
    "\u2011": "-",  # non-breaking hyphen
    "\u2012": "-",  # figure dash
    "\u2013": "-",  # en dash  <-- el de la factura 459
    "\u2014": "-",  # em dash
    "\u2015": "-",  # horizontal bar
    "\u2212": "-",  # minus
    # Comillas tipograficas: el corrector de Word las pone solas.
    "\u2018": "'", "\u2019": "'", "\u201a": "'", "\u201b": "'",
    "\u201c": '"', "\u201d": '"', "\u201e": '"', "\u201f": '"',
    "\u2032": "'", "\u2033": '"',   # prima y doble prima
    # Otros que aparecen al copiar texto de una pagina web.
    "\u2026": "...",  # ellipsis
    "\u2022": "*",    # bullet
    "\u2007": " ", "\u202f": " ", "\u2009": " ", "\u200a": " ",  # espacios finos
    "\u200b": "",     # zero width space
    "\u200e": "", "\u200f": "",     # marcas de direccion
    "\ufeff": "",     # BOM
    "\ufffd": "?",    # el caracter de reemplazo: no se sabe que era
}

# Ojo con lo que NO esta aca: el espacio duro (U+00A0) y el soft hyphen
# (U+00AD) estan en latin-1, asi que `_encodable` los deja pasar y nunca llegan
# a la tabla. Se dejan intactos a proposito: se imprimen, y tocarlos seria
# cambiar texto que ya anda. La regla es "solo lo que la fuente no tiene", y
# esos si los tiene.

# Para saber que se sustituyo, y avisar una sola vez por caracter.
SUSTITUIDOS = set()
LOG = logging.getLogger("pyfe")


def _encodable(caracter, encoding):
    """El caracter se puede escribir con esa fuente."""
    try:
        caracter.encode(encoding)
        return True
    except (UnicodeEncodeError, LookupError):
        return False


def _alternativa(caracter):
    """Un reemplazo sensato para un caracter que la fuente no tiene.

    Primero la tabla. Despues la descomposicion NFKD, que salva las letras con
    acento que no entran en latin-1 (Ā -> A, ﬁ -> fi). Y si no queda nada
    util, un '?': un caracter ilegible es preferible a una excepcion, porque la
    excepcion deja al comprobante sin imprimir.
    """
    if caracter in SUSTITUCIONES:
        return SUSTITUCIONES[caracter]

    descompuesto = unicodedata.normalize("NFKD", caracter)
    sin_acentos = "".join(
        c for c in descompuesto if not unicodedata.combining(c))
    if sin_acentos and sin_acentos != caracter:
        return sin_acentos

    return "?"


def transliterar(texto, encoding="latin-1"):
    """Cambia lo que la fuente no tiene por algo que si pueda imprimir.

    `encoding` es el de la fuente, que es lo que decide: con cp1252 el euro
    (U+20AC) entra y con latin-1 no. Por eso se pregunta por `encoding` y no se
    asume, y por eso un texto con acentos NO se toca: estan en latin-1 y salen
    bien.
    """
    if not texto or not isinstance(texto, str):
        return texto
    # El caso comun: no hay nada raro. No se arma una lista de mil caracteres
    # para una factura entera que ya se puede imprimir.
    if all(_encodable(c, encoding) for c in texto):
        return texto

    salida = []
    for caracter in texto:
        if _encodable(caracter, encoding):
            salida.append(caracter)
            continue
        reemplazo = _alternativa(caracter)
        # El reemplazo tiene que poder imprimirse tambien.
        if not all(_encodable(c, encoding) for c in reemplazo):
            reemplazo = "?"
        if caracter not in SUSTITUIDOS:
            SUSTITUIDOS.add(caracter)
            # Una linea por caracter, no por cada campo de cada factura: con
            # core fonts una factura escribe cientos de textos y el aviso se
            # repetiria sin agregar nada.
            LOG.warning(
                "PDF: el caracter U+%04X (%s) no lo tiene la fuente y se "
                "imprimio como %r. El dato guardado no se toco.",
                ord(caracter),
                unicodedata.name(caracter, "sin nombre"),
                reemplazo)
        salida.append(reemplazo)
    return "".join(salida)


def olvidar_sustituciones():
    """Vacia el registro de caracteres ya avisados. Lo usan los tests."""
    SUSTITUIDOS.clear()


def caracteres_sustituidos():
    """Los caracteres que hubo que cambiar para poder imprimir."""
    return set(SUSTITUIDOS)


def _instalar_normalize_text():
    """Que fpdf2 no revente con un caracter que la fuente no tiene.

    Envuelve `FPDF.normalize_text`, que es donde fpdf2 valida la codificacion.
    Se intercepta ahi y no en los datos del comprobante por dos motivos: es el
    unico punto por donde pasa TODO el texto (nombre del cliente, domicilio,
    descripciones, observaciones, datos de la empresa), y funciona con cualquier
    plantilla, propia o descargada.

    El shim no copia la firma de la libreria: usa `*args, **kwargs` y
    `functools.wraps`, asi que si fpdf2 cambia los argumentos, sigue andando.
    """
    try:
        from fpdf import FPDF
    except ImportError:
        return False
    if getattr(FPDF, "_pyfe_normalize_text", False):
        return False

    original = FPDF.normalize_text

    @functools.wraps(original)
    def normalize_text(self, *args, **kwargs):
        # Solo para core fonts: con una TTF no hay nada que corregir y el texto
        # se escribe tal cual. La condicion es la misma que consulta la
        # libreria, para no inventar reglas propias.
        if not getattr(self, "is_ttf_font", False):
            encoding = getattr(self, "core_fonts_encoding", None)
            if encoding and args:
                primero = args[0]
                if isinstance(primero, str):
                    args = (transliterar(primero, encoding),) + args[1:]
        return original(self, *args, **kwargs)

    FPDF.normalize_text = normalize_text
    FPDF._pyfe_normalize_text = True
    return True


def instalar_compatibilidad():
    """Instala todos los shims. Idempotente.

    Se llama una vez, al importar, para que ninguna de las pantallas que arman
    un comprobante tenga que acordarse.
    """
    _instalar_normalize_text()
    _instalar_has_key()
    _relajar_setitem()


def normalizar_plantilla(pyfpdf):
    """Deja la plantilla lista para fpdf2: metodos, alineacion y fuentes.

    Se llama despues de CrearPlantilla(), que es cuando existe el Template.
    Si la plantilla todavia no esta, no hace nada: no es un error, solo que
    todavia no hay nada que traducir.

    Devuelve cuantos campos toco cada cosa: (alineacion, fuentes, fondos).
    """
    instalar_compatibilidad()
    plantilla = getattr(pyfpdf, "template", None)
    if plantilla is None:
        return 0, 0, 0
    return (normalizar_align(plantilla.elements),
            normalizar_fuentes(plantilla.elements),
            normalizar_fondos(plantilla.elements))


# Los shims se instalan al importar el modulo, no cuando cada pantalla se acuerda
# de hacerlo. El de los caracteres es el que mas importa: sin el, basta con que
# alguien escriba un guion medio en una descripcion para que la factura no se
# pueda imprimir.
instalar_compatibilidad()
