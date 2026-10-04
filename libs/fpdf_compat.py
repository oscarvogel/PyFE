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


def normalizar_plantilla(pyfpdf):
    """Deja la plantilla lista para fpdf2: metodos, alineacion y fuentes.

    Se llama despues de CrearPlantilla(), que es cuando existe el Template.
    Si la plantilla todavia no esta, no hace nada: no es un error, solo que
    todavia no hay nada que traducir.

    Devuelve cuantos campos toco cada cosa: (alineacion, fuentes, fondos).
    """
    _instalar_has_key()
    _relajar_setitem()
    plantilla = getattr(pyfpdf, "template", None)
    if plantilla is None:
        return 0, 0, 0
    return (normalizar_align(plantilla.elements),
            normalizar_fuentes(plantilla.elements),
            normalizar_fondos(plantilla.elements))
