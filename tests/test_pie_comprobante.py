"""El pie del comprobante tiene que salir entero en el PDF.

Que pasaba
---------
El separador del pie era el caracter medio '·' (U+00B7). En el PDF salia como
un caracter de reemplazo:

    Desarrollo de Vogel Consultoria \ufffd vogelconsultoria.com.ar \ufffd ...

Comprobado sobre un PDF de muestra real, no leyendo el codigo. Los PDF se arman
con las fuentes base de fpdf2, y ese caracter no esta en la fuente que termina
usando.

El texto es nuestro: es una constante del proyecto, no algo que venga de la base
ni de un archivo del cliente. No hace falta pelear con la codificacion de la
libreria para separar tres cosas.

El test que importa es el ultimo: arma un PDF de verdad y mira los textos que
quedaron adentro. Un test que solo mira la constante pasaria aunque el
problema estuviera en la libreria.
"""
import os
import re
import sys
import zlib
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from libs.Constantes import CREDITO_SOFTWARE  # noqa: E402


@pytest.fixture
def qt():
    """Sin QApplication, construir el controlador mata el proceso."""
    from PyQt5.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_el_pie_se_arma_solo_con_caracteres_de_winansi():
    """Lo que las fuentes base de fpdf2 pueden dibujar.

    Si aparece un caracter fuera de ahi, el comprobante sale con un cuadrado o
    un signo de reemplazo. Un test, en vez de un comprobante de un cliente.
    """
    fuera = [c for c in CREDITO_SOFTWARE if ord(c) > 255]
    assert not fuera, \
        "el pie tiene caracteres que el PDF no sabe dibujar: {}".format(
            [hex(ord(c)) for c in fuera])


def test_el_pie_no_usa_el_medio_que_salia_roto():
    assert "·" not in CREDITO_SOFTWARE, \
        "el separador del pie volvio a ser el caracter medio"


def _texto_del_pdf(ruta):
    """Los textos que quedaron dibujados adentro del PDF."""
    datos = open(ruta, "rb").read()
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", datos, re.S):
        try:
            contenido = zlib.decompress(m.group(1)).decode("latin1", "replace")
        except Exception:
            continue
        if " Tj" in contenido:
            return re.findall(r"\((.*?)\) Tj", contenido)
    return []


def test_el_pdf_real_no_tiene_caracteres_de_reemplazo(qt, tmp_path):
    """Arma un comprobante de verdad y mira lo que quedo escrito.

    Este es el que hubiera atrapado el problema: el constante estaba bien en el
    fuente, y lo que se rompia era lo que quedaba dibujado en el PDF.
    """
    import shutil

    from peewee import SqliteDatabase
    import modelos.ParametrosSistema as MP
    from modelos.ParametrosSistema import ParamSist

    shutil.copytree(os.path.join(RAIZ, "plantillas"),
                    str(tmp_path / "plantillas"), dirs_exist_ok=True)
    (tmp_path / "sistema.ini").write_text(
        "[param]\nbase = sqlite\nusa_nombre_db = S\nbasedatos = pie\n"
        "homo = S\nnombre_sistema = Prueba\nconfigurado = S\n"
        "\n[FACTURA]\nempresa = UNA EMPRESA CON Ñ Y Á\n"
        "membrete1 = Una calle 123\nmembrete2 = \ncuit = 20-23347203-5\n"
        "iibb = 20233472035\niva = Responsable Inscripto\n"
        "inicio = 01/01/2020\n",
        encoding="utf-8")

    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        db = SqliteDatabase(":memory:")
        original = MP.ParamSist._meta.database
        MP.ParamSist._meta.set_database(db)
        db.create_tables([ParamSist])
        db.connect(reuse_if_open=True)
        try:
            import libs.Utiles as U
            import controladores.Facturas as FAC
            u_orig = (U.ubicacion_sistema, FAC.ubicacion_sistema)
            U.ubicacion_sistema = lambda: str(tmp_path) + os.sep
            FAC.ubicacion_sistema = lambda: str(tmp_path) + os.sep
            try:
                import controladores.DisenoComprobante as MOD
                impresor = MOD._ImpresorDeMuestra()
                muestra = MOD._Muestra(1, "000100000001")
                salida = str(tmp_path / "pie.pdf")
                impresor._armar_comprobante(
                    muestra, salida=salida, mostrar=False,
                    renglones=muestra.items_de_muestra())
            finally:
                U.ubicacion_sistema, FAC.ubicacion_sistema = u_orig
        finally:
            MP.ParamSist._meta.set_database(original)
    finally:
        os.chdir(cwd)

    assert os.path.isfile(salida), "no se genero el PDF"
    textos = _texto_del_pdf(salida)
    assert textos, "el PDF no tiene texto: el chequeo no sirve"

    rotos = [t for t in textos if "\ufffd" in t or "�" in t]
    assert not rotos, "en el PDF quedaron caracteres de reemplazo: {}".format(
        rotos)
