# coding=utf-8
from dataclasses import dataclass
from pathlib import Path
from shutil import copy2
import struct
import zlib

VOGEL_COLORES = {
    "primario": "#0F2A44",
    "secundario": "#0B2035",
    "acento": "#F2A900",
    "texto_secundario": "#8EA8C3",
}

FUENTES_LOGO_VOGEL = [
    r"O:\vogel_consultoria\src\assets\brand\logo-vogel-generated.png",
    r"O:\vogel_consultoria\src\assets\logo-vogel.png",
    r"O:\vogel_consultoria\public\logo-vogel.png",
    r"O:\vogel_consultoria\dist\logo-vogel.png",
]


@dataclass
class ConfigMarcaFactura:
    activa: bool = False
    formato: str = ""
    logo: str = ""
    fondo: str = ""
    web: str = ""
    leyenda: str = ""
    color_primario: str = "#0F2A44"
    color_secundario: str = "#0B2035"
    color_acento: str = "#F2A900"
    color_texto_secundario: str = "#8EA8C3"


@dataclass
class AssetsEjemploMarca:
    logo: Path
    fondo: Path


def cargar_config_marca_factura():
    from modelos.ParametrosSistema import ParamSist

    return ConfigMarcaFactura(
        activa=_es_si(_leer_parametro(ParamSist, "FACTURA_MARCA_ACTIVA", "N")),
        # Vacio a proposito: la marca se SUMA encima de la plantilla fiscal de
        # siempre, que tiene las lineas de la grilla y los cuadros de los
        # totales. Antes el default era factura_marca.csv, un diseno mas pobre,
        # y con eso activar la marca hacia perder el formato fiscal sin
        # avisar. Para usar otra plantilla a proposito se la carga en el
        # parametro, y la pantalla lo ofrece como opcion.
        formato=_leer_parametro(ParamSist, "FACTURA_MARCA_FORMATO", ""),
        logo=_leer_parametro(ParamSist, "FACTURA_MARCA_LOGO", ""),
        fondo=_leer_parametro(ParamSist, "FACTURA_MARCA_FONDO", ""),
        web=_leer_parametro(ParamSist, "FACTURA_MARCA_WEB", ""),
        leyenda=_leer_parametro(ParamSist, "FACTURA_MARCA_LEYENDA", ""),
        color_primario=_leer_parametro(ParamSist, "FACTURA_MARCA_COLOR_PRIMARIO", "#0F2A44"),
        color_secundario=_leer_parametro(ParamSist, "FACTURA_MARCA_COLOR_SECUNDARIO", "#0B2035"),
        color_acento=_leer_parametro(ParamSist, "FACTURA_MARCA_COLOR_ACENTO", "#F2A900"),
        color_texto_secundario=_leer_parametro(ParamSist, "FACTURA_MARCA_COLOR_TEXTO_SECUNDARIO", "#8EA8C3"),
    )


def aplicar_marca_factura_con_parametros(pyfpdf, base_dir):
    return aplicar_marca_factura(pyfpdf, base_dir, cargar_config_marca_factura())


def obtener_formato_factura(base_dir, config, formato_default):
    base = Path(base_dir)
    default = _resolver_path(base, formato_default)
    if not config.activa or not config.formato:
        return default

    formato = _resolver_path(base, config.formato)
    if formato and formato.exists():
        return formato
    return default


def aplicar_marca_factura(pyfpdf, base_dir, config):
    """Agrega la capa de marca encima de la plantilla que ya se cargo.

    Devuelve la lista de lo que NO se pudo aplicar, para que la pantalla lo
    diga. Antes devolvia un booleano y se comia el motivo.

    Importante: cada parte es independiente. No hace falta tener logo para que
    salgan la web, la leyenda y el fondo. Antes el 'return False' por falta de
    logo se llevaba TODO, y un cliente que quiere solo su color de acento se
    quedaba sin marca y sin aviso.
    """
    if not config.activa:
        return []

    pendientes = []
    base = Path(base_dir)
    logo = _resolver_path(base, config.logo)
    fondo = _resolver_path(base, config.fondo)

    if logo and logo.exists():
        pyfpdf.AgregarDato("logo", str(logo))
    elif config.logo:
        # Se pidio un logo con una ruta que no existe. No se aborta el resto.
        pendientes.append("el logo {}".format(config.logo))

    if fondo and fondo.exists():
        pyfpdf.AgregarCampo(
            "marca-fondo",
            "I",
            0,
            0,
            210,
            297,
            None,
            0,
            0,
            0,
            0,
            0,
            0,
            "I",
            str(fondo),
            -20,
        )
    elif config.fondo:
        pendientes.append("el fondo {}".format(config.fondo))

    if config.web:
        pyfpdf.AgregarCampo(
            "marca-web",
            "T",
            139,
            38.4,
            205.6,
            42.6,
            "Arial",
            8,
            True,
            False,
            False,
            _hex_a_int(config.color_primario),
            0xFFFFFF,
            "D",
            config.web,
            2,
        )

    if config.leyenda:
        pyfpdf.AgregarCampo(
            "marca-leyenda",
            "T",
            104.2,
            274.8,
            181,
            279,
            "Arial",
            7,
            False,
            False,
            False,
            _hex_a_int(config.color_texto_secundario),
            0xFFFFFF,
            "C",
            config.leyenda,
            2,
        )

    return pendientes


def crear_ejemplo_vogel(base_dir, fuentes_logo=None):
    base = Path(base_dir)
    plantillas = base / "plantillas"
    plantillas.mkdir(parents=True, exist_ok=True)

    logo_destino = plantillas / "logo-vogel-ejemplo.png"
    fondo_destino = plantillas / "factura-fondo-vogel-ejemplo.png"

    if not logo_destino.exists():
        logo_origen = _primer_archivo_existente(fuentes_logo or FUENTES_LOGO_VOGEL)
        if logo_origen:
            copy2(str(logo_origen), str(logo_destino))

    if not fondo_destino.exists():
        _crear_fondo_factura(
            fondo_destino,
            color_primario=VOGEL_COLORES["primario"],
            color_secundario=VOGEL_COLORES["secundario"],
            color_acento=VOGEL_COLORES["acento"],
        )

    return AssetsEjemploMarca(logo=logo_destino, fondo=fondo_destino)


def _resolver_path(base, valor):
    if not valor:
        return None
    path = Path(valor)
    if path.is_absolute():
        return path
    return base / path


def _leer_parametro(modelo_parametro, nombre, defecto=""):
    try:
        return modelo_parametro.select().where(modelo_parametro.parametro == nombre).get().valor
    except modelo_parametro.DoesNotExist:
        return defecto


def _es_si(valor):
    return str(valor or "").strip().upper() in ["S", "SI", "TRUE", "1"]


def _primer_archivo_existente(rutas):
    for ruta in rutas:
        archivo = Path(ruta)
        if archivo.exists():
            return archivo
    return None


def _hex_a_int(color):
    color = str(color or "#000000").strip().lstrip("#")
    if len(color) != 6:
        color = "000000"
    return int(color, 16)


def _color_rgb(color):
    color = str(color or "#000000").strip().lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def _crear_fondo_factura(destino, color_primario, color_secundario, color_acento):
    ancho, alto = 1240, 1754
    escala_x = ancho / 210.0
    escala_y = alto / 297.0
    pixeles = bytearray([255, 255, 255] * ancho * alto)

    def mezclar(pos, color, alpha=255):
        r, g, b = _color_rgb(color)
        inv = 255 - alpha
        pixeles[pos] = (r * alpha + pixeles[pos] * inv) // 255
        pixeles[pos + 1] = (g * alpha + pixeles[pos + 1] * inv) // 255
        pixeles[pos + 2] = (b * alpha + pixeles[pos + 2] * inv) // 255

    def rect(x1, y1, x2, y2, color, alpha=255):
        x1 = max(0, int(x1))
        y1 = max(0, int(y1))
        x2 = min(ancho, int(x2))
        y2 = min(alto, int(y2))
        for y in range(y1, y2):
            fila = y * ancho * 3
            for x in range(x1, x2):
                mezclar(fila + x * 3, color, alpha)

    rect(0, 0, ancho, 8.8 * escala_y, color_secundario)
    rect(0, 8.8 * escala_y, ancho, 9.8 * escala_y, color_acento)
    rect(0, 0, 3.2 * escala_x, alto, color_primario)
    rect(122 * escala_x, 11 * escala_y, 207 * escala_x, 43 * escala_y, "#F8FAFC", 255)
    rect(8 * escala_x, 48 * escala_y, 207 * escala_x, 75 * escala_y, color_primario, 10)
    rect(8 * escala_x, 82 * escala_y, 207 * escala_x, 89 * escala_y, color_primario, 255)
    rect(8 * escala_x, 89 * escala_y, 207 * escala_x, 226 * escala_y, "#F8FAFC", 255)
    rect(148 * escala_x, 232 * escala_y, 207 * escala_x, 265 * escala_y, color_primario, 9)
    rect(148 * escala_x, 263.5 * escala_y, 207 * escala_x, 265 * escala_y, color_acento, 80)
    rect(8 * escala_x, 242 * escala_y, 110 * escala_x, 286 * escala_y, "#F8FAFC", 255)
    rect(8 * escala_x, 242 * escala_y, 110 * escala_x, 243 * escala_y, color_acento, 120)
    rect(148 * escala_x, 280 * escala_y, 207 * escala_x, 286.8 * escala_y, color_acento, 45)

    destino.parent.mkdir(parents=True, exist_ok=True)
    _guardar_png_rgb(destino, ancho, alto, pixeles)


def _guardar_png_rgb(destino, ancho, alto, pixeles):
    def chunk(tipo, datos):
        return (
            struct.pack(">I", len(datos))
            + tipo
            + datos
            + struct.pack(">I", zlib.crc32(tipo + datos) & 0xFFFFFFFF)
        )

    filas = []
    largo_fila = ancho * 3
    for y in range(alto):
        inicio = y * largo_fila
        filas.append(b"\x00" + bytes(pixeles[inicio:inicio + largo_fila]))

    datos = b"".join(filas)
    contenido = [
        b"\x89PNG\r\n\x1a\n",
        chunk(b"IHDR", struct.pack(">IIBBBBB", ancho, alto, 8, 2, 0, 0, 0)),
        chunk(b"IDAT", zlib.compress(datos, 6)),
        chunk(b"IEND", b""),
    ]
    Path(destino).write_bytes(b"".join(contenido))
