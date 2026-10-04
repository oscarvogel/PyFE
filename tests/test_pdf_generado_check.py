# coding=utf-8
"""El aviso de "no se pudo generar el PDF", sobre todo el de fpdf2.

Que estaba pasando
------------------
Con fpdf2 (fpdf 2.8.7) `Template.render()` esta anotado -> None: escribe el
archivo y no devuelve nada. Y el chequeo hacia `if ok and os.path.isfile(...)`,
o sea que exigia un valor de retorno que la libreria ya no daba. Con fpdf 1.7,
de donde venia el proyecto, render() si devolvia algo verdadero; el proyecto
migro a fpdf2 y el chequeo se dio vuelta sin que nadie lo notara.

Efecto: cada factura impresa avisaba "La factura se autorizo pero no se pudo
generar el PDF" CON el PDF generado al lado, y dejaba `facturaGenerada` en
None.

Que quedo de ese arreglo, y por que ahora es distinto
-----------------------------------------------------
La salida fue aceptar que el archivo exista como prueba de que se genero. No
alcanza: fpdf2 abre el archivo de salida en modo escritura antes de escribir
una linea, asi que si esta abierto en un visor de PDF, Windows no lo deja y el
archivo se trunca a CERO bytes. El archivo existia (vacio) y la app reportaba
exito. Reproducido con Foxit PDF Reader abierto.

Ahora la escritura pasa por `libs.Utiles.escribir_pdf`, que arma a un temporal
y recien despues reemplaza el destino. El `ok` que llega aca es el resultado
real, y el archivo anterior nunca se toca si algo falla.
Ver tests/test_pdf_bloqueado.py.

Estos tests no dependen de la base ni de ARCA: llaman al metodo directo.
"""

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


def test_la_escritura_confirmada_no_avisa(controlador, tmp_path, sin_avisos):
    """El camino normal de fpdf2: la escritura se sabe por `escribir_pdf`.

    Antes esto se resolvia mirando que el archivo existiera. Ya no: se mira el
    resultado de la escritura, que es lo unico que no miente cuando la
    libreria no devuelve nada.
    """
    destino = tmp_path / "factura.pdf"

    assert controlador._pdf_generado(str(destino), True, _Falso(Excepcion=""),
                                     None) is True


def test_escribir_sin_archivo_avisa(controlador, tmp_path):
    """Sin archivo tiene que avisar: para eso esta este chequeo."""
    destino = tmp_path / "no-existe.pdf"

    resultado = controlador._pdf_generado(str(destino), False,
                                          _Falso(Excepcion=""), None,
                                          "el generador no escribio nada")

    assert resultado is False
    assert avisos, "sin archivo tiene que avisar: para eso existe el chequeo"


def test_un_ok_que_dice_que_si_no_alcanza_sin_escribir(controlador, tmp_path,
                                                       avisos):
    """Un ok que dice que si es la senal de la escritura, no del archivo.

    El archivo es consecuencia de la escritura, no al reves. Si `ok` dice que
    se escribio y el archivo no esta, el problema esta en `escribir_pdf`, y lo
    que tiene que avisar el es ella.
    """
    destino = tmp_path / "tampoco-existe.pdf"

    assert controlador._pdf_generado(str(destino), True,
                                     _Falso(Excepcion=""), None) is True
    assert avisos == []


def test_generar_pdf_devuelve_none_igual_genera(controlador, tmp_path,
                                                monkeypatch):
    """La razon de fondo: la libreria no devuelve nada. Documentado en un test.

    Si alguna vez GenerarPDF vuelve a devolver algo, este test avisa y se puede
    volver a usar `ok` como senal secundaria. AUNQUE el chequeo de la escritura
    deberia seguir siendo el que manda: con fpdf2 devuelve None igual habiendo
    fallado.
    """
    from pyafipws.pyfepdf import FEPDF
    import inspect

    retorno = inspect.signature(FEPDF.GenerarPDF).return_annotation
    assert retorno in (inspect.Signature.empty, None), \
        ("GenerarPDF ahora devuelve {!r}. Si la libreria cambio, revisar si "
         "conviene volver a usar el valor de retorno como senal, aunque el "
         "chequeo de la escritura deberia seguir siendo el que manda.").format(retorno)
