"""La emision de verdad tiene que descontar stock.

Que esta comprobando
--------------------
Que `Facturas.GrabaFE` - el metodo por donde pasan las TRES pantallas que
emiten: la venta rapida, el formulario de emision y la que se abre desde un
remito - escriba los movimientos. Los tests de libs/stock.py dicen que la regla
esta bien; este dice que la regla llega a ejecutarse.

Que pasa sin esto
-----------------
El stock queda en cero para siempre, la app no da ningun error, y todo
parece andando. Es el fallo mas caro de todos los posibles en una feature de
stock, porque es silencioso: no hay exception, no hay pantalla roja, hay un
numero que miente.

Por que el controlador entero y no el metodo suelto
--------------------------------------------------
`GrabaFE` lee la grilla, la cabecera y veinte controles de la vista. Separarlo
de la vista seria probar un metodo que la app no ejecuta: el mismo error que
daba un test que reemplaza el widget donde ocurre la falla. Se construye el
controlador de verdad, con Qt en offscreen, y se le habla como el operador.

Que no se toca
--------------
ARCA. La autorizacion ya se probó en otros lados; aca interesa lo que pasa
DESPUES, cuando la factura ya esta autorizada y hay que guardarla.
"""

import os
import sys
from datetime import date

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
    """Catalogo propio, con stock, y se devuelve al sandbox al final."""
    from peewee import SqliteDatabase

    from modelos.Articulos import Articulo
    from modelos.Cabfact import Cabfact
    from modelos.Cajeros import Cajero
    from modelos.Clientes import Cliente
    from modelos.CpbteRelacionado import CpbteRel
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
               Cliente, Localidad, Tipodoc, Tiporesp, Formapago,
               TipoComprobante, Cajero, Cabfact, Detfact, CpbteRel, Remito,
               DetalleRemito)
    anteriores = [(m, m._meta.database) for m in modelos]

    memoria = SqliteDatabase(":memory:")
    for modelo in modelos:
        modelo.bind(memoria)
    memoria.connect()
    memoria.create_tables(modelos, safe=True)

    Tipoiva.insert_many([{"codigo": "01", "descrip": "IVA GENERAL",
                          "iva": 21}]).execute()
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
    Cliente.insert_many([{"idcliente": 1, "nombre": "CONSUMIDOR FINAL",
                          "domicilio": "S/N", "localidad": 1, "dni": 11111111,
                          "tipodocu": 0, "tiporesp": 1, "formapago": 1,
                          "percepcion": 1}]).execute()
    Articulo.insert_many([
        {"idarticulo": 1, "nombre": "GASOLINA", "controlastock": True,
         "stockminimo": 5, "preciopub": 100, "costo": 80, "unidad": "UN",
         "grupo": 1, "provppal": 1, "tipoiva": "01", "concepto": "1"},
    ]).execute()

    yield memoria

    memoria.close()
    for modelo, anterior in anteriores:
        modelo.bind(anterior)


@pytest.fixture
def emisor(qt, base, monkeypatch):
    """Un FacturaController real, apuntando a la base de memoria y listo para
    guardar, sin hablar con ARCA y sin imprimir PDFs.
    """
    monkeypatch.setattr(sys, "argv", [sys.argv[0]])

    from controladores.Facturas import FacturaController
    from libs import stock

    c = FacturaController()
    c.view.show()
    qt.processEvents()

    # El atomic del controlador tiene que caer sobre la MISMA base que los
    # modelos. En produccion lo son, pero aca los modelos estan atados a la
    # base en memoria y `db` sigue siendo la conexion del sandbox: sin esto,
    # `db.atomic()` abre una transaccion sobre una base y `cabfact.save()`
    # escribe en la otra, y la transaccion no revierte NADA. El sintoma es
    # silencioso y mintioso: el test de la transaccion pasa con el atomic
    # escribiendo en el lugar correcto y solo falla si alguien lo saca.
    monkeypatch.setattr("controladores.Facturas.db", base)

    # Lo que haria ARCA y el visor, afuera del camino que se quiere probar.
    monkeypatch.setattr(c, "ImprimeFactura", lambda *a, **k: True)
    monkeypatch.setattr(c.view.layoutFactura, "AssignNumero", lambda: None)
    monkeypatch.setattr(c.view.layoutFactura, "numero", "0001-00000001")

    # ObtieneNumeroFactura consulta a ARCA el ultimo numero emitido. Sin esto
    # el test depende de la red y de los certificados: hoy pasa porque hay
    # conexion, y el dia que no la hay falla con un error que no tiene nada
    # que ver con el stock. Aca se deja el numero local.
    def numero_local(self):
        self.tipo_cpte = 6
        self.view.layoutFactura.lineEditNumero.setText("00000001")

    monkeypatch.setattr(FacturaController, "ObtieneNumeroFactura", numero_local)

    c.cliente = Cliente_de_prueba()
    c.tipo_cpte = 6
    c.concepto = "1"
    c.netos = {21: 100.0, 10.5: 0}
    c.idremito = None

    stock.registra_inventario_inicial(1, 10)
    yield c
    c.view.Cerrar()


def Cliente_de_prueba():
    """El cliente con las relaciones que GrabaFE lee, sin tocar la base."""
    class _Percepcion(object):
        porcentaje = 0

    class _Tiporesp(object):
        idtiporesp = 1

    class Cliente(object):
        idcliente = 1
        tiporesp = _Tiporesp()
        percepcion = _Percepcion()

    return Cliente()


def _cargar_una_linea(controller, cantidad="2", precio="100"):
    """Escribe una linea en la grilla por el camino de la venta rapida.

    Se usa `cargar_venta_simple` y no `AgregaItem` por dos motivos: es el
    camino que de verdad recorre la venta rapida, y limpia la grilla antes.
    Agregando a mano, la fila que la vista crea sola queda adelante, se lee
    como un renglon de mas y el stock baja de mas: el test mide el caso
    equivocado sin que se note.
    """
    from decimal import Decimal

    from controladores.venta_simple_totales import RenglonVenta

    controller.cargar_venta_simple(
        cliente_id=None,
        renglones=[RenglonVenta(
            codigo="1",
            detalle="GASOLINA",
            cantidad=Decimal(cantidad),
            precio_unitario=Decimal(precio),
            iva=Decimal("21"),
        )],
        forma_pago_id=None,
    )


# -- Lo que tiene que pasar --------------------------------------------------

def test_guardar_una_factura_descuenta_el_stock(emisor):
    """La venta de 2 sobre un stock de 10 deja 8."""
    from libs import stock
    from modelos.MovStock import MovStock

    _cargar_una_linea(emisor)

    assert emisor.GrabaFE() is True

    assert stock.stock_de(1) == 8, \
        "una venta de 2 sobre un inventario de 10 deberia dejar 8, dejo {}. " \
        "Movimientos escritos: {}. Si queda en 10, la emision no esta " \
        "llamando a la regla de stock.".format(
            stock.stock_de(1),
            [(m.origen, str(m.cantidad), m.tipo) for m in MovStock.select()])


def test_la_factura_guardada_es_la_que_movio_el_stock(emisor):
    """El movimiento tiene que apuntar a ESTA factura, no a cualquiera.

    Sin esto el stock baja pero no se puede explicar por que: el reporte de
    movimientos mostraria un origen VENTA sin numero, y el caso mas caro de
    todos (el doble descuento) seria imposible de investigar.
    """
    from libs import stock
    from modelos.Cabfact import Cabfact
    from modelos.MovStock import MovStock

    _cargar_una_linea(emisor)
    emisor.GrabaFE()

    cabfact = Cabfact.select().order_by(Cabfact.idcabfact.desc()).first()
    movimiento = MovStock.select().where(MovStock.origen == "VENTA").first()

    assert movimiento is not None, "no se escribio ningun movimiento de venta"
    # `idcabfact_id` y no `idcabfact`: peewee resuelve la relacion y devuelve
    # el objeto, asi que `movimiento.idcabfact == 1` compara un Cabfact con un
    # entero y es False aunque sean el mismo comprobante.
    assert movimiento.idcabfact_id == cabfact.idcabfact, \
        "el movimiento apunta a la factura {} y la ultima guardada es {}: " \
        "el stock baja y queda sin trazabilidad de por que".format(
            movimiento.idcabfact_id, cabfact.idcabfact)
    assert movimiento.cantidad == -2, \
        "una venta tiene que anotar la cantidad negativa, ynto {}".format(
            movimiento.cantidad)


def test_una_factura_con_remito_no_descuenta_dos_veces(emisor):
    """Remito y factura sobre el mismo negocio: una sola salida.

    El remito ya descontó cuando la mercaderia salio. Esta es la prueba con el
    codigo de la app, no con el `if` escrito en el test: si `GrabaFE` no
    respetara la regla, el stock bajaria dos veces y esto falla.
    """
    from libs import stock
    from modelos.Remitos import Remito

    remito = Remito.create(cliente=1, fecha=date(2026, 1, 15), ptovta=1,
                           numero="00000001", forma_pago=1,
                           tipo_comprobante=92, estado="A", observaciones="")
    stock.aplica_remito([(1, 2)], idremito=remito)
    assert stock.stock_de(1) == 8

    emisor.idremito = remito
    _cargar_una_linea(emisor)
    emisor.GrabaFE()

    assert stock.stock_de(1) == 8, \
        "la factura con remito esta descontando otra vez: quedo {} en vez de " \
        "8. La mercaderia esta saliendo dos veces.".format(stock.stock_de(1))


def test_una_nota_de_credito_devuelve_la_mercaderia(emisor):
    from libs import stock

    _cargar_una_linea(emisor)
    emisor.GrabaFE()
    assert stock.stock_de(1) == 8

    emisor.tipo_cpte = 8          # NOTA CREDITO B, lado H
    emisor.netos = {21: -100.0, 10.5: 0}
    emisor.view.gridFactura.setRowCount(0)
    _cargar_una_linea(emisor, cantidad="2", precio="-50")
    emisor.GrabaFE()

    assert stock.stock_de(1) == 10, \
        "una nota de credito de 2 sobre una venta de 2 deberia devolver el " \
        "stock a 10, quedo en {}".format(stock.stock_de(1))


def test_la_factura_abierta_desde_el_remito_no_descuenta_dos_veces(emisor):
    """El camino completo: remito guardado, factura abierta desde el, emitida.

    Es el caso de la vida real. Un remito sale con la mercaderia, mas tarde se
    abre la factura desde el y se emite. El stock tiene que bajar una vez.

    Se ejercita `cargar_desde_remito` de verdad, no un `idremito` puesto a
    mano: si ese metodo dejara de anotar el remito, este test lo detecta, y
    con un idremito armedado a mano pasaria en verde sin probar el enlace.
    """
    from decimal import Decimal

    from libs import stock
    from modelos.Remitos import DetalleRemito, Remito

    remito = Remito.create(cliente=1, fecha=date(2026, 1, 15), ptovta=1,
                           numero="00000001", forma_pago=1,
                           tipo_comprobante=92, estado="A", observaciones="")
    DetalleRemito.create(remito=remito, producto=1, detalle="GASOLINA",
                         cantidad=Decimal("2"), precio=Decimal("100"),
                         # '01' y no 1: Tipoiva usa codigo como clave primaria
                         # y los codigos van con cero a la izquierda. El
                         # default=1 que tiene el modelo no existe en la tabla.
                         tipo_iva="01")

    # La mercaderia sale con el remito.
    stock.aplica_remito(list(DetalleRemito.select().where(
        DetalleRemito.remito == remito)), idremito=remito.idremito)
    assert stock.stock_de(1) == 8

    # Se abre la factura desde el remito, como haria el boton.
    emisor.cargar_desde_remito(remito.idremito)
    assert emisor.idremito == remito.idremito, \
        "cargar_desde_remito tiene que dejar anotado de que remito es la " \
        "factura, si no GrabaFE no tiene forma de saber que la mercaderia ya " \
        "salo y la descuenta dos veces"

    assert emisor.GrabaFE() is True

    assert stock.stock_de(1) == 8, \
        "remito de 2 y factura del mismo remito de 2 sobre un inventario de " \
        "10 dejaron {} en vez de 8. La mercaderia esta saliendo dos veces.".format(
            stock.stock_de(1))


# -- Lo que no puede pasar ---------------------------------------------------

def test_si_falla_un_renglon_no_queda_factura_ni_stock(emisor, monkeypatch):
    """La transaccion: o se guarda todo, o no se guarda nada.

    Antes cada save() era su propia transaccion, y un renglon que fallaba
    dejaba la cabecera guardada con la mitad de los items. Con stock en el
    camino, eso es una mercaderia que salio de la mercaderia que quedo: el
    conteo no cierra y no hay forma de saber desde cuando.
    """
    from libs import stock
    from modelos.Cabfact import Cabfact
    from modelos.Detfact import Detfact
    from modelos.MovStock import MovStock

    # Se rompe el SEGUNDO renglone, cuando la cabecera ya esta guardada.
    guardar_original = Detfact.save
    llamadas = {"n": 0}

    def save_que_falla_en_el_segundo(self, *args, **kwargs):
        llamadas["n"] += 1
        if llamadas["n"] == 2:
            raise ValueError("se rompio el segundo renglone")
        return guardar_original(self, *args, **kwargs)

    monkeypatch.setattr(Detfact, "save", save_que_falla_en_el_segundo)
    monkeypatch.setattr(emisor, "ImprimeFactura", lambda *a, **k: True)

    controller = emisor
    controller.view.gridFactura.AgregaItem(items=["2", "1", "GASOLINA",
                                                  "100", "21", "200"])
    controller.view.gridFactura.AgregaItem(items=["1", "1", "GASOLINA",
                                                  "100", "21", "100"])

    try:
        controller.GrabaFE()
    except ValueError:
        pass

    assert Cabfact.select().count() == 0, \
        "quedo una cabecera sin sus renglones: {} facturas".format(
            Cabfact.select().count())
    assert Detfact.select().count() == 0, \
        "quedaron renglones sueltos: {}".format(Detfact.select().count())
    assert MovStock.select().where(MovStock.origen == "VENTA").count() == 0, \
        "desconto stock de una factura que no se guardo: el inventario baja " \
        "por una venta que no existio"
    assert stock.stock_de(1) == 10, \
        "el inventario quedo en {} en vez de 10".format(stock.stock_de(1))
