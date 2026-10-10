import os
import sys
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication


def test_venta_simple_controller_se_puede_construir(monkeypatch):
    monkeypatch.setattr(sys, "argv", [sys.argv[0]])
    app = QApplication.instance() or QApplication([])

    from controladores.VentaSimple import VentaSimpleController

    controller = VentaSimpleController()

    assert controller.view.windowTitle() == "Nueva venta"
    controller.view.Cerrar()


def test_venta_simple_inicia_con_la_forma_de_pago_por_defecto(monkeypatch):
    monkeypatch.setattr(sys, "argv", [sys.argv[0]])
    app = QApplication.instance() or QApplication([])

    from controladores.VentaSimple import VentaSimpleController
    from modelos.Formaspago import Formapago

    controller = VentaSimpleController()

    # La vista elige la forma de pago por id (findData("1")), que es lo que
    # consume el controlador al emitir. El detalle visible ("EFECTIVO",
    # "CONTADO", ...) es dato maestro de la base local, que no se versiona
    # porque *.db esta en .gitignore, asi que se compara contra la propia
    # base y no contra un texto fijo.
    assert controller.view.cboFormaPago.text() == "1"
    assert (
        controller.view.cboFormaPago.currentText().strip().upper()
        == Formapago.get_by_id(1).detalle.strip().upper()
    )
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
    monkeypatch.setattr(controller, "buscar_clientes", lambda busqueda: [ClienteEncontrado()])
    controller.view.textCliente.setText("duomo")

    controller.cargar_cliente_desde_busqueda()

    assert controller.cliente.idcliente == 7
    assert controller.view.checkConsumidorFinal.isChecked() is False
    assert controller.view.textCliente.text() == "7 - DUOMO"
    assert controller.view.textDocumento.text() == "20-12345678-9"
    controller.view.Cerrar()


def test_busqueda_cliente_con_multiples_coincidencias_obliga_a_elegir(monkeypatch):
    monkeypatch.setattr(sys, "argv", [sys.argv[0]])
    app = QApplication.instance() or QApplication([])

    from controladores.VentaSimple import VentaSimpleController

    class ClienteA:
        idcliente = 10
        nombre = "TRAID UNO"
        cuit = "20-00000000-1"
        dni = 0

    class ClienteB:
        idcliente = 11
        nombre = "TRAID DOS"
        cuit = "20-00000000-2"
        dni = 0

    controller = VentaSimpleController()
    monkeypatch.setattr(controller, "buscar_clientes",
                        lambda busqueda, limite=None: [ClienteA(), ClienteB()])
    # `seleccionar_cliente` recibe lo que se escribio, no la lista: el dialogo
    # vuelve a consultar para poder acotar la lista sin cerrarlo. El dialogo en
    # si lo prueba tests/test_busqueda_clientes.py, con 1200 clientes.
    monkeypatch.setattr(controller, "seleccionar_cliente", lambda busqueda: ClienteB())
    controller.view.textCliente.setText("traid")

    controller.cargar_cliente_desde_busqueda()

    assert controller.cliente.idcliente == 11
    assert controller.view.textCliente.text() == "11 - TRAID DOS"
    assert controller.view.textDocumento.text() == "20-00000000-2"
    controller.view.Cerrar()


def test_cliente_no_encontrado_propone_alta_y_lo_carga(monkeypatch):
    monkeypatch.setattr(sys, "argv", [sys.argv[0]])
    app = QApplication.instance() or QApplication([])

    from controladores.VentaSimple import VentaSimpleController

    class ClienteNuevo:
        idcliente = 9
        nombre = "Cliente nuevo"
        cuit = ""
        dni = 12345678

    controller = VentaSimpleController()
    # Se parchea `buscar_clientes`, que es el metodo que se usa. Antes se
    # parcheaba `buscar_cliente` (en singular), que no lo llama nadie: el
    # monkeypatch no tenia efecto y el test pasaba porque la base real no
    # tiene un cliente llamado "Cliente nuevo". Parecia que cubria el camino
    # de "no encontrado" y en realidad no lo cubria.
    monkeypatch.setattr(controller, "buscar_clientes", lambda busqueda, limite=None: [])
    # confirmar_alta recibe textoOk: el boton lo nombra segun lo que se
    # va a crear, asi que el parche tiene que aceptar el parametro.
    monkeypatch.setattr(controller, "confirmar_alta",
                        lambda titulo, mensaje, textoOk="Crear cliente": True)
    monkeypatch.setattr(controller, "solicitar_alta_cliente", lambda busqueda: ClienteNuevo())
    controller.view.textCliente.setText("Cliente nuevo")

    controller.cargar_cliente_desde_busqueda()

    assert controller.cliente.idcliente == 9
    assert controller.view.checkConsumidorFinal.isChecked() is False
    assert controller.view.textCliente.text() == "9 - Cliente nuevo"
    assert controller.view.textDocumento.text() == "12345678"
    controller.view.Cerrar()


def test_agregar_articulo_pide_cantidad_y_precio(monkeypatch):
    monkeypatch.setattr(sys, "argv", [sys.argv[0]])
    app = QApplication.instance() or QApplication([])

    from controladores.VentaSimple import VentaSimpleController

    class TipoIva:
        iva = Decimal("21")

    class ArticuloEncontrado:
        idarticulo = 11
        nombre = "Articulo modal"
        preciopub = Decimal("100.00")
        tipoiva = TipoIva()

    controller = VentaSimpleController()
    monkeypatch.setattr(controller, "buscar_articulo", lambda busqueda: ArticuloEncontrado())
    monkeypatch.setattr(
        controller,
        "solicitar_cantidad_y_precio",
        lambda articulo, cantidad: (Decimal("3"), Decimal("150.00")),
    )
    controller.view.textArticulo.setText("articulo modal")
    controller.view.textCantidad.setText("2")

    controller.agregar_articulo()

    # En una columna numerica ObtenerItem devuelve el numero, no el texto de
    # la celda: el texto lleva el formato de presentacion (1.250,50) y el valor
    # crudo es el que sirve para calcular. El texto se puede comprobar aparte
    # con .text() de la celda.
    assert controller.view.gridVenta.ObtenerItem(fila=0, col="Cant.") == Decimal("3")
    assert controller.view.gridVenta.ObtenerItem(fila=0, col="Unitario") == Decimal("150.00")
    assert controller.view.gridVenta.ObtenerItem(fila=0, col="SubTotal") == Decimal("450.00")
    assert controller.view.gridVenta.item(0, 0).text() == "3"
    # Por encabezado y no con un indice fijo: la columna Stock se metio en el
    # medio y corrio todas las de la derecha. Con el indice, agregar una
    # columna rompe esto sin que se entienda por que, porque la asercion
    # sigue mirando "la tercera" y ahora es otra cosa.
    columnas = {controller.view.gridVenta.horizontalHeaderItem(c).text(): c
                for c in range(controller.view.gridVenta.columnCount())}
    assert controller.view.gridVenta.item(0, columnas["Unitario"]).text() == "150,00"
    # El total se ve con el formato argentino, como los SubTotal de arriba.
    # Antes decia "450.00", que era `str(Decimal)` puesto a mano. El numero no
    # cambia; la asercion estaba fijando el formato viejo, asi que hubo que
    # cambiarla, y ese es el punto: un aserto sobre texto de presentacion
    # cambia cuando la presentacion mejora.
    assert controller.view.textTotal.text() == "450,00"
    controller.view.Cerrar()


def test_articulo_no_encontrado_propone_alta_y_lo_agrega(monkeypatch):
    monkeypatch.setattr(sys, "argv", [sys.argv[0]])
    app = QApplication.instance() or QApplication([])

    from controladores.VentaSimple import VentaSimpleController

    class TipoIva:
        iva = Decimal("21")

    class ArticuloNuevo:
        idarticulo = 12
        nombre = "Articulo nuevo"
        preciopub = Decimal("80.00")
        tipoiva = TipoIva()

    controller = VentaSimpleController()
    monkeypatch.setattr(controller, "buscar_articulo", lambda busqueda: None)
    # confirmar_alta recibe textoOk: el boton lo nombra segun lo que se
    # va a crear, asi que el parche tiene que aceptar el parametro.
    monkeypatch.setattr(controller, "confirmar_alta",
                        lambda titulo, mensaje, textoOk="Crear cliente": True)
    monkeypatch.setattr(controller, "solicitar_alta_articulo", lambda busqueda: ArticuloNuevo())
    monkeypatch.setattr(
        controller,
        "solicitar_cantidad_y_precio",
        lambda articulo, cantidad: (Decimal("2"), Decimal("80.00")),
    )
    controller.view.textArticulo.setText("Articulo nuevo")

    controller.agregar_articulo()

    assert controller.view.gridVenta.ObtenerItem(fila=0, col="Codigo") == "12"
    assert controller.view.gridVenta.ObtenerItem(fila=0, col="Detalle") == "Articulo nuevo"
    assert controller.view.gridVenta.ObtenerItem(fila=0, col="SubTotal") == Decimal("160.00")
    controller.view.Cerrar()


def test_solicitar_cantidad_y_precio_acepta_dialogo_formulario(monkeypatch):
    monkeypatch.setattr(sys, "argv", [sys.argv[0]])
    app = QApplication.instance() or QApplication([])

    import controladores.VentaSimple as venta_simple
    from controladores.VentaSimple import VentaSimpleController

    class TipoIva:
        iva = Decimal("21")

    class ArticuloEncontrado:
        idarticulo = 11
        nombre = "Articulo modal"
        preciopub = Decimal("100.00")
        tipoiva = TipoIva()

    class DialogoAceptado:
        def __init__(self, articulo, cantidad, precio):
            self.articulo = articulo
            self.cantidad = cantidad
            self.precio = precio

        def exec_(self):
            return None

        def result(self):
            return 1

        def valores(self):
            return "4", "125.50"

    controller = VentaSimpleController()
    monkeypatch.setattr(venta_simple, "VentaSimpleCantidadPrecioDialog", DialogoAceptado)

    cantidad, precio = controller.solicitar_cantidad_y_precio(ArticuloEncontrado(), Decimal("2"))

    assert cantidad == Decimal("4")
    assert precio == Decimal("125.50")
    controller.view.Cerrar()


def test_el_total_va_resaltado(monkeypatch):
    monkeypatch.setattr(sys, "argv", [sys.argv[0]])
    app = QApplication.instance() or QApplication([])

    from controladores.VentaSimple import VentaSimpleController

    controller = VentaSimpleController()

    # El Total es lo que se mira para cobrar: lleva objectName para que el
    # tema lo pinte grande (temas/pyfe.css), y negrita en el propio widget
    # por si el tema no carga.
    assert controller.view.textTotal.objectName() == "totalVenta"
    assert controller.view.textTotal.font().bold()
    assert controller.view.textTotal.font().pointSizeF() >= 20
    assert controller.view.lblTotal.objectName() == "etiquetaTotal"
    controller.view.Cerrar()


class ClienteElegido:
    idcliente = 7
    nombre = "DUOMO"
    cuit = "20-12345678-9"
    dni = 0


def test_enter_en_cliente_vacio_abre_el_buscador(monkeypatch):
    """Enter sin texto y sin CF abre la busqueda, como en producto."""
    monkeypatch.setattr(sys, "argv", [sys.argv[0]])
    app = QApplication.instance() or QApplication([])

    from controladores.VentaSimple import VentaSimpleController

    controller = VentaSimpleController()
    controller.view.checkConsumidorFinal.setChecked(False)
    controller.view.textCliente.setText("")
    elegidos = []
    monkeypatch.setattr(
        controller, "seleccionar_cliente",
        lambda busqueda: elegidos.append(busqueda) or ClienteElegido())

    controller.view.textCliente.returnPressed.emit()

    assert elegidos == [""]
    assert controller.cliente.idcliente == 7
    assert controller.view.textCliente.text() == "7 - DUOMO"
    assert controller.view.textDocumento.text() == "20-12345678-9"
    controller.view.Cerrar()


def test_enter_en_cliente_vacio_cancelado_no_carga_nada(monkeypatch):
    monkeypatch.setattr(sys, "argv", [sys.argv[0]])
    app = QApplication.instance() or QApplication([])

    from controladores.VentaSimple import VentaSimpleController

    controller = VentaSimpleController()
    controller.view.checkConsumidorFinal.setChecked(False)
    controller.view.textCliente.setText("")
    monkeypatch.setattr(controller, "seleccionar_cliente", lambda busqueda: None)

    controller.view.textCliente.returnPressed.emit()

    assert controller.cliente is None
    assert controller.view.textCliente.text() == ""
    controller.view.Cerrar()


def test_enter_en_cliente_vacio_con_cf_no_busca(monkeypatch):
    """Con consumidor final no hay cliente que buscar."""
    monkeypatch.setattr(sys, "argv", [sys.argv[0]])
    app = QApplication.instance() or QApplication([])

    from controladores.VentaSimple import VentaSimpleController

    controller = VentaSimpleController()
    controller.view.checkConsumidorFinal.setChecked(True)
    controller.view.textCliente.setText("")
    llamadas = []
    monkeypatch.setattr(
        controller, "seleccionar_cliente",
        lambda busqueda: llamadas.append(busqueda))

    controller.view.textCliente.returnPressed.emit()

    assert llamadas == []
    controller.view.Cerrar()


def test_enter_con_texto_no_abre_el_buscador(monkeypatch):
    """Con texto, Enter lo resuelve editingFinished: aca no se abre nada."""
    monkeypatch.setattr(sys, "argv", [sys.argv[0]])
    app = QApplication.instance() or QApplication([])

    from controladores.VentaSimple import VentaSimpleController

    controller = VentaSimpleController()
    controller.view.checkConsumidorFinal.setChecked(False)
    controller.view.textCliente.setText("muni")
    llamadas = []
    monkeypatch.setattr(
        controller, "seleccionar_cliente",
        lambda busqueda: llamadas.append(busqueda))

    controller.view.textCliente.returnPressed.emit()

    assert llamadas == []
    controller.view.Cerrar()
