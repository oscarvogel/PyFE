"""El boton de la confirmacion tiene que decir que se va a crear.

Que estaba pasando
------------------
Al agregar un producto que no existia, el mensaje decia "Producto no
encontrado. Desea agregarlo?" y el boton decia "Crear cliente". La misma
funcion de confirmacion se usa para el cliente y para el producto, con un
texto de boton fijo.

Un boton que contradice el mensaje hace dudar de toda la pantalla: el operador
no sabe si va a crear un cliente o un producto, y por lo tanto no sabe si
esta por tocar algo que no es.

Este test mira las dos pantallas a la vez. Si alguien vuelve a hardcodear el
texto, el nombre del boton vuelve a no coincidir con el mensaje.
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402


@pytest.fixture
def qt():
    from PyQt5.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


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
def preguntas(monkeypatch):
    """Captura las preguntas de confirmacion en vez de mostrarlas."""
    import libs.Ventanas as V

    hechas = []

    def _capturar(titulo, mensaje, textoOk="Sí", textoCancelar="Cancelar",
                  por_defecto_cancelar=True):
        hechas.append({"titulo": titulo, "mensaje": mensaje,
                       "textoOk": textoOk})
        return False          # el operador elige cancelar

    monkeypatch.setattr(V, "showConfirmation", _capturar)
    return hechas


def test_el_boton_del_producto_dice_producto(controller, preguntas, qt):
    controller.view.textArticulo.setText("Cosa que no existe")
    controller.agregar_articulo()

    assert len(preguntas) == 1
    assert preguntas[0]["textoOk"] == "Crear producto", \
        "el boton dice {!r} sobre un mensaje que dice {!r}".format(
            preguntas[0]["textoOk"], preguntas[0]["mensaje"])


def test_el_boton_del_cliente_dice_cliente(controller, preguntas, qt,
                                            monkeypatch):
    """La otra mitad: cada pantalla nombra lo que va a crear."""
    controller.view.textCliente.setText("Cliente que no existe")
    monkeypatch.setattr(controller, "buscar_clientes", lambda *a, **k: [])

    controller.cargar_cliente_desde_busqueda()

    assert len(preguntas) == 1
    assert preguntas[0]["textoOk"] == "Crear cliente"
    assert "Cliente" in preguntas[0]["mensaje"]


def test_el_boton_siempre_nombra_lo_que_crea(controller, preguntas, qt,
                                              monkeypatch):
    """La regla, puesta como asercion y no como ejemplo.

    Comparando el boton contra el mensaje, el test no depende de las palabras
    exactas: si alguien agrega una tercera pantalla y se olvida de pasar el
    texto, tambien falla.
    """
    controller.view.textArticulo.setText("No existe")
    controller.agregar_articulo()

    controller.view.textCliente.setText("Tampoco existe")
    monkeypatch.setattr(controller, "buscar_clientes", lambda *a, **k: [])
    controller.cargar_cliente_desde_busqueda()

    cosa = {"producto": "producto", "cliente": "cliente"}
    for pregunta in preguntas:
        for palabra in cosa.values():
            if palabra in pregunta["mensaje"].lower():
                assert palabra in pregunta["textoOk"].lower(), \
                    "mensaje: {!r} / boton: {!r}".format(
                        pregunta["mensaje"], pregunta["textoOk"])


def test_cancelar_no_abre_el_dialogo_de_alta(controller, preguntas, qt,
                                              monkeypatch):
    """Responder que no tiene que dejar pasar todo lo que viene despues.

    Si el dialogo de alta se abriera, el operador habria visto dos pantallas
    seguidas por responder 'no' a la primera.
    """
    abrio = {"n": 0}
    original = controller.solicitar_alta_articulo

    def _contado(busqueda):
        abrio["n"] += 1
        return original(busqueda)

    monkeypatch.setattr(controller, "solicitar_alta_articulo", _contado)

    controller.view.textArticulo.setText("No existe")
    controller.agregar_articulo()

    assert len(preguntas) == 1, "no se pregunto nada"
    assert abrio["n"] == 0, "se abrio el alta del articulo sin confirmacion"
