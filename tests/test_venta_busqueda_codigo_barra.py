"""En la venta se tiene que poder buscar por codigo de barras.

Que estaba pasando
------------------
El campo de producto de la venta promete, en su placeholder, "Codigo, nombre
o codigo de barras". Antes de esto searching solo por nombre. El codigo de
barras COMPLETO ya entraba, porque `_articulo_exacto` compara con igualdad; el
PARCIAL no, y el parcial es el caso del dia a dia: con un lector en la mano se
teclean los primeros digitos, no los 13.

Y el parcial no era solo "no encuentra". Era peor:

    agregar_articulo()
      -> _articulo_es_ambiguo("10487")   -> 0 coincidencias -> False
      -> buscar_articulo("10487")        -> None
      -> "Producto no encontrado. Desea agregarlo?"  -> Crear producto

O sea: el operador teclea los primeros 6 digitos de un articulo que YA
EXISTE y el sistema le ofrece darlo de alta, duplicandolo en el catalogo con
otro codigo de barras. Eso es dano de datos, no una molestia, y por eso este
archivo no se limita a probar que la busqueda ahora encuentra.

Que se verifica en las dos direcciones
-------------------------------------
Contra el codigo viejo estos tests tienen que fallar con el sintoma, no con un
error: `AttributeError` por un metodo que todavia no existe dice "me falta un
metodo", no "el operador estaba por duplicar un producto". Los dos que mas
importan son `test_el_barcode_parcial_no_ofrece_crear` y
`test_una_coincidencia_de_barcode_no_abre_el_catalogo`: los dos caroten el
"Crear producto", que es el dano.
"""

import os
import sys
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402


# Los de la captura del reporte, con el barcode que se escribio a mano.
ACCESS_RE200 = "ACCESS POINT EXTENSOR WIFI TP-LINK RE200 AC750 DUAL BAND 2.4GHZ 300MBPS / 5GHZ 450MBPS"
ACCESS_UNIFI = "ACCESS POINT UNIFI U7-PRO UBIQUITI"
POE_INVECTOR = "POE INVERTOR 48VDC 30W UBIQUITI UACC-POE++-2.5G"
WHEY = "WHEY CUTTER 1080G PROTE+QUEMADOR SPX VAINILLA/FRUTILLA BOLSA"

# El barcode que share el prefijo: los tres arrancan con 11. Es el caso que
# obliga a elegir, y por lo tanto el que tiene que abrir el catalogo.
CATALOGO = [
    {"idarticulo": 4, "nombre": ACCESS_RE200, "codbarra": "104872"},
    {"idarticulo": 5, "nombre": "EXTENSOR WIFI TP-LINK TL-WA850RE 300MBPS",
     "codbarra": "102505"},
    {"idarticulo": 6, "nombre": ACCESS_UNIFI, "codbarra": "111178"},
    {"idarticulo": 543, "nombre": POE_INVECTOR, "codbarra": "111203"},
    {"idarticulo": 15, "nombre": WHEY, "codbarra": "INTWHEYCUTTER1"},
]


@pytest.fixture
def qt():
    from PyQt5.QtWidgets import QApplication
    return QApplication.instance() or QApplication(sys.argv)


@pytest.fixture
def articulos():
    """El catalogo real en memoria, para probar la consulta y no un doble.

    Se usa una base de verdad a proposito: el bug era de la CONSULTA (buscaba
    solo por nombre) y del CRITERIO (los dos caminos no coincidian). Con una
    lista de objetos en Python y un `_coincidencias_articulo` de mentira, el
    test pasa en verde contra el codigo viejo y no verifica nada.

    Los modelos se restauran al final: si se olvidara, el resto de la suite
    pasaria a leer de una base que no es la de la app.
    """
    from peewee import SqliteDatabase

    from modelos.Articulos import Articulo
    from modelos.Formaspago import Formapago
    from modelos.Grupos import Grupo
    from modelos.Proveedores import Proveedor
    from modelos.Tipoiva import Tipoiva
    from modelos.Unidades import Unidad

    # Formapago esta porque `VentaSimpleController()` arma la vista entera, y
    # la vista tiene un ComboFormapago: sin esa tabla el controlador ni
    # siquiera llega a existir y el test muere con "no such table" en vez de
    # fallar por lo que esta probando.
    modelos = (Unidad, Grupo, Proveedor, Tipoiva, Formapago, Articulo)
    anteriores = [m._meta.database for m in modelos]

    memoria = SqliteDatabase(":memory:")
    for modelo in modelos:
        modelo.bind(memoria)
    memoria.connect()
    for modelo in modelos:
        modelo.create_table(safe=True)

    # Sin esta fila, `articulo.tipoiva` es None y `_agregar_este_articulo`
    # muere en `Decimal(str(articulo.tipoiva.iva))`. Y como `agregar_articulo`
    # esta envuelto en `inicializar_y_capturar_excepciones`, la excepcion se
    # traga sola y el renglon no aparece: el test falla con "0 lineas" y no
    # dice nada de los barcodes. Un fallo sin motivo no dice donde mirar.
    Tipoiva.insert(codigo="01", descrip="IVA 21", iva=Decimal("21")).execute()

    for fila in CATALOGO:
        Articulo.create(
            idarticulo=fila["idarticulo"],
            nombre=fila["nombre"],
            nombreticket=fila["nombre"][:30],
            codbarra=fila["codbarra"],
            preciopub=Decimal("14198.80"),
            costo=Decimal("10142"),
            incre1=Decimal("40"),
        )
    assert Articulo.select().count() == len(CATALOGO)

    yield Articulo

    for modelo, anterior in zip(modelos, anteriores):
        modelo.bind(anterior)


@pytest.fixture
def controller(qt, articulos, monkeypatch):
    monkeypatch.setattr(sys, "argv", [sys.argv[0]])

    from controladores.VentaSimple import VentaSimpleController

    c = VentaSimpleController()
    c.view.show()
    qt.processEvents()
    yield c
    c.view.Cerrar()


# -- La busqueda encuentra el codigo de barras, tambien parcial --------------

def test_el_codigo_de_barras_completo_encuentra(articulos, controller):
    """Lo que ya andaba, para no romperlo: el completo por igualdad."""
    from modelos.Articulos import Articulo

    assert controller.buscar_articulo("104872").idarticulo == 4


def test_un_fragmento_del_codigo_de_barras_encuentra(articulos, controller):
    """El caso del lector: los primeros digitos, no el codigo entero.

    Este es el test central del issue. Contra el codigo viejo devuelve None.
    """
    from modelos.Articulos import Articulo

    articulo = controller.buscar_articulo("1048")
    assert articulo is not None, (
        "un fragmento del codigo de barras no encontro nada")
    assert articulo.idarticulo == 4


def test_por_nombre_sigue_andando(articulos, controller):
    """Lo de antes: por nombre, con y sin tilde."""
    from modelos.Articulos import Articulo

    articulo = controller.buscar_articulo("unifi")
    assert articulo is not None
    assert articulo.idarticulo == 6


def test_por_nombre_con_tilde_ysin_tilde(articulos, controller):
    """La normalizacion de `contiene` sigue entrando por el barcode tambien."""
    from modelos.Articulos import Articulo

    # "RED EXTENSOR" encuentra a "EXTENSOR" sin tilde, y viceversa.
    assert controller.buscar_articulo("extensor") is not None


def test_lo_que_no_existe_no_encuentra_nada(articulos, controller):
    """El camino de "Crear producto" tiene que seguir existiendo.

    Esto es lo que separa el arreglo de tapar el sintoma: si un texto raro
    tambien encontrara algo, se habria cerrado el alta de productos nuevos, que
    es el camino que permite cargar algo sin salir de la pantalla.
    """
    from modelos.Articulos import Articulo

    assert controller.buscar_articulo("zzz-no-existe-zzz") is None


def test_el_fragmento_que_ambigua_abre_el_catalogo(articulos, controller):
    """Un prefijo compartido tiene que obligar a elegir, como dos nombres."""
    from modelos.Articulos import Articulo

    # "11" abre a los tres que arrancan con 11: 111178, 111203 y el que tiene
    # el 11 adelante en otro lado. Con 2 o mas no se elige nada solo.
    encontrados, total = controller._coincidencias_articulo("11")
    assert total > 1, (
        "un prefijo de barcode compartido tiene que dar mas de una "
        "coincidencia, dio {}".format(total))
    assert len(encontrados) >= 2


def test_los_barcodes_que_arrancan_con_lo_escrito_van_primero(articulos, controller):
    """Escaneado, el producto buscado va primero.

    Sin esto, teclear "1048" devuelve los parciales ordenados por nombre y el
    articulo escaneado aparece en algun lugar de la lista: con la compra en la
    mano, el operador tiene que leer 20 filas para encontrarlo.
    """
    from modelos.Articulos import Articulo

    encontrados, _total = controller._coincidencias_articulo("1048")
    # El `if not encontrados` va primero a proposito: sin el, contra el codigo
    # viejo `encontrados[0]` tira IndexError, y un IndexError no dice nada de
    # barcodes. Dice "no hay elemento 0", que es un error de este test, no el
    # sintoma que se esta buscando.
    assert encontrados, (
        "1048 no encontro ningun articulo: el codigo de barras no se busca")
    assert encontrados[0].idarticulo == 4, (
        "el barcode buscado quedo en la posicion {}, no primero".format(
            [a.idarticulo for a in encontrados]))


def test_los_ceros_a_la_izquierda_no_se_pierden(articulos, controller):
    """`codbarra` es texto: un barcode que empieza con 0 tiene que encontrable.

    Si `codbarra` fuera numerico, "011178" y "111178" serian lo mismo y con el
    lector en la mano se cargaria el articulo equivocado.
    """
    from modelos.Articulos import Articulo

    Articulo.create(
        idarticulo=99, nombre="TEST CON CERO", nombreticket="TEST CERO",
        codbarra="0111789", preciopub=Decimal("1"), costo=Decimal("1"))

    articulo = controller.buscar_articulo("0111789")
    assert articulo is not None, "el barcode con cero inicial no se encontro"
    assert articulo.idarticulo == 99


# -- El campo de producto: el barcode NO ofrece crear ------------------------
# Estos son los que importan. El dano no era no encontrar: era ofrecer dar de
# alta un producto que ya existia.

def test_el_barcode_parcial_no_ofrece_crear(articulos, controller, monkeypatch):
    """El sintoma del reporte, textual.

    Con un fragmento que SI existe, la pantalla tiene que agregar el producto,
    no preguntar si se lo crea. Antes caia en "Producto no encontrado. Desea
    agregarlo?", con el boton "Crear producto".
    """
    from modelos.Articulos import Articulo

    preguntas = []
    # `buscar_articulo` NO se parchea: es justamente el que tiene que resolver
    # el fragmento. `_articulo_es_ambiguo` ya dijo "no es ambiguo", y ahora
    # este devuelve el articulo en vez de None. Parchearlo hacia "no deberia
    # llamarse" estaria probando una regla que el codigo nunca tuvo.
    monkeypatch.setattr(controller, "confirmar_alta",
                        lambda titulo, mensaje, **kw: preguntas.append(mensaje) or False)
    monkeypatch.setattr(controller, "solicitar_alta_articulo",
                        lambda busqueda: pytest.fail(
                            "un barcode existente jamas debe crear un articulo nuevo"))
    monkeypatch.setattr(controller, "solicitar_cantidad_y_precio",
                        lambda a, c: (c, Decimal("14198.80")))

    controller.view.textArticulo.setText("1048")
    controller.agregar_articulo()
    controller.view.textArticulo.clear()

    assert not preguntas, (
        "un barcode parcial que existe ofrecio crear: {}".format(preguntas))
    assert controller.view.gridVenta.rowCount() == 1, (
        "el barcode parcial no se agrego como renglon: quedan {} lineas".format(
            controller.view.gridVenta.rowCount()))


def test_una_coincidencia_de_barcode_no_abre_el_catalogo(articulos, controller,
                                                        monkeypatch):
    """Con una sola coincidencia de barcode se agrega directo.

    Es lo que hay que dejar igual: si abriera el catalogo, habria un click de
    mas por producto escaneado, y el operador volveria al campo de texto.
    """
    from modelos.Articulos import Articulo

    monkeypatch.setattr(controller, "seleccionar_articulo",
                        lambda b: pytest.fail(
                            "una coincidencia unica de barcode no deberia "
                            "abrir el catalogo"))
    monkeypatch.setattr(controller, "confirmar_alta",
                        lambda titulo, mensaje, **kw: pytest.fail(
                            "un barcode existente no debe entrar al camino de "
                            "DARLO DE ALTA: el mensaje fue {!r}".format(mensaje)))
    monkeypatch.setattr(controller, "solicitar_alta_articulo",
                        lambda busqueda: pytest.fail(
                            "un barcode existente jamas debe crear un articulo"))
    monkeypatch.setattr(controller, "solicitar_cantidad_y_precio",
                        lambda a, c: (c, Decimal("14198.80")))

    controller.view.textArticulo.setText("1048")
    controller.agregar_articulo()
    controller.view.textArticulo.clear()

    assert controller.view.gridVenta.rowCount() == 1


def test_el_texto_que_no_existe_sigue_ofreciendo_crear(articulos, controller,
                                                       monkeypatch):
    """El alta de productos nuevos no se toco."""
    preguntas = []
    monkeypatch.setattr(controller, "confirmar_alta",
                        lambda titulo, mensaje, **kw: preguntas.append(mensaje) or False)
    monkeypatch.setattr(controller, "solicitar_alta_articulo",
                        lambda busqueda: pytest.fail("no deberia crearse"))

    controller.view.textArticulo.setText("Producto que no existe")
    controller.agregar_articulo()
    controller.view.textArticulo.clear()

    assert len(preguntas) == 1
    assert "Producto no encontrado" in preguntas[0]