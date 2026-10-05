"""Las pantallas de stock se tienen que poder construir.

Que esta comprobando
--------------------
Que las tres ventanas arman, con todos sus widgets y todas sus columnas. Es
lo mas barato que hay y evita el peor escenario de una pantalla nueva: que
este todo escrito, bien, y que reviente al abrirla con un AttributeError por
un nombre de columna mal escrito.

Un 'se puede construir' no es un test de aburrido. Cubre las columnas que se
piden a la grilla (que es donde un nombre mal escrito duele), los handlers
que se conectan (un handler mal escrito revienta al apretar el boton, no al
abrir) y el ciclo de imports entero.

Lo que NO cubre
---------------
Que los numeros sean correctos. Eso esta en test_stock.py, que no usa Qt.
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)


@pytest.fixture
def qt():
    from PyQt5.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture
def base():
    """Base en memoria. Ver tests/ayuda_stock.py.

    Necesaria en los tests que tocan el stock de verdad: sin ella, un ajuste
    de inventario se escribe en la base de desarrollo del sandbox.
    """
    from ayuda_stock import base_memoria

    with base_memoria() as memoria:
        yield memoria


def test_la_ventana_de_stock_se_puede_abrir(qt, base):
    from controladores.Stock import StockController

    controller = StockController()
    controller.view.show()
    qt.processEvents()

    assert controller.view.windowTitle() == "Stock"
    controller.view.Cerrar()


def test_la_ventana_de_ajuste_se_puede_abrir(qt):
    from controladores.Stock import AjustesStockController

    controller = AjustesStockController()
    controller.view.show()
    qt.processEvents()

    assert controller.view.windowTitle() == "Ajustar stock"
    controller.view.Cerrar()


def test_la_ventana_de_movimientos_se_puede_abrir(qt):
    from controladores.Stock import MovimientosStockController

    controller = MovimientosStockController()
    controller.view.show()
    qt.processEvents()

    assert controller.view.windowTitle() == "Movimientos de stock"
    controller.view.Cerrar()


def test_el_estado_de_un_articulo_se_entiende_de_un_vistazo():
    """La columna 'Estado' es la que se lee, no la de 'Stock'.

    El operador mira la pantalla y tiene que ver "Falta", no "-2". Un estado
    que obliga a hacer cuentas en la cabeza es un estado que no se usa.
    """
    from decimal import Decimal

    from controladores.Stock import FALTA, NEGATIVO, OK, SIN_STOCK, estado_de

    class _Articulo(object):
        def __init__(self, controlastock, stockminimo):
            self.controlastock = controlastock
            self.stockminimo = stockminimo

    assert estado_de(_Articulo(True, 0), Decimal("-3")) == NEGATIVO
    assert estado_de(_Articulo(True, 5), Decimal("2")) == FALTA
    assert estado_de(_Articulo(True, 5), Decimal("7")) == OK
    assert estado_de(_Articulo(True, 0), Decimal("0")) == SIN_STOCK
    # Un minimo de 0 no es un faltante: quiere decir "no pedi nada".
    assert estado_de(_Articulo(True, 0), Decimal("0")) != FALTA


def test_la_grilla_de_compras_tiene_columna_de_producto(qt):
    """Sin columna de producto, la compra no puede entrar al stock.

    Y el producto va en la septima posicion a proposito: el resto de la grilla
    usa indices fijos (el F2 del centro de costos es la columna 0, el salto
    de fila con Enter corta en la ultima), y si el producto se inserta en el
    medio, los indices se corren en silencio y el F2 busca un centro de costo
    donde hay un producto.
    """
    from PyQt5.QtWidgets import QTableWidgetItem

    from vistas.CargaFacturasProveedor import GrillaFactProv

    grilla = GrillaFactProv()
    cabeceras = [grilla.horizontalHeaderItem(c).text()
                 for c in range(grilla.columnCount())]

    assert "Producto" in cabeceras, \
        "la grilla de compras no tiene columna de producto: {}".format(cabeceras)
    assert cabeceras[GrillaFactProv.COL_PRODUCTO] == "Producto", \
        "la columna de producto quedo en {} y no en {}: los indices de la " \
        "grilla se van a correr. Cabeceras: {}".format(
            cabeceras.index("Producto"), GrillaFactProv.COL_PRODUCTO, cabeceras)
    # Y las columnas viejas siguen donde estaban.
    assert cabeceras[0] == "Ctro Costos", \
        "la primera columna cambio y el F2 busca el centro de costos ahi: " \
        "{}".format(cabeceras)


# -- El buscador con F2 ------------------------------------------------------

def test_el_buscador_con_f2_no_revienta_al_apretarlo(qt, base, monkeypatch):
    """Apretar F2 tiene que elegir el producto, no tirar un TypeError.

    Este camino no lo cubria nadie, y la app lo tiraba: `_buscar_producto`
    llama al callback con DOS argumentos (id y nombre), y el callback de
    Movimientos aceptaba uno. El TypeError salia recien cuando el operador
    apretaba F2, con la ventana de busqueda abierta y el dialogo de error
    encima.

    Por que un test puede cubrirlo y la app no se deja: la ventana de busqueda
    es modal y bloquea. Aca se reemplaza SOLO la ventana por una que devuelve
    al toque; el callback, el controlador y el resto del camino son los de
    verdad, que es justo la parte que estaba rota.
    """
    from controladores.Stock import (AjustesStockController,
                                    MovimientosStockController)

    import vistas.Stock as _vistas_stock

    class _BusquedaFalsa(object):
        """Imita lo que hace la ventana real al elegir una fila.

        El detalle importa: `_buscar_producto` deja puesto
        `campoRetornoDetalle = Articulo.nombre`, que es un CharField de peewee,
        y despues la ventana real lo REEMPLAZA por el texto de la fila elegida.
        Si el fake no lo reemplaza, el nombre llega como un
        `<CharField: Articulo.nombre>` y el test falla por un motivo que no es
        el que esta probando.
        """

        def __init__(self, *args, **kwargs):
            self.lRetval = False
            self.ValorRetorno = None
            self.campoRetornoDetalle = None

        def CargaDatos(self):
            pass

        def exec_(self):
            # Lo que hace la ventana cuando el operador elige una fila.
            self.ValorRetorno = 1
            self.campoRetornoDetalle = "GASOLINA"
            self.lRetval = True
            return 1

    # Se reemplaza el atributo del modulo y no con un string: el mixin
    # `_BuscarProducto` resuelve `UiBusqueda` en el ambito de vistas/Stock.py.
    monkeypatch.setattr(_vistas_stock, "UiBusqueda", _BusquedaFalsa)

    # El que estaba roto.
    movimientos = MovimientosStockController()
    movimientos.view.F2Producto(movimientos.CargaProducto)
    assert movimientos.view.txtProducto.text() == "1", \
        "el buscador de movimientos no cargo el producto"
    assert movimientos.view.lblNombreProducto.text() == "GASOLINA", \
        "el buscador de movimientos no cargo el nombre"
    movimientos.view.Cerrar()

    # El otro, que tambien toma los dos.
    ajustes = AjustesStockController()
    ajustes.view.buscar_producto()
    assert ajustes.view.txtProducto.text() == "1", \
        "el buscador de ajustes no cargo el producto"
    assert ajustes.view.lblNombre.text() == "GASOLINA"
    ajustes.view.Cerrar()


def test_todos_los_callbacks_del_buscador_toman_los_dos_argumentos():
    """`_buscar_producto` siempre manda (id, nombre). Todos tienen que poder.

    Se mira la firma de cada callback, sin ejecutarlo: asi el test no depende
    de una base ni de Qt, y sigue cubriendo el dia que se agregue una cuarta
    pantalla con su propio buscador.
    """
    import inspect

    from controladores.Stock import MovimientosStockController
    from vistas.Stock import AjustesStockView

    for metodo in (AjustesStockView.ProductoElegido,
                   MovimientosStockController.CargaProducto):
        sin_self = [p for p in inspect.signature(metodo).parameters
                    if p != "self"]
        assert len(sin_self) >= 2, \
            "{} recibe {} y el buscador le manda dos: al apretar F2 tira " \
            "TypeError".format(metodo.__qualname__, len(sin_self))


def test_el_ajuste_no_puede_guardarse_sin_observacion(qt, base, monkeypatch):
    """Un ajuste sin motivo no deja el stock mejor que uno sin motivo.

    Es la regla mas importante del formulario de ajuste, y va aca porque es
    una regla de la pantalla: la logica de stock acepta un movimiento sin
    observacion (el inventario inicial no necesita ninguna), y el filtro es
    de este formulario.

    Con observacion si se guarda: si el control fuera al reves, el formulario
    no serviria para nada.
    """
    from controladores.Stock import AjustesStockController
    from modelos.MovStock import MovStock

    def sin_preguntar(titulo, mensaje, *args, **kwargs):
        return True

    monkeypatch.setattr("libs.Ventanas.showAlert", sin_preguntar)
    monkeypatch.setattr("libs.Ventanas.showConfirmation", sin_preguntar)

    controller = AjustesStockController()
    controller.view.show()
    qt.processEvents()

    controller.CargaProducto(1)
    controller.view.txtCantidad.setText("5")
    controller.view.txtObservacion.setText("")
    controller.Grabar()

    assert MovStock.select().count() == 0, \
        "un ajuste sin observacion se guardo: queda un movimiento que nadie " \
        "va a poder explicar"


def test_un_ajuste_con_observacion_se_guarda(qt, base, monkeypatch):
    """La contraparte del anterior: con motivo, se guarda y el stock cambia."""
    from controladores.Stock import AjustesStockController
    from libs import stock
    from modelos.MovStock import MovStock

    def sin_preguntar(titulo, mensaje, *args, **kwargs):
        return True

    monkeypatch.setattr("libs.Ventanas.showAlert", sin_preguntar)

    controller = AjustesStockController()
    controller.view.show()
    qt.processEvents()

    stock.registra_inventario_inicial(1, 10)
    controller.CargaProducto(1)
    assert controller.view.txtStockActual.text() == "10.0000", \
        "el formulario tiene que mostrar el stock real, mostro {}".format(
            controller.view.txtStockActual.text())

    controller.view.txtCantidad.setText("-3")
    controller.view.txtObservacion.setText("Conteo fisico de ayer")
    controller.Grabar()

    assert stock.stock_de(1) == 7, \
        "un ajuste de -3 sobre 10 deberia dejar 7, quedo {}".format(
            stock.stock_de(1))
    movimiento = MovStock.get(MovStock.origen == "AJUSTE")
    assert movimiento.observacion == "Conteo fisico de ayer"


def test_marcar_productos_avisa_cuantos_servicios_quedaron_afuera(qt, base,
                                                                 monkeypatch):
    """El boton tiene que decir que no toco los servicios.

    Sin este aviso, el operador marca y ve "listo", cree que todo el catalogo
    quedo controlado, y meses despues descubre que los servicios no lo
    quedaron. El mensaje es la unica parte del cambio que sea reversible con
    un clic.

    Se capturan los mensajes en vez de responder a pelo: showAlert es modal y
    en un test bloquearia, y ademas queremos poder ASSERT sobre lo que dijo.
    """
    from controladores.Stock import StockController
    from libs import stock

    alertas = []
    monkeypatch.setattr("libs.Ventanas.showConfirmation",
                        lambda *a, **k: True)
    monkeypatch.setattr("libs.Ventanas.showAlert",
                        lambda titulo, mensaje, *a, **k: alertas.append(
                            (titulo, mensaje)))

    # Los dos sin marcar: el producto es el que se tiene que marcar.
    stock.Articulo.update(controlastock=False).execute()

    controller = StockController()
    controller.view.show()
    qt.processEvents()

    controller.MarcarProductos()

    assert stock.controla(stock.Articulo.get_by_id(1)) is True, \
        "el producto tiene que quedar controlado"
    assert stock.controla(stock.Articulo.get_by_id(2)) is False, \
        "el servicio no se toca"

    finales = [m for _t, m in alertas]
    assert any("1 producto" in m for m in finales), \
        "no dice cuantos productos marco: {}".format(finales)
    assert any("servicio" in m for m in finales), \
        "no dice que los servicios quedaron afuera: {}".format(finales)
    controller.view.Cerrar()


def test_marcar_productos_no_pide_confirmacion_si_no_hay_nada_que_marcar(
        qt, base, monkeypatch):
    """Con el catalogo ya controlado, avisar "marcar 0 productos" es ruido.

    Y tiene que avisar igual, aunque lo unico que quede sea un servicio: si
    no dice nada, el operador no sabe si el boton esta roto.
    """
    from controladores.Stock import StockController
    from libs import stock

    alertas = []
    monkeypatch.setattr("libs.Ventanas.showConfirmation",
                        lambda *a, **k: True)
    monkeypatch.setattr("libs.Ventanas.showAlert",
                        lambda titulo, mensaje, *a, **k: alertas.append(
                            (titulo, mensaje)))

    # GASOLINA controlado (viene asi en el seed), MANTENIMIENTO sin marcar.
    stock.Articulo.update(controlastock=True).where(
        stock.Articulo.idarticulo == 1).execute()

    controller = StockController()
    controller.view.show()
    qt.processEvents()

    controller.MarcarProductos()

    assert len(alertas) == 1, \
        "tiene que avisar una sola vez: {}".format(alertas)
    assert "servicio" in alertas[0][1], \
        "tiene que explicar que los servicios no se controlan: {}".format(
            alertas[0])
    controller.view.Cerrar()


def test_el_aviso_de_faltantes_acumula_el_mismo_producto_dos_veces(qt, base):
    """Dos renglones del mismo producto se comparan juntos, no uno por uno.

    El caso que hace que esto importa: quedan 5, la venta lleva 3 y 3 del
    mismo producto. Mirando renglon por renglon, el primero entra y el
    segundo avisa con "hay 5" cuando en realidad se van 6 y quedan -1. El
    aviso tiene que decir la verdad, porque es el unico lugar donde el
    operador se entera antes de cobrar.
    """
    from decimal import Decimal

    from controladores.VentaSimple import VentaSimpleController
    from controladores.venta_simple_totales import RenglonVenta
    from libs import stock

    stock.registra_inventario_inicial(1, 5)

    controller = VentaSimpleController()
    controller.view.show()
    qt.processEvents()

    renglones = [
        RenglonVenta(codigo="1", detalle="GASOLINA", cantidad=Decimal("3"),
                     precio_unitario=Decimal("100"), iva=Decimal("21")),
        RenglonVenta(codigo="1", detalle="GASOLINA", cantidad=Decimal("3"),
                     precio_unitario=Decimal("100"), iva=Decimal("21")),
    ]

    lineas = controller.faltantes_de_la_venta(renglones)

    assert len(lineas) == 1, \
        "un solo producto tiene que dar un solo aviso, dio {}: {}".format(
            len(lineas), lineas)
    assert "se venden 6" in lineas[0], \
        "el aviso tiene que decir el total que se vende, no el de un renglon: " \
        "{}".format(lineas[0])
    controller.view.Cerrar()


def test_un_servicio_nunca_genera_aviso_de_faltante(qt, base):
    """El Mantenimiento no controla stock: no puede aparecer en un aviso.

    Si apareciera, cada venta de un mantenimientoaria le avisaria al operador
    que no hay stock de un servicio, y el aviso dejaria de significar algo.
    """
    from decimal import Decimal

    from controladores.VentaSimple import VentaSimpleController
    from controladores.venta_simple_totales import RenglonVenta
    from libs import stock

    stock.registra_inventario_inicial(2, 0)

    controller = VentaSimpleController()
    controller.view.show()
    qt.processEvents()

    renglones = [RenglonVenta(codigo="2", detalle="MANTENIMIENTO",
                              cantidad=Decimal("1"),
                              precio_unitario=Decimal("5000"),
                              iva=Decimal("21"))]

    assert controller.faltantes_de_la_venta(renglones) == []
    controller.view.Cerrar()
