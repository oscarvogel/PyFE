"""El stock: lo que se descuenta, lo que entra, y lo que NO tiene que pasar.

Que esta comprobando
--------------------
Que el stock sea la suma de los movimientos, con el signo puesto por la
funcion y no por quien la llama. La razon de ser de este archivo es esa: la
logica de stock vive en libs/stock.py justamente para poder probarla sin
QApplication, sin ARCA y sin una factura emitida.

El caso que da nombre al modulo
-------------------------------
El remito descuenta, y la factura descuenta solo cuando no hay remito. Si eso
esta mal, una venta con remito y factura baja el stock dos veces, y el
inventario se come mercaderia que existe. No se ve en la pantalla: se ve
semanas despues, cuando el conteo no cierra y nadie sabe desde cuando.

El otro que suele olvidarse
--------------------------
Los servicios. El catalogo mezcla productos y cosas que no se inventan
("Mantenimiento de computadoras", "Servicios"), y si un servicio genera
movimientos, cada venta de un servicio descuenta un servicio.

Como esta armado
----------------
Base sqlite en memoria con los modelos atados a ella y devueltos a la del
sandbox al final. Sin esto los tests escriben en la base de trabajo: el
stock de la base de desarrollo bajaria con cada corrida y al dia siguiente
nadie sabria por que.
"""

import os
import sys
from datetime import date

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)


@pytest.fixture
def base():
    """Base propia con el catalogo minimo, y se devuelve al sandbox al final."""
    from peewee import SqliteDatabase

    from modelos.Articulos import Articulo
    from modelos.CabFacProv import CabFactProv
    from modelos.Cabfact import Cabfact
    from modelos.Cajeros import Cajero
    from modelos.CentroCostos import CentroCosto
    from modelos.Clientes import Cliente
    from modelos.DetFactProv import DetFactProv
    from modelos.Detfact import Detfact
    from modelos.Formaspago import Formapago
    from modelos.Grupos import Grupo
    from modelos.Impuestos import Impuesto
    from modelos.Localidades import Localidad
    from modelos.MovStock import MovStock
    from modelos.Proveedores import Proveedor
    from modelos.Remitos import DetalleRemito, Remito
    from modelos.Tipocomprobantes import TipoComprobante
    from modelos.Tipodoc import Tipodoc
    from modelos.Tipoiva import Tipoiva
    from modelos.Tiporesp import Tiporesp
    from modelos.Unidades import Unidad

    modelos = (Articulo, MovStock, Grupo, Proveedor, Tipoiva, Unidad, Impuesto,
               Cliente, Localidad, Tipodoc, Tiporesp, Formapago, TipoComprobante,
               Cajero, Cabfact, Detfact, Remito, DetalleRemito, CentroCosto,
               CabFactProv, DetFactProv)
    anteriores = [(m, m._meta.database) for m in modelos]

    memoria = SqliteDatabase(":memory:")
    for modelo in modelos:
        modelo.bind(memoria)
    memoria.connect()
    # create_tables ordena solo segun las dependencias, asi que el orden de
    # esta lista es el que le queda comodo a quien lee, no al motor.
    memoria.create_tables(modelos, safe=True)

    # La siembra va campo por campo a proposito: peewee pone los defaults en
    # Python y no en el CREATE TABLE, asi que una columna NOT NULL sin default
    # hay que.passarla sí o sí, y adivinarla tira un IntegrityError que dice
    # que faltan columnas de una tabla de maestro y no del stock.
    Tipoiva.insert_many([
        {"codigo": "01", "descrip": "IVA GENERAL", "iva": 21},
        {"codigo": "02", "descrip": "10.5", "iva": 10.5},
    ]).execute()
    TipoComprobante.insert_many([
        {"codigo": 6, "nombre": "FACTURA B", "abreviatura": "B", "lado": "D",
         "exporta": 0, "ultcomp": 0, "letra": "B"},
        {"codigo": 8, "nombre": "NOTA CREDITO B", "abreviatura": "NCB",
         "lado": "H", "exporta": 0, "ultcomp": 0, "letra": "B"},
        {"codigo": 92, "nombre": "Proforma", "abreviatura": "PRO", "lado": "",
         "exporta": 0, "ultcomp": 0, "letra": "X"},
    ]).execute()
    Formapago.insert_many([{"idformapago": 1, "detalle": "EFECTIVO"}]).execute()
    Impuesto.insert_many([{"idimpuesto": 1, "detalle": "SIN PERCEPCION"}]).execute()
    Grupo.insert_many([{"idgrupo": 1, "nombre": "VARIOS", "impuesto": 1}]).execute()
    Localidad.insert_many([{"idlocalidad": 1, "nombre": "x", "provincia": "x",
                            "nacion": "ARGENTINA"}]).execute()
    Tipodoc.insert_many([{"codigo": 0, "tipo": "2", "nombre": "DNI"}]).execute()
    Tiporesp.insert_many([{"idtiporesp": 1, "nombre": "CONSUMIDOR FINAL",
                           "factura": 6, "notacredito": 8, "notadebito": 7,
                           "condicion_iva_receptor_id": 5}]).execute()
    Unidad.insert_many([{"unidad": "UN", "descripcion": "UNIDAD"}]).execute()
    Proveedor.insert_many([{"idproveedor": 1, "nombre": "SIN PROVEEDOR",
                            "tiporesp": 1, "idlocalidad": 1}]).execute()
    Cajero.insert_many([{"idcajero": 1, "nombre": "CAJERO"}]).execute()
    CentroCosto.insert_many([{"idctrocosto": 1, "nombre": "GENERAL"}]).execute()
    Cliente.insert_many([{"idcliente": 1, "nombre": "CONSUMIDOR FINAL",
                          "domicilio": "S/N", "localidad": 1, "dni": 11111111,
                          "tipodocu": 0, "tiporesp": 1, "formapago": 1,
                          "percepcion": 1}]).execute()

    Articulo.insert_many([
        {"idarticulo": 1, "nombre": "GASOLINA", "controlastock": True,
         "stockminimo": 5, "preciopub": 100, "costo": 80, "unidad": "UN",
         "grupo": 1, "provppal": 1, "tipoiva": "01", "concepto": "1"},
        {"idarticulo": 2, "nombre": "MANTENIMIENTO", "controlastock": False,
         "stockminimo": 0, "preciopub": 5000, "costo": 0, "unidad": "UN",
         "grupo": 1, "provppal": 1, "tipoiva": "01", "concepto": "2"},
    ]).execute()

    assert Articulo.select().count() == 2, "no entraron los articulos"

    yield memoria

    memoria.close()
    for modelo, anterior in anteriores:
        modelo.bind(anterior)


# -- Lo basico ---------------------------------------------------------------

def test_el_stock_de_un_articulo_nuevo_es_cero(base):
    """Nada se descuenta solo por existir. Ni por vender, hasta que se venda."""
    from libs import stock

    assert stock.stock_de(1) == 0, \
        "un articulo sin movimientos deberia estar en cero, no en {}".format(
            stock.stock_de(1))


def test_una_venta_deja_el_stock_menor(base):
    """Lo que se vende sale. Este es el caso base, y es el que se rompe."""
    from libs import stock

    stock.registra_salida(1, 3)

    assert stock.stock_de(1) == -3, \
        "vender 3 deberia dejar -3, dejo {}".format(stock.stock_de(1))


def test_una_compra_suma_al_stock(base):
    from libs import stock

    stock.registra_salida(1, 3)
    stock.registra_entrada(1, 10)

    assert stock.stock_de(1) == 7


def test_el_inventario_inicial_deja_el_stock_en_lo_contado(base):
    """El stock arranca en el numero que conto el operador, no en cero."""
    from libs import stock

    stock.registra_inventario_inicial(1, 120, observacion="countado el lunes")

    assert stock.stock_de(1) == 120
    movimiento = stock.MovStock.get(stock.MovStock.idarticulo == 1)
    assert movimiento.origen == "INICIAL", \
        "un inventario inicial tiene que quedar marcado como tal, no como un " \
        "ajuste suelto: {}".format(movimiento.origen)


# -- El signo ----------------------------------------------------------------

def test_las_cantidades_con_comas_no_dejan_rastro_de_float(base):
    """0.1 + 0.2 tiene que dar 0.3, no 0.30000000000000004.

    SUM sobre DECIMAL devuelve float en sqlite. Sin el redondeo, un articulo
    que se vendio de a medias termina con un stock de 2.9999999999999996 y el
    reporte de faltantes lo marca como faltante cuando no lo es.
    """
    from libs import stock

    stock.registra_entrada(1, "0.1")
    stock.registra_entrada(1, "0.2")

    assert stock.stock_de(1) == stock.Decimal("0.3"), \
        "la suma de decimales quedo en {!r}".format(stock.stock_de(1))


def test_el_lado_credito_devuelve_la_mercaderia(base):
    """Una nota de credito repone lo que la facturaoriginal se llevo."""
    from libs import stock
    from modelos.Tipocomprobantes import TipoComprobante

    stock.registra_salida(1, 3)
    signo = stock.descuenta_lado(TipoComprobante.get_by_id(8).lado)
    stock.registra_entrada(1, 3 * signo)

    assert stock.stock_de(1) == 0, \
        "una nota de credito de 3 sobre una venta de 3 deberia dejar el stock " \
        "como estaba, quedo en {}".format(stock.stock_de(1))


def test_el_lado_de_factura_saca_mercaderia(base):
    from libs import stock
    from modelos.Tipocomprobantes import TipoComprobante

    assert stock.descuenta_lado(TipoComprobante.get_by_id(6).lado) == -1


def test_el_lado_vacio_no_dice_por_si_mismo_si_mueve_stock(base):
    """El proforma no tiene lado, y su tipo de comprobante no es el que decide.

    Un remito proforma SI mueve stock, asi que el que decide es el flujo que
    llama, no la tabla de tipos. Que 'lado' vacio devuelva None en vez de 0 o
    -1 es lo que evita que un remito termine descontando.
    """
    from libs import stock
    from modelos.Tipocomprobantes import TipoComprobante

    assert stock.descuenta_lado(TipoComprobante.get_by_id(92).lado) is None


# -- El caso caro ------------------------------------------------------------

def test_la_mercaderia_no_sale_dos_veces_con_remito_y_factura(base):
    """Remito y factura del mismo negocio: el stock baja una sola vez.

    El remito descuenta cuando sale la mercaderia. La factura llega
    despues, y si tambien descontara, este articulo habria perdido 5 de stock
    por una venta de 5. Es el error mas caro de esta feature y el mas
    silencioso: la pantalla de stock muestra un numero, y el numero esta mal
    sin ninguna senal.

    El `if` que evita el doble descuento esta en `aplica_factura`, no aca.
    Si estuviera en el test, el test probaria su propio if y no el codigo que
    corre la app: pasaria en verde aunque la app descontara dos veces.
    """
    from libs import stock
    from modelos.Cabfact import Cabfact
    from modelos.Remitos import Remito
    from modelos.Tipocomprobantes import TipoComprobante

    stock.registra_inventario_inicial(1, 10)

    # La fecha va explicita: Remito.fecha tiene default=peewee.fn.now(), que
    # sqlite no tiene y tira 'no such function: now'. Es un default de MySQL
    # que llego hasta aca.
    remito = Remito.create(cliente=1, fecha=date(2026, 1, 15), ptovta=1,
                           numero="00000001", forma_pago=1,
                           tipo_comprobante=92, estado="A", observaciones="")
    factura = Cabfact.create(tipocomp=TipoComprobante.get_by_id(6), cliente=1,
                             numero="0001-00000001", nombre="X", domicilio="X",
                             idremito=remito)

    # El remito sale con la mercaderia.
    stock.aplica_remito([(1, 5)], idremito=remito)
    # La factura llega con idremito puesto: la mercaderia ya salio.
    stock.aplica_factura([(1, 5)], idcabfact=factura,
                         idremito=factura.idremito,
                         lado=TipoComprobante.get_by_id(6).lado)

    assert stock.stock_de(1) == 5, \
        "una venta de 5 con remito deberia dejar 5 (10-5), dejo {}. El stock " \
        "esta bajando dos veces.".format(stock.stock_de(1))


def test_la_nota_de_credito_de_una_factura_con_remito_devuelve_la_mercaderia(base):
    """La excepcion a la excepcion: la NC repone, tenga remito o no.

    Si la mercaderia volvio, entra de nuevo. Frenar la NC por tener remito
    dejaria el stock bajo para siempre, y el remito ya habia descontado una
    vez que la NC deberia devolver.
    """
    from libs import stock
    from modelos.Cabfact import Cabfact
    from modelos.Remitos import Remito
    from modelos.Tipocomprobantes import TipoComprobante

    stock.registra_inventario_inicial(1, 10)
    remito = Remito.create(cliente=1, fecha=date(2026, 1, 15), ptovta=1,
                           numero="00000001", forma_pago=1,
                           tipo_comprobante=92, estado="A", observaciones="")
    stock.aplica_remito([(1, 5)], idremito=remito)

    nota = Cabfact.create(tipocomp=TipoComprobante.get_by_id(8), cliente=1,
                          numero="0001-00000003", nombre="X", domicilio="X",
                          idremito=remito)
    stock.aplica_factura([(1, 5)], idcabfact=nota, idremito=nota.idremito,
                         lado=TipoComprobante.get_by_id(8).lado)

    assert stock.stock_de(1) == 10, \
        "remito de 5 y nota de credito de 5 sobre 10 deberian dejar 10, " \
        "quedaron {}".format(stock.stock_de(1))


def test_una_factura_sin_remito_si_descuenta(base):
    """La venta directa, la de la venta rapida, no tiene remito: descuenta."""
    from libs import stock
    from modelos.Cabfact import Cabfact
    from modelos.Tipocomprobantes import TipoComprobante

    stock.registra_inventario_inicial(1, 10)
    factura = Cabfact.create(tipocomp=TipoComprobante.get_by_id(6), cliente=1,
                             numero="0001-00000002", nombre="X", domicilio="X",
                             idremito=None)

    stock.registra_salida(1, 5, origen="VENTA", idcabfact=factura)

    assert stock.stock_de(1) == 5


# -- Lo que no tiene que pasar ----------------------------------------------

def test_un_servicio_no_genera_movimientos(base):
    """"Mantenimiento" no se descuenta: no hay nada que contar.

    El catalogo mezcla productos con servicios, y si un servicio generase
    movimientos cada venta de un mantenimientoaria bajaria el stock de un
    servicio que no existe.
    """
    from libs import stock
    from modelos.MovStock import MovStock

    resultado = stock.registra_salida(2, 1)

    assert resultado is None, \
        "un articulo sin controlastock no deberia generar movimiento"
    assert MovStock.select().count() == 0, \
        "hay {} movimientos de un articulo que no controla stock".format(
            MovStock.select().count())


def test_una_cantidad_cero_no_deja_movimiento(base):
    """Cero no es un movimiento. Es ruido, y ensucia el reporte."""
    from libs import stock
    from modelos.MovStock import MovStock

    assert stock.registra_salida(1, 0) is None
    assert stock.registra_entrada(1, 0) is None
    assert stock.registra_ajuste(1, 0) is None
    assert MovStock.select().count() == 0


def test_un_articulo_inexistente_no_revienta(base):
    """Un renglon con un articulo que se borro no puede tirar la venta."""
    from libs import stock

    assert stock.registra_salida(9999, 2) is None
    assert stock.stock_de(9999) == 0


# -- Anular ------------------------------------------------------------------

def test_anular_devuelve_el_stock_y_deja_rastro(base):
    """Anular no borra: escribe el contrario.

    Si se borrara el movimiento, el historico dejaria de contar que hubo una
    correccion, y el stock quedaria en un valor del que nadie sabe de donde
    salio. Con el contrario, se ve que hubo un error y quien lo corrigio.
    """
    from libs import stock
    from modelos.MovStock import MovStock

    stock.registra_salida(1, 4)
    movimiento = MovStock.get(MovStock.idarticulo == 1)

    stock.anula(movimiento, observacion="se vendio de mas")

    assert stock.stock_de(1) == 0, \
        "anular una venta de 4 deberia devolver el stock a 0, quedo en {}".format(
            stock.stock_de(1))
    assert MovStock.select().count() == 2, \
        "anular tiene que dejar los dos movimientos, no borrar el primero"
    movimiento = MovStock.get_by_id(movimiento.idmovstock)
    assert movimiento.anula is not None, \
        "el movimiento anulado tiene que saber cual lo corrijo"


# -- Faltantes ---------------------------------------------------------------

def test_avisa_faltante_el_que_esta_por_debajo_del_minimo(base):
    from libs import stock

    stock.registra_inventario_inicial(1, 3)  # el minimo del articulo 1 es 5

    assert stock.hay_faltantes(1) is True


def test_un_minimo_de_cero_no_es_un_faltante(base):
    """Minimo 0 quiere decir "no pedi nada", no "pedi cero".

    Con un minimo en 0 y stock en 0, un articulo vacio seria un faltante
    eterno y el reporte de faltantes seria una lista de medio catalogo que no
    dice nada.
    """
    from libs import stock
    from modelos.Articulos import Articulo

    articulo = Articulo.get_by_id(1)
    articulo.stockminimo = 0
    articulo.save()

    assert stock.hay_faltantes(1) is False
    assert stock.faltantes() == []


def test_un_servicio_nunca_falta(base):
    from libs import stock

    stock.registra_entrada(2, 1)

    assert stock.hay_faltantes(2) is False


def test_faltantes_viene_del_mas_faltante_al_menos(base):
    from libs import stock
    from modelos.Articulos import Articulo

    Articulo.create(idarticulo=3, nombre="ACEITE", controlastock=True,
                    stockminimo=10, preciopub=1, costo=1, unidad="UN",
                    grupo=1, provppal=1, tipoiva="01", concepto="1")
    stock.registra_inventario_inicial(3, 1)  # falta 9
    stock.registra_inventario_inicial(1, 4)  # falta 1

    faltantes = stock.faltantes()
    nombres = [f["articulo"].nombre for f in faltantes]

    assert nombres == ["ACEITE", "GASOLINA"], \
        "esperaba el mas faltante primero, vino {}".format(nombres)


def test_revertir_un_comprobante_devuelve_el_stock(base):
    """Editar un remito tiene que devolver lo que habia descontado.

    Los renglones del remito se borran y se vuelven a escribir. Si lo
    descontado antes no se devuelve, cada edicion deja el stock mas bajo que
    la anterior, y no hay ningun aviso: los movimientos viejos siguen ahi y se
    suman a los nuevos.
    """
    from libs import stock
    from modelos.Remitos import Remito

    remito = Remito.create(cliente=1, fecha=date(2026, 1, 15), ptovta=1,
                           numero="00000001", forma_pago=1,
                           tipo_comprobante=92, estado="A", observaciones="")
    stock.aplica_remito([(1, 4)], idremito=remito)
    assert stock.stock_de(1) == -4

    stock.revierte_de_comprobante(idremito=remito.idremito,
                                  observacion="Remito modificado")

    assert stock.stock_de(1) == 0, \
        "despues de revertir deberia quedar en 0, quedo en {}".format(
            stock.stock_de(1))


def test_revertir_dos_veces_no_devuelve_dos_veces(base):
    """Revertir es idempotente, o un doble clic deja el stock al doble."""
    from libs import stock
    from modelos.Remitos import Remito

    remito = Remito.create(cliente=1, fecha=date(2026, 1, 15), ptovta=1,
                           numero="00000001", forma_pago=1,
                           tipo_comprobante=92, estado="A", observaciones="")
    stock.aplica_remito([(1, 4)], idremito=remito)

    stock.revierte_de_comprobante(idremito=remito.idremito)
    stock.revierte_de_comprobante(idremito=remito.idremito)

    assert stock.stock_de(1) == 0, \
        "revertir dos veces devolvio dos veces: el stock quedo en {}".format(
            stock.stock_de(1))


def test_revertir_solo_toca_los_movimientos_de_ese_comprobante(base):
    """Revertir un remito no puede tocar la venta de otro lado.

    Un movimiento ya anulado queda fuera, y los de otros comprobantes no se
    ven: revertir es por comprobante, no 'deshacer el ultimo movimiento'.
    """
    from libs import stock
    from modelos.Cabfact import Cabfact
    from modelos.Remitos import Remito
    from modelos.Tipocomprobantes import TipoComprobante

    stock.registra_inventario_inicial(1, 100)
    remito = Remito.create(cliente=1, fecha=date(2026, 1, 15), ptovta=1,
                           numero="00000001", forma_pago=1,
                           tipo_comprobante=92, estado="A", observaciones="")
    stock.aplica_remito([(1, 4)], idremito=remito)
    factura = Cabfact.create(tipocomp=TipoComprobante.get_by_id(6), cliente=1,
                             numero="0001-00000009", nombre="X", domicilio="X",
                             idremito=None)
    stock.aplica_factura([(1, 6)], idcabfact=factura,
                         lado=TipoComprobante.get_by_id(6).lado)

    stock.revierte_de_comprobante(idremito=remito.idremito)

    assert stock.stock_de(1) == 94, \
        "revertir el remito de 4 sobre 100-4-6 deberia dejar 94, quedo {}".format(
            stock.stock_de(1))


# -- Consultas en bloque -----------------------------------------------------

def test_stock_de_todos_incluye_los_que_no_controlan(base):
    """La pantalla de stock tiene que poder mostrar un producto sin marcar.

    Si la consulta filtrara por controlastock, el producto aparecio en la
    lista del ABM de Productos pero no en la de Stock, y el operador no
    entendia por que.
    """
    from libs import stock

    todos = stock.stock_de_todos(controlados=False)

    assert set(todos) == {1, 2}, \
        "con controlados=False tienen que aparecer los dos, aparecieron {}".format(
            sorted(todos))


def test_stock_de_todos_consulta_todo_de_a_una(base):
    """Con controlados=False entran todos, con stock en 0 si no se movieron.

    Con controlados=True (el default) solo entran los marcados, asi que un
    servicio no aparece: es lo que quiere la pantalla de faltantes, no la de
    stock.
    """
    from libs import stock

    stock.registra_entrada(1, 7)
    stock.registra_salida(1, 2)

    todos = stock.stock_de_todos(controlados=False)

    assert todos[1] == 5
    assert todos[2] == 0, \
        "el servicio tiene que aparecer con 0, no con None"

    solo_controlados = stock.stock_de_todos()
    assert set(solo_controlados) == {1}, \
        "con controlados=True solo entra lo que controla, entro {}".format(
            sorted(solo_controlados))


# -- El atajo de arranque ----------------------------------------------------

def test_marcar_como_controlados_pasa_todo_lo_que_falta(base):
    """El atajo para cuando alguien cargo veinte productos y no quiere
    acordarse de tildar veinte casillas."""
    from libs import stock

    assert stock.marcar_como_controlados() == 1
    assert stock.sin_controlar() == []
    assert stock.controla(stock.Articulo.get_by_id(2)) is True
