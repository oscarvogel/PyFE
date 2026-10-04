# coding=utf-8
"""Tests de _pdf_generado, el aviso de 'no se pudo generar el PDF'.

Que estaba pasando
------------------
GenerarPDF devuelve None aunque el PDF se haya generado bien: con fpdf2
(fpdf 2.8.7) Template.render() esta anotado -> None, escribe el archivo y no
devuelve nada. Y _pdf_generado hacia `if ok and os.path.isfile(salida)`, o
sea que exigia un valor de retorno que la libreria ya no da.

Efecto: cada factura impresa avisaba "La factura se autorizo pero no se pudo
generar el PDF" CON el PDF generado, y dejaba facturaGenerada en None. Con
fpdf 1.7, que es de donde venia el proyecto, render() si devolvia algo
verdadero; el proyecto migro a fpdf2 y el chequeo se dio vuelta sin que nadie
lo notara.

Estos tests no dependen de la base ni de ARCA: llaman al metodo directo con un
archivo de verdad.
"""

import io
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class _Falso(object):
    def __init__(self, **atributos):
        self.__dict__.update(atributos)


@pytest.fixture
def qt():
    """FacturaController construye widgets, y sin QApplication el proceso
    muere con STATUS_STACK_BUFFER_OVERRUN, sin dejar traceback."""
    from PyQt5.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture
def avisos(monkeypatch):
    """Anota los showError en vez de hacerlos.

    Hay tests cuyo resultado correcto ES que avise, asi que el showError no
    puede ser un fallo automatico. Se anotan y cada test decide.
    """
    import libs.Ventanas as V

    vistos = []
    monkeypatch.setattr(V, "showError",
                        lambda titulo, mensaje, **kw: vistos.append(
                            (titulo, mensaje)))
    return vistos


@pytest.fixture
def sin_avisos(avisos):
    """Para los tests que NO deben avisar: si avisa, es un fallo."""
    def _fallar():
        if avisos:
            pytest.fail("no deberia haber avisado: {}".format(avisos))
    yield _fallar


@pytest.fixture
def controlador(qt, avisos, tmp_path):
    from controladores.Facturas import FacturaController
    return FacturaController()


def test_el_pdf_existe_aunque_ok_venga_vacio(controlador, tmp_path,
                                           sin_avisos):
    """El caso de fpdf2: ok es None y el archivo esta.

    Con el chequeo anterior esto daba False y saltava el aviso de que la
    factura quedo autorizada sin comprobante, que es la peor alarma posible
    porque el comprobante estaba ahi.
    """
    destino = tmp_path / "factura.pdf"
    destino.write_bytes(b"%PDF-1.4\n%%EOF\n")

    assert controlador._pdf_generado(str(destino), None, _Falso(Excepcion=""),
                                     None) is True


def test_sin_archivo_sigue_avisando(controlador, tmp_path):
    """Sin archivo, tiene que avisar: para eso esta este chequeo."""
    destino = tmp_path / "no-existe.pdf"

    resultado = controlador._pdf_generado(str(destino), True,
                                          _Falso(Excepcion=""), None)

    assert resultado is False
    assert avisos, "sin archivo tiene que avisar: para eso existe el chequeo"


def test_el_ok_verdadero_no_alcanza_sin_archivo(controlador, tmp_path, avisos):
    """Un ok que dice que si, pero sin archivo, es un fallo igual.

    Con fpdf 1.7 el ok era lo unico que se podia mirar, y por eso el chequeo
    aceptaba un ok sin comprobar nada. El archivo es lo que prueba.
    """
    destino = tmp_path / "tampoco-existe.pdf"

    assert controlador._pdf_generado(str(destino), True,
                                     _Falso(Excepcion=""), None) is False
    assert avisos


def test_generar_pdf_devuelve_none_igual_genera(controlador, tmp_path,
                                                monkeypatch):
    """La razon de fondo: la libreria no devuelve nada. Documentado en un test.

    Si alguna vez GenerarPDF vuelve a devolver algo, este test avisa y se puede
    volver a usar `ok` como senal secundaria.
    """
    from pyafipws.pyfepdf import FEPDF
    import inspect

    retorno = inspect.signature(FEPDF.GenerarPDF).return_annotation
    assert retorno in (inspect.Signature.empty, None), \
        ("GenerarPDF ahora devuelve {!r}. Si la libreria cambio, revisar si "
         "conviene volver a usar el valor de retorno como senal, aunque el "
         "chequeo del archivo deberia seguir siendo el que manda.").format(retorno)
