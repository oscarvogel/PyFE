import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication


def test_venta_simple_controller_se_puede_construir(monkeypatch):
    monkeypatch.setattr(sys, "argv", [sys.argv[0]])
    app = QApplication.instance() or QApplication([])

    from controladores.VentaSimple import VentaSimpleController

    controller = VentaSimpleController()

    assert controller.view.windowTitle() == "Nueva venta"
    controller.view.Cerrar()


def test_carga_cliente_desde_busqueda(monkeypatch):
    monkeypatch.setattr(sys, "argv", [sys.argv[0]])
    app = QApplication.instance() or QApplication([])

    from controladores.VentaSimple import VentaSimpleController

    class ClienteEncontrado:
        idcliente = 7
        nombre = "DUOMO"
        cuit = "20-12345678-9"
        dni = 0

    controller = VentaSimpleController()
    monkeypatch.setattr(controller, "buscar_cliente", lambda busqueda: ClienteEncontrado())
    controller.view.textCliente.setText("duomo")

    controller.cargar_cliente_desde_busqueda()

    assert controller.cliente.idcliente == 7
    assert controller.view.checkConsumidorFinal.isChecked() is False
    assert controller.view.textCliente.text() == "7 - DUOMO"
    assert controller.view.textDocumento.text() == "20-12345678-9"
    controller.view.Cerrar()
