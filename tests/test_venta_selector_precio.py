"""El selector de producto: mas ancho, y con el precio al publico a la vista.

Que se pidio
------------
De las dos capturas del reporte:

1. El dialogo tiene que ser **mas ancho**. La captura lo muestra ya estirado
   a mano (~950 px) con la fila de 110 caracteres que el operador estaba
   tratando de leer: con el `resize(560, 420)` de antes, a 560 px entraba la
   mitad del nombre y habia que arrastrar la ventana en cada apertura, porque
   `resize` corre en cada construccion y no recuerda nada.

2. La fila tiene que mostrar el **precio al publico**. El operador con "acc"
   escrito esta eligiendo entre 4 access points que se diferencian por el
   modelo, y no puede compararlos: elige a ciegas y se enter del precio con el
   renglon ya cargado.

Por que una grilla y no un string pegado al final
-------------------------------------------------
El precio tiene que estar **alineado**. Con los importes pegados al codigo de
barras hay que contarlos a ojo para compararlos, que es justo lo que el
operador esta haciendo. Por eso la lista paso de `QListWidget` (un string por
item) a `QTableWidget` con columnas.
"""

import os
import sys
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402


# El mas largo del reporte, para que el ancho tenga que crecer con el.
LARGO = ("ACCESS POINT EXTENSOR WIFI TP-LINK RE200 AC750 DUAL BAND "
         "2.4GHZ 300MBPS / 5GHZ 450MBPS")


class _Articulo(object):
    def __init__(self, idarticulo, nombre, codbarra="", preciopub=Decimal("14198.80")):
        self.idarticulo = idarticulo
        self.nombre = nombre
        self.codbarra = codbarra
        self.preciopub = preciopub
        self.tipoiva = type("T", (), {"iva": Decimal("21")})()


CATALOGO = [
    _Articulo(4, LARGO, "104872"),
    _Articulo(6, "ACCESS POINT UNIFI U7-PRO UBIQUITI", "111178"),
    _Articulo(543, "POE INVERTOR 48VDC 30W UBIQUITI UACC-POE++-2.5G", "111203",
              Decimal("7890.50")),
]


@pytest.fixture
def qt():
    from PyQt5.QtWidgets import QApplication
    return QApplication.instance() or QApplication(sys.argv)


def _dialogo(qt, catalogo=None, busqueda=""):
    from vistas.VentaSimple import VentaSimpleSeleccionArticuloDialog

    catalogo = catalogo if catalogo is not None else CATALOGO

    def _buscar(texto):
        texto = (texto or "").strip().lower()
        if not texto:
            return list(catalogo), len(catalogo)
        hallados = [a for a in catalogo
                    if texto in a.nombre.lower() or texto in str(a.codbarra or "").lower()]
        return hallados, len(hallados)

    dialogo = VentaSimpleSeleccionArticuloDialog(_buscar, busqueda=busqueda)
    # Se muestra porque la columna Detalle es `Stretch`: Qt reparte el ancho
    # sobrante recien cuando arma el layout, que es cuando la ventana aparece.
    # Sin `show()`, `columnWidth()` devuelve lo que quedo del default y el
    # test mide un widget que nunca vio el operador.
    dialogo.show()
    qt.processEvents()
    return dialogo


# -- El precio esta a la vista ------------------------------------------------

def test_la_fila_muestra_el_precio_al_publico(qt):
    """El pedido: ver el precio antes de elegir, no despues de elegir.

    Sin esto el operador elige entre 4 productos parecidos sin poder
    compararlos, y se entera del precio con el renglon ya cargado.
    """
    from vistas.VentaSimple import COL_PRECIO

    dialogo = _dialogo(qt)
    celda = dialogo.listaArticulos.item(0, COL_PRECIO)
    assert celda is not None, "la fila no tiene columna de precio"
    assert celda.text() == "14.198,80", (
        "el precio no se muestra como importe: {!r}".format(celda.text()))
    dialogo.close()


def test_el_precio_de_cada_articulo_es_el_suyo(qt):
    """Cada fila con su precio: si todos salieran iguales, el dato no sirve."""
    from vistas.VentaSimple import COL_PRECIO, COL_DETALLE

    dialogo = _dialogo(qt)
    precios = {}
    for fila in range(dialogo.listaArticulos.rowCount()):
        nombre = dialogo.listaArticulos.item(fila, COL_DETALLE).text()
        precios[nombre] = dialogo.listaArticulos.item(fila, COL_PRECIO).text()

    assert precios[LARGO] == "14.198,80"
    assert precios[CATALOGO[2].nombre] == "7.890,50"
    dialogo.close()


def test_el_precio_derecho_sobrevive_a_un_articulo_sin_precio(qt):
    """Un articulo sin precio no rompe la lista.

    `preciopub` tiene default 1 pero en una base vieja puede venir NULL, y
    `_formato_importe(None)` devuelve el TEXTO "None": se veria un producto
    que cuesta "None", que parece un dato roto y no un dato que falta.
    """
    from vistas.VentaSimple import COL_PRECIO

    catalogo = [_Articulo(1, "SIN PRECIO CARGADO", "x", preciopub=None),
                _Articulo(2, "CON PRECIO", "y")]
    dialogo = _dialogo(qt, catalogo)

    assert dialogo.listaArticulos.rowCount() == 2, (
        "un articulo sin precio desaparecio de la lista")
    assert dialogo.listaArticulos.item(0, COL_PRECIO).text() == "", (
        "un articulo sin precio muestra {!r}".format(
            dialogo.listaArticulos.item(0, COL_PRECIO).text()))
    assert dialogo.listaArticulos.item(1, COL_PRECIO).text() == "14.198,80"
    dialogo.close()


def test_las_columnas_son_codigo_detalle_barra_y_precio(qt):
    """El orden de las columnas, que es lo que el operador lee de izquierda
    a derecha: el nombre primero, que es lo que distingue un producto de
    otro, y el precio al final."""
    from vistas.VentaSimple import (COL_BARRA, COL_CODIGO, COL_DETALLE,
                                    COL_PRECIO)

    dialogo = _dialogo(qt)
    assert dialogo.listaArticulos.item(0, COL_CODIGO).text() == "4"
    assert dialogo.listaArticulos.item(0, COL_DETALLE).text() == LARGO
    assert dialogo.listaArticulos.item(0, COL_BARRA).text() == "104872"
    assert dialogo.listaArticulos.item(0, COL_PRECIO).text() == "14.198,80"
    dialogo.close()


def test_la_grilla_del_selector_no_se_edita(qt):
    """Si se pudiera escribir en una celda, el articulo se llevaria con el
    precio que el operador invente de tipear, sin ningun aviso. En una venta
    eso es cobrar cualquier cosa."""
    from PyQt5.QtWidgets import QAbstractItemView

    dialogo = _dialogo(qt)
    assert dialogo.listaArticulos.editTriggers() == QAbstractItemView.NoEditTriggers
    dialogo.close()


def test_el_precio_esta_alineado_a_la_derecha(qt):
    """Alineado, que es lo que hace comparables dos precios.

    Es la diferencia entre "ver el precio" y "poder comparar precios", que es
    lo que el operador hace cuando tiene 4 productos parecidos delante.
    """
    from PyQt5.QtCore import Qt
    from vistas.VentaSimple import COL_PRECIO

    dialogo = _dialogo(qt)
    alineacion = dialogo.listaArticulos.item(0, COL_PRECIO).textAlignment()
    assert alineacion & Qt.AlignRight, (
        "los precios no estan alineados a la derecha: comparar dos importes "
        "pegados al codigo de barras es contar de memoria")
    dialogo.close()


def _ancho_medido(dialogo, articulos):
    """El ancho que el codigo calcula para un catalogo dado.

    Se mide sin aplicar el piso de la ventana, porque en `offscreen` la pantalla
    mide 800 px y el piso tapa cualquier medicion: el ancho real del selector se
    veria siempre igual.
    """
    dialogo.articulos = articulos
    return dialogo._ancho_para_contenido()


# -- El ancho ----------------------------------------------------------------

def test_el_dialogo_es_mas_ancho_que_los_560_px_de_antes(qt):
    """El pedido crudo: mas ancho que antes.

    Con 560 px entraba la mitad del nombre y el operador terminaba estirando la
    ventana a mano en cada apertura.
    """
    dialogo = _dialogo(qt)
    assert dialogo.width() > 560, (
        "el selector quedo en {} px, el mismo ancho de antes".format(
            dialogo.width()))
    dialogo.close()


def test_el_ancho_se_mide_por_el_nombre_mas_largo(qt):
    """El ancho sale de medir el texto, no de un numero inventado.

    La comparacion es entre dos catalogos que solo se diferencian en la
    longitud del nombre: si el ancho fuera un 900 fijo, los dos darian lo mismo
    y este test pasaria sin estar probando nada.
    """
    from PyQt5.QtGui import QFontMetrics

    dialogo = _dialogo(qt)
    metrics = QFontMetrics(dialogo.listaArticulos.font())
    corto = _ancho_medido(dialogo, [_Articulo(1, "X" * 20, "c")])
    largo = _ancho_medido(dialogo, [_Articulo(1, "X" * 190, "l")])

    assert metrics.horizontalAdvance("X" * 190) > metrics.horizontalAdvance("X" * 20)
    assert largo > corto, (
        "un nombre de 190 caracteres midio {} y uno de 20 midio {}: el ancho no "
        "sale del texto".format(largo, corto))
    assert largo >= metrics.horizontalAdvance("X" * 190), (
        "el ancho medido ({}) no alcanza para el nombre mas largo".format(largo))
    dialogo.close()


def test_el_ancho_alcanza_para_el_nombre_mas_largo(qt):
    """Cada columna entra entera, sin puntos suspensivos ni scroll.

    Se compara la columna contra el texto medido con `QFontMetrics` desde el
    test, no contra el metodo del codigo: si el test se comprobara a si mismo,
    pasaria aunque la medicion estuviera rota.
    """
    from PyQt5.QtGui import QFontMetrics
    from vistas.VentaSimple import CABECERAS_ARTICULOS

    dialogo = _dialogo(qt)
    metrics = QFontMetrics(dialogo.listaArticulos.font())

    for columna, titulo in enumerate(CABECERAS_ARTICULOS):
        mayor = metrics.horizontalAdvance(titulo)
        for articulo in CATALOGO:
            ancho_texto = metrics.horizontalAdvance(
                dialogo._celda_texto(articulo, columna))
            if ancho_texto > mayor:
                mayor = ancho_texto
        assert dialogo.listaArticulos.columnWidth(columna) >= mayor, (
            "la columna {} quedo en {} px y su texto pide {}".format(
                columna, dialogo.listaArticulos.columnWidth(columna), mayor))

    dialogo.close()


def test_el_nombre_largo_del_reporte_entra_entero(qt):
    """La fila del reporte, medida de punta a punta.

    110 caracteres a 560 px no entran ni por lejos: ahi esta el pedido.
    """
    from PyQt5.QtGui import QFontMetrics
    from vistas.VentaSimple import COL_DETALLE

    dialogo = _dialogo(qt)
    metrics = QFontMetrics(dialogo.listaArticulos.font())

    assert dialogo.listaArticulos.columnWidth(COL_DETALLE) >= \
        metrics.horizontalAdvance(LARGO), (
        "la columna Detalle quedo en {} px y el nombre del reporte pide {}".format(
            dialogo.listaArticulos.columnWidth(COL_DETALLE),
            metrics.horizontalAdvance(LARGO)))
    dialogo.close()


def test_el_ancho_no_pasa_de_la_pantalla(qt):
    """Un ancho que no entra en la pantalla no es "mas ancho", es inusable.

    Con un nombre de 400 caracteres, que pediria 6000 px, la ventana tiene que
    quedar dentro de la pantalla. El tope lo pone `Formulario.ajusta_tamano`, no
    este dialogo, asi que se mide sobre la ventana ya mostrada.
    """
    from PyQt5.QtWidgets import QApplication

    dialogo = _dialogo(qt, [_Articulo(1, "X" * 400, "largo")])
    pantalla = QApplication.primaryScreen().availableGeometry().width()

    assert dialogo.width() <= pantalla, (
        "el selector mide {} px y la pantalla tiene {}".format(
            dialogo.width(), pantalla))
    assert dialogo.width() == int(pantalla * 0.92), (
        "con un nombre de 400 caracteres el tope de pantalla no se aplico: "
        "quedo en {}".format(dialogo.width()))
    dialogo.close()


def test_el_ancho_no_cambia_mientras_se_escribe(qt):
    """Se mide una vez, al abrir.

    Este test existio para verificar una cosa y encontro DOS motivos por los que
    la ventana se movia sola, y los dos estan en el layout, no en la medicion:

    1. La columna Detalle era `Stretch`, y Qt tomaba el ancho del contenido como
       minimo del layout: aparecia un nombre mas largo y empujaba la ventana.
    2. `lblCuenta` es un QLabel, y un QLabel toma el ancho de su texto como
       minimo. El mensaje "2 coincidencias. Elegi una con las flechas o el
       mouse." era mas largo que la ventana.

    Los dos hacen que "el ancho se mide una vez" sea falso mientras queden.
    """
    dialogo = _dialogo(qt)
    ancho_inicial = dialogo.width()

    for texto in ("access", "access point", "access point extensor wifi", ""):
        dialogo.txtBuscar.setText(texto)
        qt.processEvents()
        assert dialogo.width() == ancho_inicial, (
            "el ancho cambio al escribir {!r}: {} -> {}".format(
                texto, ancho_inicial, dialogo.width()))

    dialogo.close()


# -- Elegir sigue funcionando con columnas -----------------------------------

def test_el_doble_clique_elige_el_articulo_de_la_fila(qt):
    """Con columnas, el doble clic tiene que elegir el ARTICULO, no la celda.

    Si eligiera la celda, `currentRow()` daria -1 y Aceptar no cerraria: el
    operador hacia doble clic y no pasaba nada.
    """
    from PyQt5.QtWidgets import QDialog
    from vistas.VentaSimple import COL_DETALLE

    dialogo = _dialogo(qt, busqueda="unifi")
    item = dialogo.listaArticulos.item(0, COL_DETALLE)
    dialogo.listaArticulos.setCurrentCell(0, COL_DETALLE)
    dialogo.listaArticulos.itemDoubleClicked.emit(item)
    qt.processEvents()

    assert dialogo.result() == QDialog.Accepted
    assert dialogo.articulo.idarticulo == 6
    dialogo.close()


def test_sin_eleccion_enter_no_cierra(qt):
    """La regla de `docs/SELECCION-PRODUCTO.md` sigue viva con columnas:
    con mas de una coincidencia no se elige nada solo."""
    from PyQt5.QtCore import Qt
    from PyQt5.QtTest import QTest
    from PyQt5.QtWidgets import QDialog

    dialogo = _dialogo(qt)
    dialogo.show()
    dialogo.txtBuscar.setText("access point")
    dialogo.txtBuscar.setFocus()
    qt.processEvents()

    assert dialogo.listaArticulos.rowCount() == 2
    assert dialogo.listaArticulos.currentRow() == -1, (
        "con 2 coincidencias quedo algo marcado solo")

    QTest.keyClick(dialogo.txtBuscar, Qt.Key_Return)
    qt.processEvents()

    assert dialogo.result() != QDialog.Accepted
    assert dialogo.articulo is None
    dialogo.close()