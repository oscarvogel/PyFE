"""Regresión: Enter no debe abrir el selector de cliente dos veces.

El síntoma era raro de ver y más raro de encontrar. El operador escribía "muni",
veía las 3 coincidencias, elegía una, y el diálogo volvía a aparecer: parecía
que la selección no se aceptaba, cuando en realidad el problema era que ya había
otro diálogo esperando abajo.

La causa: `textCliente` tenía `returnPressed` **y** `editingFinished`
conectados al mismo método. QLineEdit emite las dos señales cuando se presiona
Enter, así que el handler corría dos veces y abría dos diálogos.

Lo que faltaba en los tests es que todos llamaban a
`cargar_cliente_desde_busqueda()` directo, salteando el cableado de señales, que
es justamente lo roto. Acá se presiona la tecla de verdad.

Nota de infraestructura: los imports de QtCore y QtTest van adentro de la
fixture, después de que existe la QApplication. Importarlos arriba, antes de que
haya una instancia, hace que el proceso muera con STATUS_STACK_BUFFER_OVERRUN y
pytest no reaches a informar nada.
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402


class _ClienteFalso(object):
    idcliente = 6
    nombre = "MUNICIPALIDAD DE CAPIOVI"
    cuit = "30-67243961-9"
    dni = 0


@pytest.fixture
def qt():
    """Qt and ready. This fixture has to come before the imports that need it."""
    from PyQt5.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture
def espias(qt, monkeypatch):
    """Un controlador real, con la busqueda y el selector contados."""
    monkeypatch.setattr(sys, "argv", [sys.argv[0]])

    from controladores.VentaSimple import VentaSimpleController

    controller = VentaSimpleController()

    llamadas = {"buscar": 0, "seleccionar": 0}

    def buscar(busqueda, limite=None):
        llamadas["buscar"] += 1
        return [_ClienteFalso() for _ in range(controller._coincidencias)]

    def seleccionar(busqueda):
        llamadas["seleccionar"] += 1
        return None

    controller._coincidencias = 3
    monkeypatch.setattr(controller, "buscar_clientes", buscar)
    monkeypatch.setattr(controller, "seleccionar_cliente", seleccionar)
    # Sin esto, en offscreen el foco nunca llega al campo y el focusOut no
    # se emite: los tests de foco dan 0 siempre y pasan sin probar nada.
    controller.view.show()
    qt.processEvents()
    yield controller, llamadas
    controller.view.Cerrar()


def _enterar(controller, qt):
    from PyQt5.QtCore import Qt
    from PyQt5.QtTest import QTest

    QTest.keyClick(controller.view.textCliente, Qt.Key_Return)
    qt.processEvents()


def test_enter_busca_una_sola_vez(espias, qt):
    controller, llamadas = espias

    controller.view.textCliente.setText("muni")
    controller.view.textCliente.setFocus()
    qt.processEvents()

    llamadas["buscar"] = 0
    llamadas["seleccionar"] = 0

    _enterar(controller, qt)

    assert llamadas["buscar"] == 1, \
        "la busqueda corrio {} veces con una sola pulsacion".format(llamadas["buscar"])
    assert llamadas["seleccionar"] == 1, \
        "el selector se abrio {} veces con una sola pulsacion".format(
            llamadas["seleccionar"])


def test_enter_con_una_sola_coincidencia_no_abre_el_selector(espias, qt):
    """Con un solo cliente no hay nada que elegir: se carga directo."""
    controller, llamadas = espias
    controller._coincidencias = 1

    controller.view.textCliente.setText("muni")
    controller.view.textCliente.setFocus()
    qt.processEvents()

    _enterar(controller, qt)

    assert llamadas["seleccionar"] == 0
    assert controller.cliente is not None


def test_salir_del_campo_tambien_busca(espias, qt):
    """El otro camino de editingFinished: perder el foco, sin tocar Enter.

    Por esto el arreglo fue sacar returnPressed y no editingFinished: si se
    saca el otro, este camino se pierde.

    Ojo: hay que *escribir* el texto, no ponerlo con setText. QLineEdit solo
    emite editingFinished al perder el foco si el texto fue editado por el
    usuario; un setText desde codigo deja la bandera de "editado" apagada y
    no dispara nada. Por eso el test con setText pasaba en verde sin estar
    probando lo que decia.
    """
    controller, llamadas = espias
    from PyQt5.QtTest import QTest

    controller.view.textCliente.setFocus()
    QTest.keyClicks(controller.view.textCliente, "muni")
    qt.processEvents()

    llamadas["buscar"] = 0
    controller.view.textArticulo.setFocus()
    qt.processEvents()

    assert llamadas["buscar"] == 1, \
        "salir del campo no busco: quedan {} llamadas".format(llamadas["buscar"])


def test_el_campo_de_cliente_no_tiene_conectado_el_return_pressed(espias):
    """La forma del bug, fijada por si alguien vuelve a conectar esa senal.

    Es el guard estructural: si el campo vuelve a tener el handler en
    returnPressed, Enter emite las dos senales y la busqueda corre dos veces
    otra vez, aunque el test de arriba siga mirando lo correcto.
    """
    controller, _ = espias

    conexiones = controller.view.textCliente.receivers(
        controller.view.textCliente.returnPressed)
    assert conexiones == 0, (
        "el campo de cliente tiene {} conexiones en returnPressed. Con esa "
        "senal conectada, Enter corre la busqueda dos veces porque QLineEdit "
        "emite returnPressed y editingFinished.".format(conexiones))


def test_editing_finished_sigue_conectado(espias):
    """Lo que hay que dejar: la busqueda al salir del campo."""
    controller, _ = espias

    conexiones = controller.view.textCliente.receivers(
        controller.view.textCliente.editingFinished)
    assert conexiones == 1, \
        "la busqueda quedo sin conectar: {} receivers".format(conexiones)
