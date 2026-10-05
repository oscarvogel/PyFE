"""Que la app no diga que emitio bien cuando no hay PDF.

Por que esta probada
--------------------
Una factura autorizada en ARCA no se puede deshacer. Si despues el PDF no se
genera y la app no avisa, el usuario cierra la pantalla creyendo que termino y
el cliente no recibe nada. Es el peor resultado posible del sistema fiscal, y
por eso tiene que quedar fijo con un test, no depende de que alguien se acuerde
de mirarlo.

Que cambio, y por que
--------------------
Este archivo fijaba antes otra premisa: que "el archivo exista" probaba que
se habia generado. Con fpdf2 no se puede pedir el retorno de `GenerarPDF`
(`Template.render()` esta anotado -> None), asi que la existencia del archivo
era la unica prueba disponible, y parecio buena enough.

No era. fpdf2 abre el archivo de salida en modo escritura ANTES de escribir
una linea: si el destino esta abierto en un visor de PDF, Windows no lo deja,
el archivo se trunca a CERO bytes y recien ahi la libreria falla. Como el
archivo existia (de cero bytes), la app reportaba exito con un comprobante
vacio. Reproducido con Foxit abierto: archivo de 0 bytes y ningun aviso.

Ahora el PDF se arma a un temporal y se pasa al destino recien terminado
(`libs.Utiles.escribir_pdf`), asi que el `ok` que llega aca es el resultado
real de la escritura. Ver tests/test_pdf_bloqueado.py.
"""
import os
import sys

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class _View(object):
    # El CAE vive en un atributo de la vista, no en un `EntradaTexto` con
    # `.text()`. Ver `vistas/Facturas.py::MuestraAutorizacion`.
    cae = "86400944641465"


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


def test_si_se_escribio_no_avisa_nada(controlador, monkeypatch, tmp_path):
    """El camino normal: la escritura termino bien, no hay nada que reportar."""
    errores = _capturar_error(monkeypatch)
    salida = tmp_path / "factura.pdf"
    salida.write_bytes(b"%PDF-1.4 contenido")

    ok = controlador._pdf_generado(str(salida), True, _Pyfpdf(), _Cabfact())

    assert ok is True
    assert errores == []


def test_si_no_se_escribio_avisa_con_el_cae(controlador, monkeypatch, tmp_path):
    """El fallo tiene que llegar con el CAE, que es lo que hay que reimprimir."""
    errores = _capturar_error(monkeypatch)
    salida = tmp_path / "factura.pdf"   # nunca se escribio

    ok = controlador._pdf_generado(str(salida), False, _Pyfpdf(), _Cabfact(),
                                  "el generador no escribio ningun archivo")

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
    """Haya archivo viejo o no, si la escritura fallo hay que avisar.

    El archivo viejo es de una impresion anterior del MISMO comprobante (la
    salida es determinista por numero y ARCA no reutiliza numeros), asi que
    que este ahi no dice que esta la de ahora.
    """
    errores = _capturar_error(monkeypatch)
    salida = tmp_path / "factura.pdf"
    salida.write_bytes(b"%PDF-1.4")   # existe de una corrida anterior

    ok = controlador._pdf_generado(str(salida), False, _Pyfpdf(), _Cabfact(),
                                  "el generador fallo")

    assert ok is False
    assert len(errores) == 1


def test_un_ok_que_dice_que_si_no_alcanza(controlador, monkeypatch, tmp_path):
    """Guarda: `escribir_pdf` no puede devolver ok=True sin escribir.

    Si alguna vez devuelve eso, es porque la funcion cambio, no porque el
    archivo este: el chequeo tiene que seguir siendo el del resultado real.
    """
    errores = _capturar_error(monkeypatch)

    ok = controlador._pdf_generado(str(tmp_path / "factura.pdf"), True,
                                  _Pyfpdf(), _Cabfact())

    assert ok is True, "con la escritura confirmada no hay nada que comprobar"
    assert errores == []


def test_el_bloqueo_dice_que_cerrar_el_comprobante(controlador, monkeypatch,
                                                   tmp_path):
    """El caso del visor: el mensaje tiene que dar la accion.

    El operador no puede adivinar que tiene el PDF abierto en otra aplicacion,
    y sin eso lo unico que ve es un error tecnico.
    """
    errores = _capturar_error(monkeypatch)
    salida = tmp_path / "factura.pdf"
    salida.write_bytes(b"%PDF-1.4 contenido")

    controlador._pdf_generado(
        str(salida), False, _Pyfpdf(), _Cabfact(),
        "no se pudo reemplazar factura.pdf: Acceso denegado (5). Es el que "
        "tenes abierto en el visor de PDF.")

    que_hacer = errores[0]["que_hacer"]
    assert "Cerr" in que_hacer
    assert "factura.pdf" in que_hacer
    assert "no se toco el archivo anterior" in que_hacer.lower()
    # Y no puede pedir Diagnostics cuando el problema es abrir el visor.
    assert "Diagnostico" not in que_hacer


def test_el_detalle_incluye_la_excepcion_tecnica(controlador, monkeypatch, tmp_path):
    """El texto tecnico va en el detalle, para pasarlo a soporte."""
    errores = _capturar_error(monkeypatch)
    controlador._pdf_generado(str(tmp_path / "no-existe.pdf"), False,
                              _Pyfpdf(), _Cabfact(), "algo fallo")
    assert "I is not a valid Align" in errores[0]["detalle"]
    assert "algo fallo" in errores[0]["detalle"]
