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
