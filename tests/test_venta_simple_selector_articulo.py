"""Enter con el producto vacio abre el catalogo.

Que estaba pasando
------------------
Con el cliente, Enter abre un selector y uno elige. Con el producto, Enter con
el campo vacio decia "Ingrese un producto": un aviso de que no se entendio que
hacer, sin salida para el operador que no se acuerda el nombre exacto del
producto.

Con texto escrito el camino es otro y no se toca: se busca, y si no aparece se
ofrece darlo de alta. Eso es lo que permite cargar algo nuevo sin salir de la
pantalla.

Estos tests cubren las dos ramas, y una de las aserciones mira que el camino del
campo vacio NO ofrezca crear: sin texto escrito no hay nada que crear, y
ofrecerlo seria meter un producto en blanco en el catalogo.
"""

import os
import sys
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402


class _Articulo(object):
    def __init__(self, idarticulo, nombre, codbarra=""):
        self.idarticulo = idarticulo
        self.nombre = nombre
        self.codbarra = codbarra
        self.preciopub = Decimal("100")
        self.tipoiva = type("T", (), {"iva": Decimal("21")})()


@pytest.fixture
def qt():
    from PyQt5.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture
def controller(qt, monkeypatch):
    monkeypatch.setattr(sys, "argv", [sys.argv[0]])

    from controladores.VentaSimple import VentaSimpleController

    c = VentaSimpleController()

    catalogo = [_Articulo(1, "Mantenimiento de computadoras"),
                _Articulo(2, "Consultoria", "CONS-001")]
    monkeypatch.setattr(c, "_coincidencias_articulo",
                        lambda texto, limite=None: _filtrar(catalogo, texto))
    c.view.show()
    qt.processEvents()
    yield c
    c.view.Cerrar()


def _filtrar(catalogo, texto):
    texto = (texto or "").strip().lower()
    if not texto:
        return list(catalogo), len(catalogo)
    hallados = [a for a in catalogo if texto in a.nombre.lower()]
    return hallados, len(hallados)


@pytest.fixture
def selector(monkeypatch):
    """El dialogo real, pero eligiendo el primero y cerrandose solo."""
    from PyQt5.QtCore import QTimer
    import controladores.VentaSimple as VS
    import vistas.VentaSimple as WV

    base = WV.VentaSimpleSeleccionArticuloDialog
    registro = {"n": 0, "elegir": True, "vistos": []}

    class DialogoContado(base):
        def __init__(self, buscador, busqueda=""):
            registro["n"] += 1
            base.__init__(self, buscador, busqueda)
            registro["vistos"].append(self)

        def exec_(self):
            if registro["elegir"]:
                QTimer.singleShot(30, self.accept)
            else:
                QTimer.singleShot(30, self.reject)
            return base.exec_(self)

    monkeypatch.setattr(WV, "VentaSimpleSeleccionArticuloDialog", DialogoContado)
    monkeypatch.setattr(VS, "VentaSimpleSeleccionArticuloDialog", DialogoContado)
    return registro


def _barrer(qt, milisegundos=900):
    import time
    from PyQt5.QtCore import QElapsedTimer

    reloj = QElapsedTimer()
    reloj.start()
    while reloj.elapsed() < milisegundos:
        qt.processEvents()
        time.sleep(0.01)


@pytest.fixture
def sin_preguntar(controller, monkeypatch):
    """Que ningun dialogo de los de verdad se abra en un test.

    Si se abre uno, el test queda esperando un click que nadie va a hacer y
    cuelga en vez de fallar. Los dialogos que se quieren probar se parchean
    uno por uno en el test que los necesita.
    """
    import libs.Ventanas as V

    def _no_preguntar(titulo, mensaje, *args, **kwargs):
        pytest.fail("se abrio un dialogo: {} / {}".format(titulo, mensaje))

    monkeypatch.setattr(V, "showAlert", _no_preguntar)
    monkeypatch.setattr(V, "showConfirmation",
                        lambda titulo, mensaje, **kw: False)
    monkeypatch.setattr(V, "showError", _no_preguntar)
    return controller


def test_enter_con_el_campo_vacio_abre_el_catalogo(sin_preguntar, selector, qt,
                                                   monkeypatch):
    """Lo pedido: el campo vacio levanta la pantalla de busqueda."""
    from PyQt5.QtCore import Qt
    from PyQt5.QtTest import QTest

    controller = sin_preguntar
    # Sin esto, elegir un articulo abre el dialogo REAL de cantidad y precio y
    # el test queda esperando un click.
    monkeypatch.setattr(controller, "solicitar_cantidad_y_precio",
                        lambda articulo, cantidad: (cantidad, Decimal("100")))

    controller.view.textArticulo.clear()
    controller.view.textArticulo.setFocus()

    selector["n"] = 0
    QTest.keyClick(controller.view.textArticulo, Qt.Key_Return)
    _barrer(qt)

    assert selector["n"] == 1, "no se abrio el selector de productos"


def test_enter_con_el_campo_vacio_no_pide_ingresar_un_producto(
        controller, selector, qt):
    """El aviso de "Ingrese un producto" no tiene que aparecer mas."""
    import libs.Ventanas as V

    avisos = []
    monkeypatch_vista = V.showAlert
    V.showAlert = lambda titulo, mensaje: avisos.append(mensaje)
    try:
        controller.view.textArticulo.clear()
        controller.seleccionar_articulo("")
    finally:
        V.showAlert = monkeypatch_vista

    assert "Ingrese un producto" not in avisos


def test_el_articulo_elegido_se_agrega_como_renglon(controller, selector, qt,
                                                   monkeypatch):
    """Elegir en el catalogo agrega la linea, con su cantidad y su precio."""
    pedidos = []

    def _precio(articulo, cantidad):
        pedidos.append((articulo.nombre, cantidad))
        return (cantidad, Decimal("100"))

    monkeypatch.setattr(controller, "solicitar_cantidad_y_precio", _precio)

    # Por agregar_articulo y no por seleccionar_articulo: agregar la linea es
    # cosa de agregar_articulo, el helper solo devuelve lo elegido.
    controller.view.textArticulo.clear()
    controller.view.textCantidad.setText("2")
    controller.agregar_articulo()

    assert pedidos, "no se pidio cantidad y precio del articulo elegido"
    assert pedidos[0][0] == "Mantenimiento de computadoras"
    assert pedidos[0][1] == Decimal("2")
    assert controller.view.gridVenta.rowCount() == 1


def test_cancelar_el_selector_no_agrega_nada(controller, selector, qt,
                                             monkeypatch):
    selector["elegir"] = False
    monkeypatch.setattr(controller, "solicitar_cantidad_y_precio",
                        lambda *a, **k: pytest.fail("no deberia llamarse"))

    controller.view.textArticulo.clear()
    controller.agregar_articulo()

    assert controller.view.gridVenta.rowCount() == 0


def test_con_texto_escrito_no_se_abre_el_catalogo(controller, selector, qt,
                                                   monkeypatch):
    """Con texto va por el camino de antes: buscar, y si no, crear.

    El catalogo es para cuando no hay nada escrito. Si aparece con texto, el
    operador pierde la eleccion de crear algo nuevo.
    """
    encontrado = _Articulo(1, "Mantenimiento de computadoras")
    selector["n"] = 0
    monkeypatch.setattr(controller, "buscar_articulo",
                        lambda busqueda: encontrado)
    monkeypatch.setattr(controller, "solicitar_cantidad_y_precio",
                        lambda articulo, cantidad: (cantidad, Decimal("100")))

    controller.view.textArticulo.setText("Mantenimiento")
    controller.agregar_articulo()
    _barrer(qt, 200)

    assert selector["n"] == 0, "se abrio el catalogo con texto escrito"
    assert controller.view.gridVenta.rowCount() == 1


def test_con_texto_que_no_existe_sigue_ofreciendo_crear(controller, qt,
                                                        monkeypatch):
    """La rama de crear no se toco: es la que carga algo nuevo."""
    preguntas = []
    monkeypatch.setattr(controller, "buscar_articulo", lambda busqueda: None)
    monkeypatch.setattr(controller, "confirmar_alta",
                        lambda titulo, mensaje, textoOk="Crear cliente":
                        preguntas.append(mensaje) or False)
    monkeypatch.setattr(controller, "solicitar_alta_articulo",
                        lambda busqueda: pytest.fail("no deberia crearse"))

    controller.view.textArticulo.setText("Producto que no existe")
    controller.agregar_articulo()

    assert len(preguntas) == 1
    assert "Producto no encontrado" in preguntas[0]
