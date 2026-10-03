"""Atajos de teclado y descarte de venta.

Por que estan probados
----------------------
Un atajo que no se registra no da error: QShortcut se crea, se conecta y se
garbage-collectea, la pantalla anda perfecto y el atajo no hace nada. Solo se
entrega descubriendolo en la maquina del cliente. Y el atajo de cerrar con una
venta cargada, si pierde lo tipeado, es peor que no tenerlo.
"""
import sys
from decimal import Decimal

import pytest
from PyQt5.QtWidgets import QApplication

os_environ_ya_puesto = True


@pytest.fixture(scope="module", autouse=True)
def _app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def controller(monkeypatch):
    monkeypatch.setattr(sys, "argv", [sys.argv[0]])
    from controladores.VentaSimple import VentaSimpleController
    c = VentaSimpleController()
    yield c
    c.view.Cerrar()


# -- Los atajos existen ------------------------------------------------------

def test_los_atajos_se_crean_todos(controller):
    from PyQt5.QtGui import QKeySequence
    from PyQt5.QtWidgets import QShortcut

    atajos = controller.view.findChildren(QShortcut)
    registrados = [a.key() for a in atajos]

    for esperada, _, _, _ in controller.ATAJOS:
        # Se comparan QKeySequence y no strings porque Qt normaliza: la que se
        # escribe "Delete" se reporta como "Del". Comparar strings daria un
        # falso negativo y taparia justo el bug que se quiere cazar.
        assert QKeySequence(esperada) in registrados, \
            "el atajo {} no se registro".format(esperada)


def test_cada_atajo_apunta_a_un_metodo_que_existe(controller):
    for _, metodo, _, _ in controller.ATAJOS:
        assert callable(getattr(controller, metodo)), metodo


def test_los_atajos_se_anuncian_en_el_boton(controller):
    """El atajo tiene que estar a la vista: si no, nadie lo descubre."""
    assert "Ctrl+E" in controller.view.btnEmitir.toolTip()
    assert "Ctrl+Return" in controller.view.btnAgregar.toolTip()
    assert "Ctrl+B" in controller.view.btnBorrar.toolTip()


# -- Foco: cargar una venta es escribir -------------------------------------

def test_al_agregar_un_producto_el_foco_vuelve_al_producto(controller, monkeypatch):
    """Cargar renglon tras renglon no deberia obligar a ir al mouse."""
    import controladores.VentaSimple as venta_simple

    class TipoIva:
        iva = Decimal("21")

    class Articulo:
        idarticulo = 3
        nombre = "Tornillo"
        preciopub = Decimal("100.00")
        tipoiva = TipoIva()

    monkeypatch.setattr(controller, "buscar_articulo", lambda texto: Articulo())
    monkeypatch.setattr(controller, "solicitar_cantidad_y_precio",
                        lambda a, c: (Decimal("1"), Decimal("100.00")))

    controller.view.show()
    controller.view.textArticulo.setText("TORNILLO")
    controller.agregar_articulo()

    assert controller.view.gridVenta.rowCount() == 1
    # focusWidget() y no hasFocus(): con la ventana inactiva (que es lo que hay
    # en offscreen) hasFocus() es False para todos los widgets, se mire lo que
    # se mire, y el test pasaria siempre o fallaria siempre.
    assert controller.view.focusWidget() is controller.view.textArticulo


# -- Cerrar con la venta cargada --------------------------------------------

def test_cerrar_una_venta_vacia_no_pregunta(controller, monkeypatch):
    from controladores import VentaSimple as modulo

    def no_deberia_preguntar(*a, **k):
        raise AssertionError("una venta vacia no tiene nada que perder")

    monkeypatch.setattr(modulo.Ventanas, "showConfirmation", no_deberia_preguntar)
    controller._cerrar()
    assert controller.view.isVisible() is False


def test_cerrar_una_venta_cargada_pide_confirmacion(controller, monkeypatch):
    """Perder el trabajo tipeado sin avisar es la falla que se evita aca."""
    from controladores import VentaSimple as modulo

    controller.view.gridVenta.AgregaItem(
        items=["1", "3", "Tornillo", "100", "21", "100"])

    preguntas = []
    monkeypatch.setattr(modulo.Ventanas, "showConfirmation",
                        lambda *a, **k: preguntas.append(a) or False)

    controller._cerrar()

    assert preguntas, "con renglones cargados hay que preguntar antes de cerrar"
    assert "perdio" in preguntas[0][1].lower() or "pierde" in preguntas[0][1].lower()


def test_cerrar_una_venta_cargada_cierra_si_se_confirma(controller, monkeypatch):
    from controladores import VentaSimple as modulo

    controller.view.gridVenta.AgregaItem(
        items=["1", "3", "Tornillo", "100", "21", "100"])
    monkeypatch.setattr(modulo.Ventanas, "showConfirmation", lambda *a, **k: True)

    controller._cerrar()

    assert controller.view.isVisible() is False
