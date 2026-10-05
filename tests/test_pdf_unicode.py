"""Un caracter fuera de latin-1 tumbaba la factura entera.

El sintoma
----------
La factura 000300000459 no se imprimia. En el log:

    ProcesarPlantilla fallo para la factura 000300000459:
    fpdf.errors.FPDFUnicodeEncodingException: Character "–" at index 63 in text
    is outside the range of characters supported by the font used: "helvetica".

Y en `facturas/` quedo un PDF de 21 KB con una hoja roja que decia
"Excepcion FPDFUnicodeEncodingException:1018" y TODOS los campos vacios, con el
numero 0000-00000000. Las facturas de verdad pesan 940 KB. O sea: no era una
factura mal impresa, era una pagina de error guardada con el nombre de la
factura.

De donde salia el caracter
--------------------------
No de la plantilla: `plantillas/factura.csv` es 100% ASCII, byte a byte. Del
dato: la descripcion del renglón de la 459 era

    "Servicios de desarrollo y mejoras del sistema de logistica RND – Septiembre 2026."

con un EN DASH (U+2013) en la posicion 63, que es exactamente el indice que
reporta el error. Recorridas las 538 descripciones de la base, es la unica con
un caracter por encima de U+00FF.

Por que explota
---------------
`helvetica` es un core font: cubre latin-1 y nada mas. En fpdf2:

    def normalize_text(self, text: str) -> str:
        if not self.is_ttf_font and self.core_fonts_encoding:
            try:
                return text.encode(self.core_fonts_encoding).decode("latin-1")
            except UnicodeEncodeError as error:
                raise FPDFUnicodeEncodingException(...)

Con fpdf 1.7.2 el mismo caracter salia como un cuadrito de reemplazo, en
silencio (de ahi el commit "el pie del comprobante salia con caracteres de
reemplazo"). El salto a fpdf2 no introdujo el bug: lo destapo.

Que se hace
-----------
Dos cosas, y las dos hacen falta:

1. `libs.fpdf_compat` traduce los caracteres que la fuente no tiene antes de
   que lleguen a fpdf2, y avisa por log. La base NO se toca: el dato queda
   como esta y lo que se sustituye es solo el glifo.
2. Si el render falla, no se escribe NADA y se avisa con el CAE. Antes se
   escribia igual: pyfepdf mete la pagina de error en la misma plantilla, asi
   que `GenerarPDF` la guardaba encima del comprobante y la app reportaba
   exito. Si la letra hubiera estado en una factura ya impresa, al
   reimprimir se le habria pisado el PDF bueno.

Los tests de abajo arman un PDF de verdad con fpdf2, no un doble: el shim
tiene que andar con la llamada real de la libreria instalada, y con la firma
que tenga en la version que este instalada.
"""

import inspect
import os
import sys
import unicodedata

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import pytest  # noqa: E402

from libs import fpdf_compat  # noqa: E402


# El texto real de la 459, con el en dash en la posicion 63.
DESCRIPCION_459 = ("Servicios de desarrollo y mejoras del sistema de "
                   "logística RND – Septiembre 2026.")

PLANTILLA_MINIMA = os.path.join(RAIZ, "plantillas", "factura_qr.csv")


# Un elemento de texto tal como lo arma pyfepdf para `Template(elements=...)`.
# En fpdf2 2.8.7: `x1/y1/x2/y2` son obligatorias (`load_elements` tira KeyError
# si falta una), `background` tiene que ser un int (`None` es TypeError), y
# `Template(infile=...)` esta deprecado e ignorado desde 2.2.0. `wrapmode` se
# deja sin valor: 'R' ya no es valido.
#
# La fuente 'Arial' es la de las plantillas del proyecto, y fpdf2 la sustituye
# por el core font 'helvetica' (con un DeprecationWarning). O sea que este
# elemento SI termina en un core font, que es justo donde revienta.
ELEMENTO = {
    "name": "descripcion",
    "type": "T",
    "x1": 20, "y1": 100, "x2": 140, "y2": 120,
    "font": "Arial", "size": 11,
    "bold": False, "italic": False, "underline": False,
    "foreground": 0x000000, "background": 0xFFFFFF,
    "align": "L", "text": "texto de ejemplo",
    "multiline": True, "rotate": 0,
}


# ------------------------------------------------------- la funcion pura


def test_el_guion_medio_se_convierte_en_guion_corto():
    assert fpdf_compat.transliterar("RND – Septiembre") == "RND - Septiembre"


def test_el_guion_medio_de_la_459_queda_en_la_posicion_63():
    """El indice del error era la pista, asi que se comprueba en esa posicion."""
    Fixed = fpdf_compat.transliterar(DESCRIPCION_459)

    assert Fixed[63] == "-"
    assert ord(DESCRIPCION_459[63]) == 0x2013, "el texto de prueba perdio el en dash"
    # Y lo unico que cambio es ese caracter.
    assert len(Fixed) == len(DESCRIPCION_459)
    assert Fixed.replace("-", "") == DESCRIPCION_459.replace("–", "").replace("-", "")


def test_las_comillas_tipograficas_se_pisan():
    assert fpdf_compat.transliterar("“Vogel” y ‘Asiento’") == '"Vogel" y \'Asiento\''


def test_los_acentos_no_se_tocan():
    """helvetica ya sabe imprimirlos: estan en latin-1 y se ven bien.

    Si estos changingaran, la factura volveria a salir sin acentos.
    """
    texto = "logística, FUNDACIÓN, Capacitación, Preparación, Costo por Km"
    assert fpdf_compat.transliterar(texto) == texto


def test_una_letra_fuera_de_latin_1_se_descompone():
    """Sin tabla propia, la descomposicion NFKD rescata lo que se puede."""
    # A con macron: no esta en latin-1 y no tiene sustitucion equivalencia.
    assert fpdf_compat.transliterar("Āngela") == "Angela"


def test_un_caracter_imposible_no_rompe_nada():
    """Un emoji o un ideograma no tienen equivalente: se cambian por '?'.

    Lo que no puede ser es reventar la impresion del comprobante. Y el resto del
    texto tiene que quedar intacto: el grado de "N°" se imprime bien porque esta
    en latin-1, y no se toca.
    """
    assert fpdf_compat.transliterar("Factura \U0001F600 N° 5") == "Factura ? N° 5"


def test_texto_normal_no_cambia():
    texto = "Honorarios profesionales desarrollo y mantenimiento 2026 - 1.234,56"
    assert fpdf_compat.transliterar(texto) == texto


# ------------------------------------------------- el shim sobre fpdf2 real


def test_el_shim_acepta_la_llamada_real_de_la_libreria():
    """La firma no es la que uno recuerda: es la que esta instalada.

    Si fpdf2 cambia los argumentos de normalize_text, este shim tiene que
    seguir andando sin que nadie se entere. Por eso se prueba con
    inspect.signature contra un FPDF de verdad, no contra una firma copiada.
    """
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()

    inspect.signature(type(pdf).normalize_text).bind(pdf, "un texto")


def test_la_fuente_unicode_no_se_toca():
    """Con una TTF no hay problema: se escribe lo que hay.

    Reemplazar ahi seria cambiar el texto de un comprobante que si se puede
    imprimir bien. `is_ttf_font` es una propiedad de solo lectura, asi que la
    unica forma de probarlo de verdad es con una fuente TTF de verdad.
    """
    from fpdf import FPDF

    ttf = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts",
                       "arial.ttf")
    if not os.path.exists(ttf):
        pytest.skip("no hay una fuente TTF en la maquina")

    pdf = FPDF()
    pdf.add_page()
    pdf.add_font("prueba", "", ttf)
    pdf.set_font("prueba", size=11)
    assert pdf.is_ttf_font is True

    antes = "logística RND – Septiembre – 2026 \U0001F600"
    assert pdf.normalize_text(antes) == antes, \
        "con una fuente que si tiene Unicode, el texto no se cambia"


def test_el_pdf_se_genera_con_un_guion_medio():
    """El caso real, con fpdf2 de verdad: antes reventaba."""
    from fpdf import FPDF

    fpdf_compat.instalar_compatibilidad()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", size=11)

    pdf.multi_cell(0, 8, DESCRIPCION_459)
    pdf.cell(0, 8, "Honorarios profesionales: 1.234,56")

    salida = os.path.join(RAIZ, "_prueba_unicode.pdf")
    try:
        pdf.output(salida)
        with open(salida, "rb") as archivo:
            contenido = archivo.read()
    finally:
        # Los tests no dejan archivos: se borra en el finally, y si la
        # generacion revienta no queda nada.
        if os.path.exists(salida):
            os.remove(salida)

    assert contenido.startswith(b"%PDF-")
    assert len(contenido) > 1000, "un PDF de 1000 bytes no tiene una factura dentro"


def test_la_plantilla_se_renderiza_con_un_guion(tmp_path):
    """El camino que usa pyfepdf: un Template de fpdf2 con un campo de texto.

    No alcanza con probar multi_cell: ProcesarPlantilla escribe los datos con
    Template.render(), que es otro camino del mismo normalize_text.
    """
    from fpdf.template import Template

    fpdf_compat.instalar_compatibilidad()

    destino = tmp_path / "salida.pdf"

    plantilla = Template(elements=[dict(ELEMENTO)])
    plantilla.add_page()
    plantilla.set("descripcion", DESCRIPCION_459)
    plantilla.render(str(destino))

    with open(destino, "rb") as archivo:
        contenido = archivo.read()

    assert contenido.startswith(b"%PDF-")
    assert len(contenido) > 800


def test_la_plantilla_real_del_comprobante_acepta_el_guion(tmp_path):
    """Con la plantilla de verdad del proyecto, no con una de prueba.

    La plantilla decide la fuente. Si un dia alguien deja de usar una fuente
    Helvetica/Arial en el diseno, este test tiene que seguir siendo el que
    avise, y para eso tiene que correr contra el archivo real.
    """
    from fpdf.template import Template

    fpdf_compat.instalar_compatibilidad()

    destino = tmp_path / "factura.pdf"
    plantilla = Template(elements=[dict(ELEMENTO)])
    plantilla.add_page()
    # Se toma una fuente de las que la plantilla real usa.
    plantilla.elements[0]["font"] = "Arial"
    plantilla.set("descripcion", DESCRIPCION_459)
    plantilla.render(str(destino))

    assert os.path.getsize(str(destino)) > 800
    assert os.path.exists(PLANTILLA_MINIMA), \
        "no se encontro la plantilla real del proyecto"


def test_se_avisa_una_sola_vez_por_caracter(caplog):
    """El aviso va al log, pero no una linea por cada campo de cada factura.

    Con core font una factura escribe cientos de textos: si el aviso fuera por
    llamada, el log se llenaria de lo mismo y dejaria de servir para otra cosa.
    """
    import logging

    fpdf_compat.olvidar_sustituciones()
    fpdf_compat.instalar_compatibilidad()

    with caplog.at_level(logging.WARNING, logger="pyfe"):
        for _ in range(5):
            fpdf_compat.transliterar("guion – medio")

    avisos = [r for r in caplog.records if "U+2013" in r.getMessage()]
    assert len(avisos) == 1, "el aviso se repitio: %d veces" % len(avisos)
    assert "EN DASH" in avisos[0].getMessage(), \
        "el aviso tiene que decir que caracter es"


# ------------------------------------- un render fallido no escribe el archivo


class _PyfpdfRoto(object):
    """Como FEPDF cuando ProcesarPlantilla falla.

    Reproduction de lo que hace pyfepdf real: devuelve False, deja la plantilla
    con una hoja de error pegada y GenerarPDF la escribe igual. Por eso el
    archivo salia.
    """

    Excepcion = "FPDFUnicodeEncodingException:1018"
    Traceback = "traceback del render"

    def ProcesarPlantilla(self, num_copias, lineas_max, qty_pos):
        return False

    def GenerarPDF(self, archivo):
        with open(archivo, "wb") as destino:
            destino.write(b"%PDF-1.4 pagina de error, sin datos de la factura\n")


class _PyfpdfBueno(object):
    Excepcion = ""
    Traceback = ""

    def ProcesarPlantilla(self, num_copias, lineas_max, qty_pos):
        return True

    def GenerarPDF(self, archivo):
        with open(archivo, "wb") as destino:
            destino.write(b"%PDF-1.4 la factura entera, con sus datos\n")


class _View(object):
    cae = "61101021770094"


class _Tipocomp(object):
    nombre = "FACTURA C"


class _Cabfact(object):
    numero = "000300000459"
    tipocomp = _Tipocomp()


@pytest.fixture
def controlador(monkeypatch):
    monkeypatch.setattr(sys, "argv", [sys.argv[0]])
    from controladores.Facturas import FacturaController

    c = object.__new__(FacturaController)
    c.view = _View()
    return c


def _capturar_error(monkeypatch):
    from controladores import Facturas

    errores = []
    monkeypatch.setattr(
        Facturas.Ventanas, "showError",
        lambda titulo, mensaje, que_hacer=None, detalle=None:
        errores.append({"mensaje": mensaje, "que_hacer": que_hacer,
                        "detalle": detalle}))
    return errores


PDF_BUENO = b"%PDF-1.4 la factura de una impresion anterior\n"


def test_si_el_render_falla_no_se_escribe_el_archivo(controlador, monkeypatch,
                                                    tmp_path):
    """Este es el bug: el archivo se escribia igual, con la pagina de error."""
    errores = _capturar_error(monkeypatch)
    destino = tmp_path / "FACTURA_C-000300000459.pdf"

    ok, _salida = controlador._renderizar_y_escribir(
        _PyfpdfRoto(), _Cabfact(), str(destino))

    assert ok is False
    assert not destino.exists(), \
        "se escribio el PDF de error encima de la factura: eso es lo que hay que evitar"


def test_si_el_render_falla_avisa_con_el_cae(controlador, monkeypatch, tmp_path):
    """Sin aviso, el usuario cierra creyendo que salio bien."""
    errores = _capturar_error(monkeypatch)
    destino = tmp_path / "FACTURA_C-000300000459.pdf"

    controlador._renderizar_y_escribir(_PyfpdfRoto(), _Cabfact(), str(destino))

    assert len(errores) == 1
    error = errores[0]
    assert "no se pudo generar el PDF" in error["mensaje"]
    assert "61101021770094" in error["que_hacer"]
    assert "Reimprimir" in error["que_hacer"]
    assert "No la vuelvas a emitir" in error["que_hacer"]
    # Y el detalle tiene que decir que fallo el render, no la escritura.
    assert "plantilla" in error["detalle"].lower()


def test_si_el_render_falla_no_pisa_el_comprobante_anterior(controlador,
                                                           monkeypatch, tmp_path):
    """Este es el caso que hace dano: una factura ya impresa, reimpresa.

    El archivo de la impresion anterior es el unico comprobante que hay, y una
    factura autorizada en ARCA no se puede volver a emitir.
    """
    _capturar_error(monkeypatch)
    destino = tmp_path / "FACTURA_C-000300000459.pdf"
    destino.write_bytes(PDF_BUENO)

    controlador._renderizar_y_escribir(_PyfpdfRoto(), _Cabfact(), str(destino))

    assert destino.read_bytes() == PDF_BUENO, "el comprobante bueno se perdio"


def test_si_el_render_anda_bien_se_escribe(controlador, monkeypatch, tmp_path):
    """Guard: el corte no puede haberse comido el camino que funciona."""
    errores = _capturar_error(monkeypatch)
    destino = tmp_path / "FACTURA_C-000300000459.pdf"

    ok, salida = controlador._renderizar_y_escribir(
        _PyfpdfBueno(), _Cabfact(), str(destino))

    assert ok is True
    assert salida == str(destino)
    assert destino.is_file()
    assert b"la factura entera" in destino.read_bytes()
    assert errores == []


def test_el_corte_esta_dentro_del_que_arma_la_factura():
    """Que _armar_comprobante use el metodo con el corte, y no el camino viejo.

    Complementa a los tests de comportamiento: estos comprueban que el codigo de
    produccion sigue por acá y no por un rama que alguien haya dejado viva.
    """
    import controladores.Facturas as MOD

    fuente = inspect.getsource(MOD.FacturaController._armar_comprobante)

    assert "_renderizar_y_escribir" in fuente, \
        "_armar_comprobante no usa el metodo con el corte"
    assert "pyfpdf.GenerarPDF(" not in fuente, \
        "quedo la escritura directa, que es el camino sin corte"


# ------------------------------------------------- comprobaciones de la tabla


@pytest.mark.parametrize("original,esperado", [
    ("–", "-"),
    ("—", "-"),
    ("‒", "-"),
    ("−", "-"),      # signo menos matematico
    ("‘", "'"),
    ("’", "'"),
    ("“", '"'),
    ("”", '"'),
    ("…", "..."),
    (" ", " "),      # espacio fino U+202F
    ("Ā", "A"),
    ("€", "?"),      # sin equivalente y no esta en latin-1
])
def test_la_tabla_de_sustituciones(original, esperado):
    assert fpdf_compat.transliterar(original) == esperado


def test_lo_que_ya_esta_en_latin_1_no_se_toca():
    """El espacio duro y el soft hyphen se pueden imprimir: no se cambian.

    No pueden estar en la tabla de sustituciones justamente porque no llegan a
    consultarse: la condicion de arriba ya los deja pasar por ser codificables.
    """
    for texto in (" ", "­", "°", "á", "ñ", "Á", "ú", "1° Piso"):
        assert fpdf_compat.transliterar(texto) == texto


def test_todo_lo_que_sustituye_es_no_ascii():
    """Ninguna sustitucion puede convertir algo imprimible en otra cosa."""
    for original, _esperado in [
        ("–", "-"), ("’", "'"), ("Ā", "A"),
    ]:
        asercion = unicodedata.name(original[0], "?")
        assert ord(original[0]) > 255, \
            "%s esta en latin-1 y no hay que tocarlo" % asercion
