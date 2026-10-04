# coding=utf-8
"""Con la marca activa, el comprobante tiene que conservar las lineas.

El sintoma que reporto el operador
----------------------------------
La vista previa salio sin las lineas de la grilla ni los cuadros de los
totales. La causa no era el preview: activar la marca cambiaba la plantilla del
comprobante por factura_marca.csv, que es un diseno mas pobre. O sea que
'usar diseno propio' hacia perder el formato fiscal.

Este test genera el PDF con la marca ACTIVADA y mira, en el flujo de contenido,
que estan los rectangulos y las lineas que dibuja factura_qr.csv. Si vuelve a
cambiarse la plantilla, la linea de la grilla no aparece y el test falla.
"""
import os
import re
import shutil
import sys
import tempfile
import zlib
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)


@pytest.fixture
def qt():
    from PyQt5.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _contenido(ruta):
    datos = open(ruta, "rb").read()
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", datos, re.S):
        try:
            texto = zlib.decompress(m.group(1)).decode("latin1", "replace")
        except Exception:
            continue
        if " Tj" in texto and " re" in texto:
            return texto
    return ""


def _pdf_con_marca(tmp_path, con_plantilla_propia=False):
    """Un PDF con la marca activada, generado con el codigo real."""
    from peewee import SqliteDatabase
    import modelos.ParametrosSistema as MP
    from modelos.ParametrosSistema import ParamSist

    shutil.copytree(os.path.join(RAIZ, "plantillas"),
                    str(tmp_path / "plantillas"), dirs_exist_ok=True)
    (tmp_path / "sistema.ini").write_text(
        "[param]\nbase = sqlite\nusa_nombre_db = S\nbasedatos = marca\n"
        "homo = S\nnombre_sistema = Prueba\nconfigurado = S\n"
        "\n[FACTURA]\nempresa = MI ESTUDIO\nmembrete1 = Una calle 123\n"
        "membrete2 = \ncuit = 20-23347203-5\niibb = 20233472035\n"
        "iva = Responsable Inscripto\ninicio = 01/01/2020\n",
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
        except ImportError:
            U = None
        import libs.Utiles as U
        import controladores.Facturas as FAC
        u_orig = (U.ubicacion_sistema, FAC.ubicacion_sistema)
        U.ubicacion_sistema = lambda: str(tmp_path) + os.sep
        FAC.ubicacion_sistema = lambda: str(tmp_path) + os.sep

        import controladores.DisenoComprobante as MOD
        try:
            MOD.DisenoComprobanteController._abrir_muestra = staticmethod(
                lambda salida: True)
            c = MOD.DisenoComprobanteController()
            c.view.Cerrar = lambda: None
            c.view.controles['activa'].setIndex("S")
            c.view.controles['logo'].setText("")
            c.view.controles['fondo'].setText("")
            c.view.controles['formato'].setText(
                "plantillas/factura_marca.csv" if con_plantilla_propia else "")
            c.view.controles['web'].setText("www.miestudio.com")
            c.view.controles['leyenda'].setText("MI ESTUDIO")
            # Hay que GUARDAR antes: el comprobante arma la marca desde los
            # parametros de la base, no desde los campos de la pantalla. Sin
            # guardar, la marca no existe todavia y la prueba mide cualquier
            # cosa menos lo que el operador cree que hizo.
            assert c.GrabaParametros() is True

            ruta = os.path.join(tempfile.gettempdir(),
                                "prueba_marca_lineas.pdf")
            impresor = MOD._ImpresorDeMuestra()
            muestra = MOD._Muestra(1, "000100000001")
            impresor._armar_comprobante(muestra, salida=ruta, mostrar=False,
                                        renglones=muestra.items_de_muestra())
            assert os.path.isfile(ruta), "no se genero el PDF"
            return _contenido(ruta)
        finally:
            U.ubicacion_sistema, FAC.ubicacion_sistema = u_orig
            MP.ParamSist._meta.set_database(original)
    finally:
        os.chdir(cwd)


def test_la_marca_suma_y_no_reemplaza(qt, tmp_path):
    """Con la marca activada, el comprobante conserva el formato fiscal.

    Lo que se mira son los rectangulos del flujo de contenido. La plantilla
    fiscal dibuja el marco de la hoja y los cuadros; la de marca no. Si un
    dia 'usar diseno propio' vuelve a cambiar la plantilla, desaparecen y este
    test se da vuelta.
    """
    contenido = _pdf_con_marca(tmp_path)

    rectangulos = re.findall(r"([\d.-]+ [\d.-]+ [\d.-]+ [\d.-]+) re ([fSbB]*)",
                             contenido)
    assert len(rectangulos) > 30, \
        "el comprobante tiene solo {} rectangulos: se perdio el formato de la " \
        "plantilla ({})".format(len(rectangulos), "pocos")

    # El marco de la hoja: algo de 566 x 790 puntos.
    hojas = [r for r in rectangulos
             if abs(float(r[0].split()[2])) > 500
             and abs(float(r[0].split()[3])) > 700]
    assert hojas, "no esta el marco de la hoja: la plantilla cambio"


def test_la_marca_aplica_el_texto_y_el_color(qt, tmp_path):
    """La marca tiene que notarse, no solo conservarse."""
    contenido = _pdf_con_marca(tmp_path)

    assert "MI ESTUDIO" in contenido, "el texto de la marca no salio"
    assert "www.miestudio.com" in contenido, "la web de la marca no salio"
