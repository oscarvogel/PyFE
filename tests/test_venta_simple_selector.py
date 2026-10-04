"""El selector de cliente no se puede abrir dos veces.

Como se reproduce el fallo
--------------------------
El operador escribia "muni", daba Enter, veia las coincidencias, elegia una,
aceptaba, y el dialogo volvia a aparecer.

La causa NO es que el campo tuviera dos senales conectadas. Es que al abrirse
el dialogo modal, Qt le quita el foco al campo de cliente, y eso emite
editingFinished en el momento en que el handler todavia esta en la pila, dentro
de dialogo.exec_(). La segunda entrada ve el texto sin cambiar, encuentra las
mismas coincidencias y abre un segundo dialogo encima del primero. El operador
eligio en el de adelante, este se cierra, y queda a la vista el de atras: de
ahi la sensacion de que la seleccion no se toma.

Por que los tests anteriores no lo veian: reemplazaban exec_ por una funcion
que devolvia enseguida. Un dialogo que no se abre no le puede quitar el foco a
nadie, que es justo lo que faltaba. Estos tests abren el dialogo de verdad y lo
cierran con un timer, que simula al operador dando Aceptar.
"""

import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402


class _ClienteFalso(object):
    idcliente = 6
    nombre = "MUNICIPALIDAD DE CAPIOVI"
    cuit = "30-67243961-9"
    dni = 0


@pytest.fixture
def qt():
    from PyQt5.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _barrer(qt, segundos=2.0):
    """Deja correr el bucle de eventos hasta que se vacien los timers."""
    from PyQt5.QtCore import QElapsedTimer

    reloj = QElapsedTimer()
    reloj.start()
    while reloj.elapsed() < int(segundos * 1000):
        qt.processEvents()
        time.sleep(0.01)


@pytest.fixture
def dialogos(qt, monkeypatch):
    """El dialogo real, pero contando cuantas veces se construye.

    Se sustituye en los DOS modulos que lo importan, porque uno lo busca para
    construirlo y el otro para el tipo de control.
    """
    from PyQt5.QtCore import QTimer
    import controladores.VentaSimple as VS
    import vistas.VentaSimple as WV

    base = WV.VentaSimpleSeleccionClienteDialog
    conteo = {"n": 0, "vivos": []}

    class DialogoContado(base):
        def __init__(self, buscador, busqueda=""):
            conteo["n"] += 1
            base.__init__(self, buscador, busqueda)
            conteo["vivos"].append(self)

        def exec_(self):
            QTimer.singleShot(60, self.accept)
            return base.exec_(self)

        def closeEvent(self, evento):
            conteo["vivos"] = [d for d in conteo["vivos"] if d is not self]
            base.closeEvent(self, evento)

    monkeypatch.setattr(WV, "VentaSimpleSeleccionClienteDialog", DialogoContado)
    monkeypatch.setattr(VS, "VentaSimpleSeleccionClienteDialog", DialogoContado)
    return conteo


@pytest.fixture
def controller(qt, monkeypatch):
    monkeypatch.setattr(sys, "argv", [sys.argv[0]])

    from controladores.VentaSimple import VentaSimpleController

    c = VentaSimpleController()

    def buscar(busqueda, limite=None):
        return [_ClienteFalso() for _ in range(3)]

    monkeypatch.setattr(c, "buscar_clientes", buscar)
    c.view.show()
    qt.processEvents()
    yield c
    c.view.Cerrar()


def test_enter_y_aceptar_abre_un_solo_dialogo(controller, dialogos, qt):
    """El caso que reporto el operador, con el dialogo de verdad."""
    from PyQt5.QtCore import Qt
    from PyQt5.QtTest import QTest

    campo = controller.view.textCliente
    campo.setFocus()
    QTest.keyClicks(campo, "muni")
    qt.processEvents()

    dialogos["n"] = 0
    QTest.keyClick(campo, Qt.Key_Return)
    _barrer(qt)

    assert dialogos["n"] == 1, (
        "se abrieron {} dialogos para una sola busqueda. Al abrirse el "
        "dialogo modal le quita el foco al campo, que vuelve a disparar la "
        "busqueda con el handler todavia en la pila.".format(dialogos["n"]))

    assert controller.cliente is not None
    assert controller.cliente.idcliente == 6
    assert campo.text() == "6 - MUNICIPALIDAD DE CAPIOVI"


def test_entrar_anidado_no_abre_nada(controller, dialogos, qt):
    """El candado, probado directo y sin depender del foco.

    Si el flag quedara puesto, la segunda entrada no debe abrir un dialogo
    ni preguntar si se crea el cliente: preguntar por encima del dialogo que
    ya esta en pantalla es peor que el bug original.
    """
    controller._resolviendo_cliente = True
    try:
        controller.cargar_cliente_desde_busqueda()
    finally:
        controller._resolviendo_cliente = False

    assert dialogos["n"] == 0
    assert controller.cliente is None


def test_el_candado_se_libera_tras_cargar(controller, dialogos, qt):
    """Con el flag trabado, la pantalla de venta queda inservible."""
    from PyQt5.QtCore import Qt
    from PyQt5.QtTest import QTest

    campo = controller.view.textCliente
    campo.setFocus()
    QTest.keyClicks(campo, "muni")
    qt.processEvents()
    QTest.keyClick(campo, Qt.Key_Return)
    _barrer(qt)

    assert controller._resolviendo_cliente is False


def test_el_candado_se_libera_si_algo_falla(controller, dialogos, qt, monkeypatch):
    """Una excepcion no puede dejar la pantalla bloqueada.

    Sin esto, con el flag trabado la pantalla de venta queda inservible hasta
    reiniciar la app: no se puede buscar ningun cliente mas en toda la sesion.
    """
    def _reventar(*args, **kwargs):
        raise RuntimeError("no se pudo resolver")

    # Con el campo vacio la funcion cortaria antes de llegar al candado, y el
    # test pasaria sin probar nada.
    controller.view.textCliente.setText("muni")
    monkeypatch.setattr(controller, "resolver_cliente_desde_busqueda", _reventar)

    with pytest.raises(RuntimeError):
        controller.cargar_cliente_desde_busqueda()

    assert controller._resolviendo_cliente is False
