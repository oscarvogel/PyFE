"""Los dialogos tienen que abrirse con el tamano que declaran.

Que esta comprobando
--------------------
Que un dialogo chico no se infle. El piso de tamano de `Formulario` (620x420
sin grilla) existe porque las 40 pantallas del menu se recortaban, y se deja
como esta para ellas. El problema es que tambien se aplicaba a los dialogos
chicos: el de "Cantidad y precio" pide 420x160 y se abria de 620x420, casi el
triple de alto para dos campos.

Y que el titulo sea una linea. `EtiquetaTitulo` es un QLabel, cuya politica
vertical por omision es Expanding: dentro de un QVBoxLayout se come todo el
sobrante. Medido, ocupaba 307 px de alto para unos 20 px de texto, y el
nombre del producto quedaba flotando en el medio de la ventana.

Que NO comprueba
---------------
Que el contenido no se corte. Eso lo mide `tools/medir_ventanas.py` sobre las
pantallas del menu, y aca lo que se mira es el otro lado: que la ventana no
sea mas grande de lo que el dialogo pidio.

Por que un tamano, y no "que se vea bien"
-----------------------------------------
Porque "se ve bien" no se puede escribir como asercion, y "560x340" si. Si un
dia hay que agrandar un dialogo, el test avisa y se decide a mano.
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


class _TipoIva(object):
    iva = "21"


class _Articulo(object):
    idarticulo = 1
    nombre = "PRODUCTOS"
    preciopub = "1"
    tipoiva = _TipoIva()


def _abrir(qt, dialogo):
    dialogo.show()
    qt.processEvents()
    return dialogo


def test_el_dialogo_de_cantidad_y_precio_no_se_infla(qt):
    """El de la captura: 420x160 con dos campos.

    Es el caso mas claro porque la diferencia se ve a simple vista: casi el
    triple de alto para lo mismo, con el titulo en el medio de la ventana.
    """
    from vistas.VentaSimple import VentaSimpleCantidadPrecioDialog

    d = _abrir(qt, VentaSimpleCantidadPrecioDialog(_Articulo(), 1, 1))
    try:
        assert (d.width(), d.height()) == (420, 160), \
            "el dialogo pide 420x160 y abrio de {}x{}. Con el piso de " \
            "Formulario son {} px de alto de mas para dos campos.".format(
                d.width(), d.height(), d.height() - 160)
    finally:
        d.close()


def test_ningun_dialogo_chico_supera_el_piso_por_defecto(qt):
    """Todos los dialogos que declaran un tamano, lo reciben.

    Se arma la lista con el tamano que cada vista declara. Si uno se infla, el
    aserto dice cual y cuanto, que es la informacion que hace falta para
    arreglarlo.
    """
    from vistas import Clientes
    from vistas.VentaSimple import (VentaSimpleAltaArticuloDialog,
                                    VentaSimpleAltaClienteDialog,
                                    VentaSimpleCantidadPrecioDialog)

    casos = [
        ("Cantidad y precio",
         lambda: VentaSimpleCantidadPrecioDialog(_Articulo(), 1, 1),
         420, 160),
        ("Agregar cliente", lambda: VentaSimpleAltaClienteDialog("x"),
         520, 220),
        ("Agregar articulo", lambda: VentaSimpleAltaArticuloDialog("x"),
         520, 220),
    ]

    for etiqueta, construir, ancho, alto in casos:
        d = _abrir(qt, construir())
        try:
            assert (d.width(), d.height()) == (ancho, alto), \
                "{} pide {}x{} y abrio de {}x{}".format(
                    etiqueta, ancho, alto, d.width(), d.height())
        finally:
            d.close()

    # La ficha de cliente tambien es chica y declaraba 500x350.
    d = _abrir(qt, Clientes.FichaClienteView())
    try:
        assert d.width() == 500, \
            "la ficha de cliente pide 500 de ancho y abrio de {}".format(
                d.width())
    finally:
        d.close()


def test_el_titulo_de_un_dialogo_ocupa_una_linea(qt):
    """El nombre del producto no puede flotar en el medio de la ventana.

    Este es el otro mitad del problema. Aunque el dialogo ya no se infla, un
    QLabel con politica Expanding dentro de un QVBoxLayout se queda con todo
    el sobrante vertical, y con 307 px de alto para una linea de texto el
    titulo queda flotando entre el borde superior y los campos.
    """
    from vistas.VentaSimple import VentaSimpleCantidadPrecioDialog

    d = _abrir(qt, VentaSimpleCantidadPrecioDialog(_Articulo(), 1, 1))
    try:
        alto = d.lblTitulo.height()
        assert alto <= 40, \
            "el titulo mide {} px de alto: esta tomando el sobrante del " \
            "layout en vez de ocupar su linea".format(alto)
    finally:
        d.close()


def test_el_titulo_no_crece_en_ningun_dialogo(qt):
    """La regla es general, no del dialogo de cantidad y precio.

    `EtiquetaTitulo` se usa en casi todas las pantallas. Si el problema estaba
    en la clase y no en el dialogo, el test tiene que mirar la clase: uno que
    solo mirara una pantalla dejaria pasar el mismo bug en las otras treinta.
    """
    from PyQt5.QtWidgets import QLabel, QSizePolicy

    from libs.Etiquetas import EtiquetaTitulo

    titulo = EtiquetaTitulo(texto="PRODUCTOS")
    assert isinstance(titulo, QLabel)
    assert titulo.sizePolicy().verticalPolicy() == QSizePolicy.Fixed, \
        "EtiquetaTitulo tiene politica vertical Expanding, asi que crece con " \
        "el sobrante del layout en cualquier pantalla que la use"


def test_las_40_pantallas_del_menu_no_cambiaron_de_tamano(qt):
    """El piso grande sigue intacto para las pantallas con grilla.

    `declara_tamano` solo baja el piso de los dialogos SIN grilla. Las 40
    pantallas del menu tienen grilla y siguen usando el piso de 900x560, que
    es el que las salve de recortarse. Si esto falla, algo bajo el piso a una
    pantalla que no debía.
    """
    from libs.Formulario import Formulario

    ventana = Formulario()
    try:
        assert ventana._piso_de_tamano() == (620, 420), \
            "el piso por omision cambio: {}".format(ventana._piso_de_tamano())

        ventana.declara_tamano(500, 300)
        assert ventana._piso_de_tamano() == (500, 300), \
            "declara_tamano no bajo el piso: {}".format(
                ventana._piso_de_tamano())
    finally:
        ventana.close()