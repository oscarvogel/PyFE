"""Que la app no diga que emitio bien cuando no hay PDF.

Por que esta probada
--------------------
Una factura autorizada en ARCA no se puede deshacer. Si despues el PDF no se
genera y la app no avisa, el usuario cierra la pantalla creyendo que termino y
el cliente no recibe nada. Es el peor resultado posible del sistema fiscal, y
por eso tiene que quedar fijo con un test, no depende de que alguien se acuerde
de mirarlo.
"""
import os
import sys

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class _CAE(object):
    def text(self):
        return "86400944641465"


class _View(object):
    lineditCAE = _CAE()


class _Cabfact(object):
    numero = 6


class _Pyfpdf(object):
    Excepcion = "I is not a valid Align"
    Traceback = "traceback del render"


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
            errores.append({"titulo": titulo, "mensaje": mensaje,
                            "que_hacer": que_hacer, "detalle": detalle}))
    return errores


def test_si_el_pdf_existe_no_avisa_nada(controlador, monkeypatch, tmp_path):
    """El camino normal: el archivo esta, no hay nada que reportar."""
    errores = _capturar_error(monkeypatch)
    salida = tmp_path / "factura.pdf"
    salida.write_bytes(b"%PDF-1.4 contenido")

    ok = controlador._pdf_generado(str(salida), True, _Pyfpdf(), _Cabfact())

    assert ok is True
    assert errores == []


def test_si_el_pdf_no_existe_avisa_con_el_cae(controlador, monkeypatch, tmp_path):
    """GenerarPDF puede decir que si y no escribir nada. Hay que mirar el archivo."""
    errores = _capturar_error(monkeypatch)
    salida = tmp_path / "factura.pdf"   # nunca se escribio

    ok = controlador._pdf_generado(str(salida), True, _Pyfpdf(), _Cabfact())

    assert ok is False
    assert len(errores) == 1
    error = errores[0]
    assert "no se pudo generar el PDF" in error["mensaje"]
    # El CAE es lo que hace falta para reimprimir: sin esto el usuario no
    # puede ni saber que comprobante tiene que buscar.
    assert "86400944641465" in error["que_hacer"]
    assert "Reimprimir" in error["que_hacer"]
    # Y tiene que aclarar que NO se vuelva a emitir.
    assert "No la vuelvas a emitir" in error["que_hacer"]
    assert "Excepcion" in error["detalle"]


def test_si_generarpdf_falla_tambien_avisa(controlador, monkeypatch, tmp_path):
    """Devolver False tambien es falla, haya archivo viejo o no."""
    errores = _capturar_error(monkeypatch)
    salida = tmp_path / "factura.pdf"
    salida.write_bytes(b"%PDF-1.4")   # existe de una corrida anterior

    ok = controlador._pdf_generado(str(salida), False, _Pyfpdf(), _Cabfact())

    assert ok is False
    assert len(errores) == 1


def test_el_detalle_incluye_la_excepcion_tecnica(controlador, monkeypatch, tmp_path):
    """El texto tecnico va en el detalle, para pasarlo a soporte."""
    errores = _capturar_error(monkeypatch)
    controlador._pdf_generado(str(tmp_path / "no-existe.pdf"), False,
                             _Pyfpdf(), _Cabfact())
    assert "I is not a valid Align" in errores[0]["detalle"]
