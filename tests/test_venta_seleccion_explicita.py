"""Con dos productos parecidos, el operador tiene que elegir cual.

Que estaba pasando
------------------
Con dos articulos cuyos nombres arrancan igual -- dos "WHEY CUTTER 1080G
PROTE+QUEMADOR SPX VAINILLA/...", que despues se diferencian en el sabor
-- escribir una parte del nombre tomaba el primero y ya. Dos caminos
distintos lo hacian, y por eso los dos hacen falta:

1. El dialogo del catalogo hacia `setCurrentRow(0)` en cada tecla que se
   escribia. Con "w" ya quedaban las dos filas con la primera marcada, y
   Enter o el boton Aceptar se la Llevaban.

2. El campo de producto, con texto escrito, llamaba a `buscar_articulo`, que
   termina en `.first()`: se llevaba el primero que devolvia la base, sin
   preguntar. Ahi el operador ni siquiera veia la lista.

Que queda
---------
Con una sola coincidencia se sigue eligiendo sola: no hay nada que decidir y
Enter tiene que servir. Con dos o mas, no se elige nada por el operador: hay
que marcar la fila. Enter sin nada marcado no hace nada, y Aceptar sin nada
marcado no cierra.

Como estos tests correccionan algo que antes estaba mal, el modo de
verificarlos es contra el codigo roto: con `git stash` el archivo nuevo tiene
que fallar con el sintoma exacto (elegir el primero), no con un error de
import o de sintaxis.
"""

import os
import sys
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402


# Los dos de la captura: mismo arranque, distinto final.
WHEY_VAINILLA = "WHEY CUTTER 1080G PROTE+QUEMADOR SPX VAINILLA/AMERICAN CREAM"
WHEY_FRUTILLA = "WHEY CUTTER 1080G PROTE+QUEMADOR SPX VAINILLA/FRUTILLA BOLSA"


class _Articulo(object):
    def __init__(self, idarticulo, nombre, codbarra=""):
        self.idarticulo = idarticulo
        self.nombre = nombre
        self.codbarra = codbarra
        self.preciopub = Decimal("14198.80")
        self.tipoiva = type("T", (), {"iva": Decimal("21")})()


class _Cliente(object):
    def __init__(self, idcliente, nombre, cuit="", dni=0):
        self.idcliente = idcliente
        self.nombre = nombre
        self.cuit = cuit
        self.dni = dni


# Los dos WHEY, en el orden en que los devuelve la base.
CATALOGO = [
    _Articulo(15, WHEY_VAINILLA, "INTWHEYCUTTER1"),
    _Articulo(14, WHEY_FRUTILLA, "INTWHEYCUTTER10"),
]


@pytest.fixture
def qt():
    from PyQt5.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _filtrar(catalogo, texto):
    """Busca como el controlador: por nombre, sin distinguir mayusculas."""
    texto = (texto or "").strip().lower()
    if not texto:
        return list(catalogo), len(catalogo)
    hallados = [a for a in catalogo if texto in a.nombre.lower()]
    return hallados, len(hallados)


# -- El dialogo: no tiene que elegir solo ------------------------------------

def test_escribir_una_parte_no_deja_el_primero_marcado(qt):
    """El sintoma de la primera captura: con "w" el primero queda elegido.

    Con dos coincidencias no se marca ninguna. Si se marcara alguna, Enter o
    Aceptar se llevarían un producto que el operador no eligió.
    """
    from PyQt5.QtWidgets import QDialog
    from vistas.VentaSimple import VentaSimpleSeleccionArticuloDialog

    dialogo = VentaSimpleSeleccionArticuloDialog(
        lambda texto: _filtrar(CATALOGO, texto))
    qt.processEvents()

    dialogo.txtBuscar.setText("w")
    qt.processEvents()

    assert dialogo.listaArticulos.count() == 2
    assert dialogo.listaArticulos.currentRow() == -1, (
        "con 2 coincidencias quedo algo marcado automaticamente (fila {}). "
        "Con productos parecidos eso es elegir por el operador.".format(
            dialogo.listaArticulos.currentRow()))
    assert dialogo.result() != QDialog.Accepted
    dialogo.close()


def test_enter_sin_elegir_no_agrega_ningun_articulo(qt):
    """Enter con dos coincidencias y nada marcado no cierra el dialogo.

    Este es el que mas importaba: si Enter aceptara, el articulo se llevaria
    el primero, que es el bug reportado.

    Se aprieta Enter de verdad con QTest y no se llama al handler: contra el
    codigo viejo el metodo interno no existia y el test moria con
    AttributeError, que dice que le falta un metodo y no que el operador
    estuvo a punto de cobrar el producto equivocado.
    """
    from PyQt5.QtCore import Qt
    from PyQt5.QtTest import QTest
    from PyQt5.QtWidgets import QDialog
    from vistas.VentaSimple import VentaSimpleSeleccionArticuloDialog

    dialogo = VentaSimpleSeleccionArticuloDialog(
        lambda texto: _filtrar(CATALOGO, texto))
    dialogo.show()
    dialogo.txtBuscar.setText("whey cutter")
    dialogo.txtBuscar.setFocus()
    qt.processEvents()

    QTest.keyClick(dialogo.txtBuscar, Qt.Key_Return)
    qt.processEvents()

    assert dialogo.result() != QDialog.Accepted, \
        "Enter sin nada marcado cerro el dialogo: se llevo {}".format(
            dialogo.articulo)
    assert dialogo.articulo is None, \
        "Enter sin nada marcado eligio {}".format(dialogo.articulo)
    dialogo.close()


def test_el_boton_aceptar_sin_elegir_no_cierra(qt):
    """Aceptar tampoco elige por el operador."""
    from PyQt5.QtWidgets import QDialog
    from vistas.VentaSimple import VentaSimpleSeleccionArticuloDialog

    dialogo = VentaSimpleSeleccionArticuloDialog(
        lambda texto: _filtrar(CATALOGO, texto))
    dialogo.txtBuscar.setText("whey cutter")
    qt.processEvents()

    dialogo.accept()
    qt.processEvents()

    assert dialogo.result() != QDialog.Accepted
    assert dialogo.articulo is None
    dialogo.close()


def test_marcar_el_segundo_lo_agrega(qt):
    """Lo que el operador quer��a hacer: marcar el que quiere y listo."""
    from PyQt5.QtWidgets import QDialog
    from vistas.VentaSimple import VentaSimpleSeleccionArticuloDialog

    dialogo = VentaSimpleSeleccionArticuloDialog(
        lambda texto: _filtrar(CATALOGO, texto))
    dialogo.txtBuscar.setText("whey cutter")
    qt.processEvents()

    # El de FRUTILLA, que es el segundo de la lista.
    dialogo.listaArticulos.setCurrentRow(1)
    dialogo.accept()
    qt.processEvents()

    assert dialogo.result() == QDialog.Accepted
    assert dialogo.articulo.nombre == WHEY_FRUTILLA, \
        "eligio {} en vez del marcado".format(dialogo.articulo.nombre)
    dialogo.close()


def test_una_sola_coincidencia_se_elige_sola(qt):
    """Con una sola no hay nada que decidir: se marca y Enter sirve.

    Es lo que hay que dejar intacto. Si esto se rompe, agregar un producto
    con el nombre completo pide un click de mas.

    Por QTest y no por el handler: ver el test de Enter, misma razon.
    """
    from PyQt5.QtCore import Qt
    from PyQt5.QtTest import QTest
    from PyQt5.QtWidgets import QDialog
    from vistas.VentaSimple import VentaSimpleSeleccionArticuloDialog

    dialogo = VentaSimpleSeleccionArticuloDialog(
        lambda texto: _filtrar(CATALOGO, texto))
    dialogo.show()
    dialogo.txtBuscar.setText("frutilla")
    dialogo.txtBuscar.setFocus()
    qt.processEvents()

    assert dialogo.listaArticulos.count() == 1
    assert dialogo.listaArticulos.currentRow() == 0, (
        "con una sola coincidencia no quedo marcada sola: hay que escribir "
        "el nombre completo y un Enter de mas por producto")

    QTest.keyClick(dialogo.txtBuscar, Qt.Key_Return)
    qt.processEvents()

    assert dialogo.result() == QDialog.Accepted
    assert dialogo.articulo.nombre == WHEY_FRUTILLA
    dialogo.close()


def test_el_contador_avisa_que_hay_que_elegir(qt):
    """Sin el aviso, "2 coincidencias" parece un resultado, no una eleccion."""
    from vistas.VentaSimple import VentaSimpleSeleccionArticuloDialog

    dialogo = VentaSimpleSeleccionArticuloDialog(
        lambda texto: _filtrar(CATALOGO, texto))
    dialogo.txtBuscar.setText("w")
    qt.processEvents()

    assert "2 coincidencias" in dialogo.lblCuenta.text()
    dialogo.close()


# -- El campo de producto: con texto tampoco elige solo ----------------------

def test_campo_con_texto_ambiguo_no_toma_el_primero(qt, monkeypatch):
    """La segunda captura: "wh" en el campo y se’agregaba uno de los dos.

    El campo nunca muestra la lista, asi que acá el operador no tendria como
    saber que se eligio por el. Con dos o mas coincidencias tiene que abrirse
    el catalogo acotado.
    """
    from PyQt5.QtWidgets import QDialog
    import controladores.VentaSimple as VS

    monkeypatch.setattr(sys, "argv", [sys.argv[0]])

    controller = VS.VentaSimpleController()
    monkeypatch.setattr(controller, "_coincidencias_articulo",
                        lambda texto, limite=None: _filtrar(CATALOGO, texto))

    abiertos = []

    def _seleccionar(busqueda):
        abiertos.append(busqueda)
        dialogo = VS.VentaSimpleSeleccionArticuloDialog(
            lambda texto: _filtrar(CATALOGO, texto), busqueda=busqueda)
        dialogo.exec_()
        if dialogo.result() != QDialog.Accepted:
            return None
        return dialogo.articulo

    # Devuelve el que el operador marque; aca, el segundo.
    monkeypatch.setattr(controller, "seleccionar_articulo", lambda busqueda: CATALOGO[1])
    monkeypatch.setattr(controller, "solicitar_cantidad_y_precio",
                        lambda a, c: (Decimal("1"), Decimal("14198.80")))

    controller.view.textArticulo.setText("wh")
    controller.agregar_articulo()
    qt.processEvents()

    assert controller.view.gridVenta.rowCount() == 1
    controller.view.Cerrar()


def test_campo_con_texto_ambiguo_abre_el_catalogo(qt, monkeypatch):
    """La forma del bug: tiene que abrirse el catalogo, no elegir de una."""
    import controladores.VentaSimple as VS

    monkeypatch.setattr(sys, "argv", [sys.argv[0]])

    controller = VS.VentaSimpleController()
    monkeypatch.setattr(controller, "_coincidencias_articulo",
                        lambda texto, limite=None: _filtrar(CATALOGO, texto))

    pedidos = []

    def _seleccionar(busqueda):
        pedidos.append(busqueda)
        return CATALOGO[1]

    monkeypatch.setattr(controller, "seleccionar_articulo", _seleccionar)
    monkeypatch.setattr(controller, "solicitar_cantidad_y_precio",
                        lambda a, c: (Decimal("1"), Decimal("14198.80")))

    controller.view.textArticulo.setText("wh")
    controller.agregar_articulo()
    qt.processEvents()

    assert pedidos == ["wh"], (
        "con 2 productos que empiezan igual no se abrio el catalogo: "
        "quedaron {} pedidos de selector".format(len(pedidos)))
    controller.view.Cerrar()


def test_campo_con_una_sola_coincidencia_no_abre_el_catalogo(qt, monkeypatch):
    """Con una sola se agrega directo: es lo que hay que dejar igual."""
    import controladores.VentaSimple as VS

    monkeypatch.setattr(sys, "argv", [sys.argv[0]])

    controller = VS.VentaSimpleController()
    monkeypatch.setattr(controller, "_coincidencias_articulo",
                        lambda texto, limite=None: _filtrar(CATALOGO, texto))
    monkeypatch.setattr(controller, "buscar_articulo", lambda busqueda: CATALOGO[1])
    monkeypatch.setattr(controller, "seleccionar_articulo",
                        lambda b: pytest.fail("no deberia abrirse el catalogo"))
    monkeypatch.setattr(controller, "solicitar_cantidad_y_precio",
                        lambda a, c: (Decimal("1"), Decimal("14198.80")))

    controller.view.textArticulo.setText("frutilla")
    controller.agregar_articulo()
    qt.processEvents()

    assert controller.view.gridVenta.rowCount() == 1
    controller.view.Cerrar()


def test_cancelar_el_catalogo_no_agrega_nada(qt, monkeypatch):
    """Si el operador cancela, no se agrega el primero "por las dudas"."""
    import controladores.VentaSimple as VS

    monkeypatch.setattr(sys, "argv", [sys.argv[0]])

    controller = VS.VentaSimpleController()
    monkeypatch.setattr(controller, "_coincidencias_articulo",
                        lambda texto, limite=None: _filtrar(CATALOGO, texto))
    monkeypatch.setattr(controller, "seleccionar_articulo", lambda b: None)
    monkeypatch.setattr(controller, "buscar_articulo",
                        lambda b: pytest.fail("no deberia elegir el primero"))
    monkeypatch.setattr(controller, "solicitar_cantidad_y_precio",
                        lambda a, c: pytest.fail("no deberia llamarse"))

    controller.view.textArticulo.setText("wh")
    controller.agregar_articulo()
    qt.processEvents()

    assert controller.view.gridVenta.rowCount() == 0
    controller.view.Cerrar()


# -- Clientes: el mismo defecto, otro campo -----------------------------------

def test_clientes_con_nombres_parecidos_tambien_exigen_eleccion(qt):
    """Dos clientes con nombres parecidos no se cobran al primero.

    Es el mismo bug que en articulos: dos "MUNICIPALIDAD DE..." y Enter se
    lleva el de arriba. Cobrarle al cliente equivocado es peor que agregar el
    producto equivocado, asi que el arreglo se aplico tambien aca.
    """
    from PyQt5.QtCore import Qt
    from PyQt5.QtTest import QTest
    from PyQt5.QtWidgets import QDialog
    from vistas.VentaSimple import VentaSimpleSeleccionClienteDialog

    clientes = [
        _Cliente(3, "MUNICIPALIDAD DE CAPIOVI", "30-67243961-9"),
        _Cliente(9, "MUNICIPALIDAD DE CAPITULO", "30-67243962-8"),
    ]

    dialogo = VentaSimpleSeleccionClienteDialog(
        lambda texto: _filtrar(clientes, texto))
    dialogo.show()
    dialogo.txtBuscar.setText("municipalidad")
    dialogo.txtBuscar.setFocus()
    qt.processEvents()

    assert dialogo.listaClientes.count() == 2
    assert dialogo.listaClientes.currentRow() == -1, \
        "con 2 clientes parecidos quedo el primero marcado solo"

    QTest.keyClick(dialogo.txtBuscar, Qt.Key_Return)
    qt.processEvents()
    assert dialogo.result() != QDialog.Accepted
    assert dialogo.cliente is None

    dialogo.listaClientes.setCurrentRow(1)
    dialogo.accept()
    qt.processEvents()

    assert dialogo.result() == QDialog.Accepted
    assert dialogo.cliente.nombre == "MUNICIPALIDAD DE CAPITULO"
    dialogo.close()


def test_un_solo_cliente_se_elige_solo(qt):
    """Con un solo cliente se marca solo: Enter sirve, como antes."""
    from PyQt5.QtCore import Qt
    from PyQt5.QtTest import QTest
    from PyQt5.QtWidgets import QDialog
    from vistas.VentaSimple import VentaSimpleSeleccionClienteDialog

    clientes = [_Cliente(3, "MUNICIPALIDAD DE CAPIOVI", "30-67243961-9")]

    dialogo = VentaSimpleSeleccionClienteDialog(
        lambda texto: _filtrar(clientes, texto))
    dialogo.show()
    dialogo.txtBuscar.setText("capiovi")
    dialogo.txtBuscar.setFocus()
    qt.processEvents()

    assert dialogo.listaClientes.currentRow() == 0
    QTest.keyClick(dialogo.txtBuscar, Qt.Key_Return)
    qt.processEvents()

    assert dialogo.result() == QDialog.Accepted
    assert dialogo.cliente.nombre == "MUNICIPALIDAD DE CAPIOVI"
    dialogo.close()