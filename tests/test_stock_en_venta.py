"""La venta tiene que mostrar el stock mientras se arma la venta.

Que esta comprobando
--------------------
Que la grilla de Venta rapida tenga una columna de stock, que diga cuanto hay
de cada producto, y que se pinte de rojo cuando la venta se lleva mas de lo
que hay.

Por que importa mas de lo que parece
------------------------------------
Antes, el operador se enteraba del faltante AL FINAL: cuando ya habia escrito
toda la venta y el boton Emitir abria el aviso de "se venden 6 y hay 5". Para
entonces el trabajo de tipear estaba hecho, y en un mostrador con cola el
tiempo que se tardo es tiempo en el que el cliente espera.

Con la columna, el faltante se ve mientras se carga. El aviso previo a emitir
se queda como esta (no se quita: avisa del total de toda la venta, que una
columna fila por fila no puede saber), pero pasa a ser la segunda vez que se
ve y no la primera.

Que NO comprueba
---------------
Que el stock este bien. Eso esta en test_stock.py, que no usa Qt.

Los indices de columna importan
-------------------------------
`columnasHabilitadas` de la grilla son indices, no nombres. Agregar una columna
en el medio los corre en silencio: una columna que era editable pasa a serlo
otra y la grilla queda editable donde no debe. Por eso este archivo mira los
indices contra los nombres, y no solo que la columna exista.
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

    Necesaria de verdad: estos tests escriben movimientos, y sin ella un
    inventario de prueba queda escrito en la base de desarrollo.
    """
    from ayuda_stock import base_memoria

    with base_memoria() as memoria:
        yield memoria


def _columna_de(grilla, nombre):
    """El indice de la columna con ese encabezado, o None."""
    for c in range(grilla.columnCount()):
        if grilla.horizontalHeaderItem(c).text() == nombre:
            return c
    return None


def _pintada(grilla, fila, col):
    """True si la celda tiene un fondo puesto de verdad.

    Se mira el `style()` del brush y no el color: una celda sin pintar tiene
    una QColor invalida, y comparar su nombre con el blanco daria una respuesta
    que depende del tema y no de lo que el test quiere preguntar.
    """
    from PyQt5.QtCore import Qt

    item = grilla.item(fila, col)
    if item is None:
        return False
    return item.background().style() != Qt.NoBrush


def _agregar(controller, idarticulo, cantidad):
    """Agrega un renglon por el camino real, sin el dialogo modal.

    `_agregar_este_articulo` es lo que usan los dos caminos de la pantalla (el
    selector del catalogo y el nombre escrito), y es el que arma la fila. Lo
    unico que se reemplaza es `solicitar_cantidad_y_precio`, que abre un
    dialogo: el resto del camino es el de verdad, que es justo la parte que
    tiene que quedar probada.
    """
    from decimal import Decimal

    from modelos.Articulos import Articulo

    articulo = Articulo.get_by_id(idarticulo)
    controller.solicitar_cantidad_y_precio = (
        lambda art, cant: (Decimal(str(cantidad)), Decimal(str(art.preciopub))))
    controller._agregar_este_articulo(articulo)


def _abrir(qt, base):
    from controladores.VentaSimple import VentaSimpleController

    controller = VentaSimpleController()
    controller.view.show()
    qt.processEvents()
    return controller


def test_la_venta_tiene_columna_de_stock(qt):
    """Sin la columna, el faltante no se ve hasta emitir."""
    from vistas.VentaSimple import VentaSimpleView

    view = VentaSimpleView()
    cabeceras = [view.gridVenta.horizontalHeaderItem(c).text()
                 for c in range(view.gridVenta.columnCount())]

    assert "Stock" in cabeceras, \
        "la grilla de la venta no tiene columna de stock: {}".format(cabeceras)
    view.Cerrar()


def test_la_columna_de_stock_no_es_editable(qt):
    """El stock es un dato derivado, no algo que el operador escriba.

    Si fuera editable, escribir ahi un numero haria creer que el stock cambio
    y no se guardaria ningun movimiento: la pantalla mentiria sobre lo que hay
    en el deposito. La unica forma de cambiar el stock es un ajuste.
    """
    from vistas.VentaSimple import VentaSimpleView

    view = VentaSimpleView()
    col = _columna_de(view.gridVenta, "Stock")

    assert col is not None, "no hay columna Stock"
    assert col not in view.gridVenta.columnasHabilitadas, \
        "la columna Stock quedo editable: alguien podria escribir un stock " \
        "que no existe. Editables={}".format(
            view.gridVenta.columnasHabilitadas)
    view.Cerrar()


def test_agregar_un_producto_muestra_cuanto_hay(qt, base):
    """La columna dice el stock real del producto."""
    from libs import stock

    stock.registra_inventario_inicial(1, 10)

    controller = _abrir(qt, base)
    _agregar(controller, 1, 2)

    grilla = controller.view.gridVenta
    assert grilla.rowCount() == 1, \
        "no se agrego el renglon: hay {}".format(grilla.rowCount())

    col = _columna_de(grilla, "Stock")
    assert "10" in grilla.item(0, col).text(), \
        "la columna tiene que mostrar el stock real (10), muestra '{}'".format(
            grilla.item(0, col).text())
    controller.view.Cerrar()


def test_un_renglon_que_no_alcanza_se_pinte(qt, base):
    """El color es lo que hace que se note sin leer los numeros.

    Hay 5, el renglon se lleva 6. El 5 y el 6 juntos se leen como cualquier
    cosa; un 5 con fondo rojo dice "este renglon no entra" de un vistazo, que
    es para lo que esta la columna.
    """
    from libs import stock

    stock.registra_inventario_inicial(1, 5)

    controller = _abrir(qt, base)
    _agregar(controller, 1, 6)

    grilla = controller.view.gridVenta
    col = _columna_de(grilla, "Stock")

    assert _pintada(grilla, 0, col), \
        "el renglon que no alcanza tiene que tener la celda de Stock pintada"
    controller.view.Cerrar()


def test_un_renglon_que_alcanza_no_se_pinte(qt, base):
    """La contraparte: si todo se pinta, el color no dice nada.

    Este es el test que evita el modo de falla de "pinto la fila entera sin
    mirar": un color que aparece siempre deja de avisar.
    """
    from libs import stock

    stock.registra_inventario_inicial(1, 10)

    controller = _abrir(qt, base)
    _agregar(controller, 1, 3)

    grilla = controller.view.gridVenta
    col = _columna_de(grilla, "Stock")

    assert not _pintada(grilla, 0, col), \
        "un renglon que alcanza no tiene que pintarse"
    controller.view.Cerrar()


def test_dos_renglones_del_mismo_producto_suman_para_el_color(qt, base):
    """La columna tiene que coincidir con el aviso de emitir.

    El caso que lo hace necesario: hay 5 y el operador carga el mismo producto
    dos veces, de a 3. Mirando renglon por renglon los dos "entran" (3 < 5) y la
    columna queda de un color que dice "estas bien". Pero la venta se lleva 6, y
    el aviso previo a emitir va a preguntar.

    Si la columna y el aviso dicen cosas distintas, el primero que se mire deja
    de servir. Es el mismo error del que ya se corrigio para el texto del aviso
    (tests/test_stock_ui.py), pero del lado de la grilla.
    """
    from libs import stock

    stock.registra_inventario_inicial(1, 5)

    controller = _abrir(qt, base)
    _agregar(controller, 1, 3)
    _agregar(controller, 1, 3)

    grilla = controller.view.gridVenta
    col = _columna_de(grilla, "Stock")

    assert grilla.rowCount() == 2, "no se agregaron los dos renglones"

    for fila in range(2):
        assert _pintada(grilla, fila, col), \
            "los dos renglones juntos se llevan 6 de 5: los dos tienen que " \
            "estar pintados, y el renglon {} no lo esta".format(fila)
    controller.view.Cerrar()


def test_un_servicio_muestra_guion_y_no_se_pinte(qt, base):
    """Un servicio no tiene stock: la columna dice que no aplica.

    Poner "0" seria mentir (dice que no hay, cuando en realidad no hay nada
    que contar), y pintarlo de rojo seria gritarle al operador por algo que
    esta bien. Un guion y el color normal.
    """
    controller = _abrir(qt, base)
    _agregar(controller, 2, 1)

    grilla = controller.view.gridVenta
    col = _columna_de(grilla, "Stock")

    texto = grilla.item(0, col).text().strip()
    assert texto in ("-", "—", ""), \
        "un servicio tiene que mostrar que el stock no aplica, muestra " \
        "'{}'".format(texto)

    assert not _pintada(grilla, 0, col), "un servicio no se pinta de rojo"
    controller.view.Cerrar()


def test_editar_la_cantidad_recalcula_el_color(qt, base):
    """Si el operador edita la cantidad, el color cambia.

    Sin esto, se carga 6 de 5 (pintado), corrige a 3 y la fila sigue pintada: la
    columna esta mintiendo con la unica informacion que el operador tiene para
    decidir. Eso es peor que no tenerla.

    Se edita la celda de verdad, con setText. No hace falta emitir la senal a
    mano: QTableWidgetItem avisa solo, asi que si el handler se engancha a otra
    cosa, este test lo ve igual.
    """
    from libs import stock

    stock.registra_inventario_inicial(1, 5)

    controller = _abrir(qt, base)
    _agregar(controller, 1, 6)

    grilla = controller.view.gridVenta
    col_stock = _columna_de(grilla, "Stock")
    col_cant = _columna_de(grilla, "Cant.")

    assert _pintada(grilla, 0, col_stock), "arranca pintado con 6 de 5"

    grilla.item(0, col_cant).setText("2")
    qt.processEvents()

    assert not _pintada(grilla, 0, col_stock), \
        "con 2 de 5 la fila tiene que dejar de estar pintada"
    controller.view.Cerrar()


def test_editar_la_cantidad_cambia_lo_que_se_factura(qt, base):
    """La factura tiene que llevar la cantidad editada, no la que estaba.

    Este es el que mas plata cuesta si se rompe. `AgregaItem` guarda el numero
    en `UserRole` y `ObtenerItem` lo devuelve crudo, pero editar la celda solo
    cambia el TEXTO. Sin volver a dejar el numero crudo, `obtener_renglones`
    arma la factura con la cantidad vieja: la pantalla muestra 4, el comprobante
    dice 2, y el operador no tiene por donde ver que paso.

    Va con el mismo camino de edicion que los otros, porque si el arreglo
    dependiera de que se pulse Enter y no de que cambie la celda, el bug
    volveria con el mouse.
    """
    from libs import stock

    stock.registra_inventario_inicial(1, 100)

    controller = _abrir(qt, base)
    _agregar(controller, 1, 2)

    grilla = controller.view.gridVenta
    col_cant = _columna_de(grilla, "Cant.")

    grilla.item(0, col_cant).setText("7")
    qt.processEvents()

    renglones = controller.obtener_renglones()

    assert len(renglones) == 1
    assert renglones[0].cantidad == 7, \
        "la factura se arma con la cantidad de la grilla, y tiene que ser la " \
        "editada: dio {}".format(renglones[0].cantidad)
    controller.view.Cerrar()


def test_editar_con_coma_decimal_no_revienta_la_lectura(qt, base):
    """El operador escribe "2,50" y eso tiene que valer dos y media.

    La celda muestra los numeros como se leen aca (coma decimal), asi que
    escribir con coma es lo normal, no la excepcion. Si la celda queda con el
    texto pero sin numero crudo, el `Decimal("2,50")` revienta al armar la
    venta con un error que no dice que celda fue.
    """
    from libs import stock

    stock.registra_inventario_inicial(1, 100)

    controller = _abrir(qt, base)
    _agregar(controller, 1, 1)

    grilla = controller.view.gridVenta
    col_cant = _columna_de(grilla, "Cant.")

    grilla.item(0, col_cant).setText("2,50")
    qt.processEvents()

    renglones = controller.obtener_renglones()

    assert renglones[0].cantidad == 2.50, \
        "\"2,50\" son dos y media, no un error: dio {}".format(
            renglones[0].cantidad)
    controller.view.Cerrar()


def test_el_total_se_ve_como_importe_y_no_como_numero_crudo(qt, base):
    """El total es lo unico de la pantalla que no se puede leer de un vistazo.

    Con dos renglones de 150 y 50 a 100 el SubTotal de cada uno sale
    "15.000,00" y "5.000,00", y el total de abajo decia "20000.00". El
    numero estaba bien: `calcular_totales` trata el precio unitario como
    precio final con el IVA adentro, asi que sumar los SubTotal es lo correcto.

    Lo que faltaba era el separador de miles. Un numero de cinco digitos sin
    puntos se lee como un bloque: no se ve de un vistazo que son veinte mil, y
    en un mostrador con cola ese es el numero que hay que leer en voz alta.
    """
    from libs import stock

    # El articulo 1 del seed vale 100, asi que 150 + 50 dan 20.000. El numero
    # importa poco: lo que se comprueba es que salga con punto de miles.
    stock.registra_inventario_inicial(1, 160)

    controller = _abrir(qt, base)
    _agregar(controller, 1, 150)
    _agregar(controller, 1, 50)
    qt.processEvents()

    texto = controller.view.textTotal.text()
    assert texto == "20.000,00", \
        "el total tiene que verse 20.000,00, con punto de miles y coma " \
        "decimal como los SubTotal. Sale '{}'".format(texto)
    controller.view.Cerrar()


def test_el_total_no_se_ve_apagado(qt, base):
    """Un campo deshabilitado se dibuja atenuado, y este es el numero mas
    importante de la pantalla.

    `EntradaTexto(enabled=False)` llama `setEnabled(False)`, asi que Qt lo
    pinta con la paleta de inactivo: el total salia gris,chiquito, como un
    campo de formulario que no se puede tocar, al lado de una botonera con
    "Emitir factura".

    Ademas un campo deshabilitado no deja seleccionar el texto, y un operador
    que necesita pasarlo por whatsapp no lo puede copiar.

    Se usa solo lectura: sigue sin poder escribirse, pero se ve normal y se
    puede seleccionar.
    """
    controller = _abrir(qt, base)

    total = controller.view.textTotal

    assert total.isEnabled(), \
        "el campo del total esta deshabilitado, y por eso se dibuja atenuado"
    assert total.isReadOnly(), \
        "tiene que ser solo lectura: si se puede escribir, el operador puede " \
        "cambiar a mano el total de la venta"
    controller.view.Cerrar()


def test_el_total_esta_alineado_a_la_derecha(qt, base):
    """Los importes se alinean a la derecha para que las cifras encajen.

    A la izquierda, un total de cinco digitos queda pegado al rótulo y uno de
    siete se separa: no hay forma de comparar los digitos de uno con otro,
    que es para lo que sirve una columna de importes.
    """
    from PyQt5.QtCore import Qt

    controller = _abrir(qt, base)

    alineacion = controller.view.textTotal.alignment()
    assert alineacion & Qt.AlignRight, \
        "el total tiene que estar alineado a la derecha. Alineacion: {}".format(
            alineacion)

    assert not alineacion & Qt.AlignHCenter, \
        "centrado no sirve: el ancho del campo no cambia con el numero"
    controller.view.Cerrar()


def test_el_total_arranca_en_cero_con_formato(qt, base):
    """El 0 inicial tiene que verse como los demas importes.

    Si el estado vacio dice "0.00" y recien cargado dice "250.100,00", el
    cambio de formato se nota cada vez que se borra un renglon.
    """
    controller = _abrir(qt, base)

    assert controller.view.textTotal.text() == "0,00", \
        "el total vacio tiene que verse 0,00. Sale '{}'".format(
            controller.view.textTotal.text())
    controller.view.Cerrar()


def test_editar_la_cantidad_actualiza_el_subtotal(qt, base):
    """Si el renglon se edita, el SubTotal de esa fila tambien cambia.

    Va junto al anterior porque es el mismo handler, y dejarlo a medias
    seria una incoherencia visible: la cantidad en 2, el subtotal todavia
    calculado para 6, y el total de abajo como si nada.

    Y compara el TEXTO LITERAL, no el numero que hay adentro. Un aserto que
    parsea "150000.0" y "150.000,00" y da 150000 en los dos casos no ve un
    problema de presentacion, y esta pantalla es de mirar. Ver
    `test_el_subtotal_editado_sale_formateado`.
    """
    from libs import stock

    stock.registra_inventario_inicial(1, 10)

    controller = _abrir(qt, base)
    _agregar(controller, 1, 2)

    grilla = controller.view.gridVenta
    col_cant = _columna_de(grilla, "Cant.")
    col_sub = _columna_de(grilla, "SubTotal")

    assert grilla.item(0, col_sub).text() == "200,00", \
        "2 unidades a 100: el subtotal tiene que verse 200,00 y no 200 ni " \
        "200,0. Sale '{}'".format(grilla.item(0, col_sub).text())

    grilla.item(0, col_cant).setText("4")
    qt.processEvents()

    assert grilla.item(0, col_sub).text() == "400,00", \
        "con 4 unidades a 100 tiene que verse 400,00. Sale '{}'".format(
            grilla.item(0, col_sub).text())
    controller.view.Cerrar()


def test_el_subtotal_editado_sale_formateado(qt, base):
    """Editar un renglon no puede dejarlo con el numero crudo.

    Es un bug que se vio mirando la pantalla, no leyendo el codigo: la celda
    Unitario decia "1.500,00" y el SubTotal de al lado "150000.0", en la misma
    fila. La celda SubTotal recien cargada si sale formateada; la que se
    recalcula al editar, no.

    La causa es que `Grilla.ModificaItem` formatea SOLO si el valor es numero:
    con un string lo escribe tal cual. Asi que el arreglo es pasar el Decimal y
    no `str(Decimal)`.
    """
    from libs import stock

    stock.registra_inventario_inicial(1, 10)

    controller = _abrir(qt, base)
    _agregar(controller, 1, 2)

    grilla = controller.view.gridVenta
    col_cant = _columna_de(grilla, "Cant.")
    col_sub = _columna_de(grilla, "SubTotal")
    col_unit = _columna_de(grilla, "Unitario")

    antes = grilla.item(0, col_sub).text()
    assert antes == "200,00", \
        "recien cargado tiene que salir formateado. Sale '{}'".format(antes)

    # Editar es lo que rompe el formato si el handler pasa un string.
    # La cantidad tiene que ser DISTINTA de la que ya estaba: Qt no avisa
    # `cellChanged` cuando el texto no cambia, asi que recargar el mismo
    # numero no recorre el handler y este test pasaria sin probar nada.
    grilla.item(0, col_cant).setText("100")
    qt.processEvents()

    despues = grilla.item(0, col_sub).text()
    assert despues == "10.000,00", \
        "con 100 unidades a 100 el subtotal tiene que verse 10.000,00, con " \
        "punto de miles y coma como el Unitario ({}), y no '100000.0'. " \
        "Sale '{}'".format(grilla.item(0, col_unit).text(), despues)
    controller.view.Cerrar()


def test_la_columna_de_stock_no_muestra_decimales_de_morej(qt, base):
    """El stock se muestra como cantidad entera, no como 85.0000.

    `stock_de` devuelve un Decimal con CUATRO_DECIMALES, y `str` de eso es
    "85.0000". El resto de las columnas de la fila se leen con separador de
    miles y coma, y la de stock era la unica con cuatro decimales y punto: en
    una pantalla que se mira de un vistazo, un numero con otra forma se lee
    como dato de otra cosa.
    """
    from libs import stock

    stock.registra_inventario_inicial(1, 85)

    controller = _abrir(qt, base)
    _agregar(controller, 1, 1)

    grilla = controller.view.gridVenta
    col_stock = _columna_de(grilla, "Stock")

    texto = grilla.item(0, col_stock).text()
    assert texto == "85", \
        "el stock tiene que verse 85, sin decimales. Sale '{}'".format(texto)
    controller.view.Cerrar()