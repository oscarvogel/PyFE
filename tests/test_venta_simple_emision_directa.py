"""La venta rapida emite sin abrir el formulario de emision.

Que estaba pasando
------------------
La pantalla "Nueva venta" tiene su boton Emitir, pero ese boton no emitia:
construia el FacturaController, le cargaba los datos y llamaba exec_().
FacturaController ES el formulario "Emision de comprobante electronico", de
pantalla completa, con sus pestanas y su propio boton Emitir. O sea que el
operador apretaba Emitir en la venta rapida, se le abria el formulario grande
ya cargado, y tenia que apretar Emitir OTRA vez ahi.

Es al reves de lo que la pantalla existe para hacer.

Que quedo

- emitir_factura() llama a GrabaFactura() en vez de a exec_(). El controlador
  se arma igual y recibe los mismos datos: se usan los metodos, no se levanta
  la ventana.
- GrabaFactura() ahora devuelve si emitio, para poder limpiar la pantalla
  cuando salio bien y dejarla con los renglones cuando salio mal. Antes no
  devolvia nada porque el unico que lo llamaba era el boton del formulario, que
  no necesita saber.
"""

import os
import sys
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402


@pytest.fixture
def qt():
    from PyQt5.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _renglon():
    """Un renglon de verdad: recalcular_total los recorre con atributos."""
    from controladores.venta_simple_totales import RenglonVenta

    return RenglonVenta(codigo="1", detalle="Un servicio",
                        cantidad=Decimal("1"), precio_unitario=Decimal("100"),
                        iva=Decimal("21"))


@pytest.fixture
def controller(qt, monkeypatch):
    monkeypatch.setattr(sys, "argv", [sys.argv[0]])

    from controladores.VentaSimple import VentaSimpleController

    c = VentaSimpleController()
    c.view.show()
    qt.processEvents()
    yield c
    c.view.Cerrar()


@pytest.fixture
def emision(monkeypatch):
    """Reemplaza FacturaController por uno que no habla con ARCA.

    Se reemplaza en el modulo Facturas y no en VentaSimple porque
    emitir_factura lo importa adentro de la funcion.
    """
    import controladores.Facturas as FAC

    registro = {"creado": False, "exec": 0, "cargado": None, "emitida": True}

    class FacturaFalsa(object):
        def __init__(self):
            registro["creado"] = True

        def cargar_venta_simple(self, cliente_id=None, renglones=None,
                                 forma_pago_id=None, cuotas=1):
            registro["cargado"] = {"cliente_id": cliente_id,
                                   "renglones": renglones,
                                   "forma_pago_id": forma_pago_id,
                                   "cuotas": cuotas}

        def exec_(self):
            registro["exec"] += 1

        def GrabaFactura(self):
            return registro["emitida"]

    monkeypatch.setattr(FAC, "FacturaController", FacturaFalsa)
    return registro


def _preparar(controller, monkeypatch, renglones=None):
    """Deja la venta con una linea y sin consumidor final, y emite."""
    renglones = renglones if renglones is not None else [_renglon()]
    monkeypatch.setattr(controller, "obtener_renglones", lambda: renglones)
    controller.view.checkConsumidorFinal.setChecked(True)
    return renglones


def test_emitir_no_abre_el_formulario_de_emision(controller, emision, qt,
                                                 monkeypatch):
    """El centro del arreglo: la pantalla rapida no levanta el formulario."""
    _preparar(controller, monkeypatch)

    controller.emitir_factura()

    assert emision["exec"] == 0, \
        "se llamo exec_() sobre el controlador de la factura: eso abre el " \
        "formulario de emision, que es lo que la venta rapida tiene que " \
        "evitar"
    assert emision["cargado"] is not None, "no se le cargaron los datos"


def test_al_emitir_se_usan_los_mismos_metodos(controller, emision, qt,
                                             monkeypatch):
    """Usa los metodos del FacturaController, no los reimplementa."""
    renglones = _preparar(controller, monkeypatch)

    controller.emitir_factura()

    assert emision["cargado"]["renglones"] == renglones
    assert emision["emitida"] is True


def test_si_salio_bien_la_pantalla_queda_lista(controller, emision, qt,
                                                monkeypatch):
    """Autorizada: no queda una venta a medio hacer pegada en la pantalla."""
    _preparar(controller, monkeypatch)
    controller.cliente = None

    controller.emitir_factura()

    assert controller.cliente is None
    assert controller.view.textCliente.text() == ""
    assert controller.view.textArticulo.text() == ""


def test_si_fallo_la_pantalla_no_se_toca(controller, emision, qt, monkeypatch):
    """Falló: los renglones se dejan, para revisar y reintentar.

    Limpiar acá perderia la venta, y la venta solo existe en memoria.
    """
    emision["emitida"] = False
    _preparar(controller, monkeypatch)
    controller.cliente = None
    controller.view.textCliente.setText("algo")

    controller.emitir_factura()

    assert controller.view.textCliente.text() == "algo"


def test_sin_cliente_no_emitir(controller, emision, qt, monkeypatch):
    """Sin cliente elegido no se emite, y no se abre el formulario."""
    monkeypatch.setattr(controller, "obtener_renglones", lambda: [_renglon()])
    monkeypatch.setattr(controller, "buscar_clientes", lambda *a, **k: [])
    controller.view.checkConsumidorFinal.setChecked(False)
    controller.cliente = None

    controller.emitir_factura()

    assert emision["exec"] == 0
    assert emision["creado"] is False


def test_a_consumidor_final_se_emite_al_cliente_generico(controller, emision,
                                                         qt, monkeypatch):
    """Con el tilde de consumidor final se puede emitir.

    La factura B necesita un cliente real en la base: se usa el generico
    CONSUMIDOR FINAL. Antes se pasaba None y caia en "No se ha
    especificado un cliente valido".
    """
    from controladores.venta_simple_cliente import id_cliente_consumidor_final

    _preparar(controller, monkeypatch)
    controller.view.checkConsumidorFinal.setChecked(True)
    controller.cliente = None

    controller.emitir_factura()

    assert emision["creado"] is True
    assert emision["cargado"]["cliente_id"] is not None
    assert (emision["cargado"]["cliente_id"]
            == id_cliente_consumidor_final())
