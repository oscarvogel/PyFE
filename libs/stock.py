# coding=utf-8
"""La logica del stock, sin pantallas.

Que hay aca y que no
--------------------
Aca esta TODO el stock menos los tres caminos que lo disparan. Las funciones
de este modulo no saben nada de Qt ni de facturas: reciben un id de articulo,
una cantidad y un comprobante, y escriben un movimiento. Los controladores
(ventas, remitos, compras) son los unicos que saben de donde salio cada
llamada.

Por que esta separado
---------------------
Porque es la unica parte del stock que se puede probar de verdad. Un
`registrar_entrada()` no necesita QApplication, ni una vista, ni ARCA, ni un
hilo: se le pasa un id y una cantidad y se verifica el stock que queda. Los
tests de este modulo son los que dicen si el stock esta bien; los de las
pantallas solo dicen si la pantalla no se rompe.

Por que la cantidad va CON signo
--------------------------------
Porque es lo que hace que `SUM(cantidad)` sea el stock, sin una columna mas.
Pero es tambien la fuente de error clasica: un signo mal puesto hace que una
venta sume stock en vez de restarlo, y eso no se ve hasta que el inventario
esta mal. Por eso hay tres funciones de entrada y ninguna que acepte el signo
como viene: `registra_salida` recibe 3 y anota -3, `registra_entrada`
recibe 3 y anota +3, y `registra_ajuste` es la unica donde el signo es parte
de lo que el operador quiere decir.
"""

from decimal import Decimal
from datetime import date

from peewee import fn

from modelos.Articulos import Articulo
from modelos.MovStock import (MovStock, ORIGEN_AJUSTE, ORIGEN_COMPRA,
                              ORIGEN_INICIAL, ORIGEN_REMITO, ORIGEN_VENTA,
                              TIPO_AJUSTE, TIPO_ENTRADA, TIPO_SALIDA)

# Los movimientos se suman en SQL, y SUM sobre DECIMAL devuelve float en
# sqlite: 0.1 + 0.2 sale 0.30000000000000004. Se redondea a las cuatro
# decimales con que se guarda el stock, que es tambien con que se mide.
CUATRO_DECIMALES = Decimal("0.0001")

CERO = Decimal("0")

# `articulos.concepto`: 1 = producto, 2 = servicio (ver
# ComboConceptoFacturacion en libs/ComboBox.py, que es el combo que lo
# edita).
#
# OJO con lo que esto NO es: `controlastock` NO se deduce de aca. En un
# mismo catalogo hay productos que no se inventan y servicios que si,
# asi que el campo sigue siendo explicito (ver modelos/Articulos.py).
#
# Lo unico que se deduce de `concepto` es a quien puede tocar el atajo de
# "Marcar productos": marcar un servicio de masse lo manda a negativo con
# la primera venta, y ese error se descubre semanas despues. Ver
# `marcar_como_controlados`.
CONCEPTO_PRODUCTO = '1'


# -- Consultas ---------------------------------------------------------------

def controla(articulo):
    """Este articulo participa del control de stock?

    No es lo mismo que ser un producto: `concepto` responde como se factura
    ante ARCA, y hay articulos de consumo interno que tampoco se controlan.
    Por eso es un campo propio y no una regla deducida.
    """
    if articulo is None:
        return False
    return bool(getattr(articulo, "controlastock", False))


def stock_de(idarticulo):
    """Cuanto hay de este articulo. Derivado de los movimientos."""
    if not idarticulo:
        return CERO
    total = (MovStock
             .select(fn.SUM(MovStock.cantidad))
             .where(MovStock.idarticulo == idarticulo)
             .scalar())
    if total is None:
        return CERO
    return Decimal(str(total)).quantize(CUATRO_DECIMALES)


def stock_de_articulo(articulo):
    if articulo is None:
        return CERO
    return stock_de(articulo.idarticulo)


def stock_de_todos(controlados=True):
    """{idarticulo: stock} para pintar una grilla entera de una vez.

    Una consulta y no una por articulo: son mil llamadas de SUM en una pantalla
    con mil productos, y en sqlite eso se nota.

    `controlados` en False trae tambien los que no controlan stock, con 0. Los
    necesita la pantalla de stock, que tiene que poder mostrar un producto
    aunque todavia no se lo haya marcado.
    """
    consulta = Articulo.select()
    if controlados:
        consulta = consulta.where(Articulo.controlastock == True)  # noqa: E712

    filas = (MovStock
             .select(MovStock.idarticulo,
                     fn.SUM(MovStock.cantidad).alias("total"))
             .group_by(MovStock.idarticulo)
             .dicts())

    stocks = {}
    for fila in filas:
        stocks[fila["idarticulo"]] = Decimal(
            str(fila["total"] or 0)).quantize(CUATRO_DECIMALES)
    return {a.idarticulo: stocks.get(a.idarticulo, CERO)
            for a in consulta}


def hay_faltantes(idarticulo):
    """Is, contando solo lo que el operador pidio.

    Un articulo con stockminimo en 0 no esta faltando nunca: 0 es "no pediste
    nada", no "pediste cero".
    """
    articulo = Articulo.get_or_none(Articulo.idarticulo == idarticulo)
    if articulo is None or not controla(articulo):
        return False
    minimo = Decimal(str(articulo.stockminimo or 0))
    if minimo <= 0:
        return False
    return stock_de(idarticulo) < minimo


def faltantes():
    """Los articulos que estan por debajo del minimo, del mas faltante al menos.

    Devuelve filas con lo que la grilla necesita: articulo, stock y minimo.
    """
    stocks = stock_de_todos(controlados=True)
    salida = []
    for a in Articulo.select().where(Articulo.controlastock == True):  # noqa: E712
        minimo = Decimal(str(a.stockminimo or 0))
        if minimo <= 0:
            continue
        stock = stocks.get(a.idarticulo, CERO)
        if stock < minimo:
            salida.append({"articulo": a, "stock": stock, "minimo": minimo,
                           "faltante": minimo - stock})
    salida.sort(key=lambda f: f["faltante"], reverse=True)
    return salida


def sin_controlar(incluir_servicios=True, solo_servicios=False):
    """Los articulos del catalogo que todavia no se marcaron.

    No es un error, pero es la razon por la que un producto puede no
    descontarse y el operador no entender por que. La pantalla de stock lo
    muestra y ofrece marcarlos de una vez.

    Los dos flags existen para que el atajo de arranque no tenga que
    filtrar en Python lo que la base puede filtrar: `incluir_servicios=False`
    trae solo productos, que es lo que se puede marcar de masse, y
    `solo_servicios=True` trae los servicios, que es lo que hay que contar
    para poder avisar cuantos quedaron afuera.

    Ojo con el nombre del flag: `incluir_servicios=False` no dice "no hay
    servicios", dice "no los traigas". Sin servicios en el catalogo
    devuelve una lista vacia, no None.
    """
    consulta = Articulo.select().where(Articulo.controlastock == False)  # noqa: E712
    if not incluir_servicios:
        consulta = consulta.where(Articulo.concepto == CONCEPTO_PRODUCTO)
    elif solo_servicios:
        consulta = consulta.where(Articulo.concepto != CONCEPTO_PRODUCTO)
    return list(consulta)


# -- Escritura ---------------------------------------------------------------

def _registra(idarticulo, cantidad, origen, tipo, fecha=None,
              idcabfact=None, idremito=None, idpcabecera=None,
              observacion=''):
    """Escribe un movimiento. Devuelve el movimiento, o None si no va.

    None tiene un motivo unico y deliberado: el articulo no controla stock.
    Asi los flujos pueden llamar siempre sin preguntar, y un servicio no
    ensucia la tabla de movimientos con filas que nadie va a consultar.
    """
    articulo = Articulo.get_or_none(Articulo.idarticulo == idarticulo)
    if articulo is None or not controla(articulo):
        return None

    return MovStock.create(
        fecha=fecha if fecha is not None else date.today(),
        idarticulo=articulo.idarticulo,
        cantidad=Decimal(str(cantidad)).quantize(CUATRO_DECIMALES),
        tipo=tipo,
        origen=origen,
        idcabfact=idcabfact,
        idremito=idremito,
        idpcabecera=idpcabecera,
        observacion=observacion or '',
    )


def registra_salida(idarticulo, cantidad, origen=ORIGEN_VENTA,
                    idcabfact=None, idremito=None, idpcabecera=None,
                    fecha=None, observacion=''):
    """Sale mercaderia. La cantidad va positiva; se anota negativa.

    `cantidad` positiva a proposito: la que escribe esto ya sabe que la
    mercaderia sale, y tener que acordarse de negation es una fuente de
    errores de los dos lados.
    """
    if Decimal(str(cantidad)) == 0:
        return None
    return _registra(idarticulo, -Decimal(str(cantidad)), origen, TIPO_SALIDA,
                     fecha=fecha, idcabfact=idcabfact, idremito=idremito,
                     idpcabecera=idpcabecera, observacion=observacion)


def registra_entrada(idarticulo, cantidad, origen=ORIGEN_COMPRA,
                     idcabfact=None, idremito=None, idpcabecera=None,
                     fecha=None, observacion=''):
    """Entra mercaderia: compra, devolucion o nota de credito."""
    if Decimal(str(cantidad)) == 0:
        return None
    return _registra(idarticulo, Decimal(str(cantidad)), origen, TIPO_ENTRADA,
                     fecha=fecha, idcabfact=idcabfact, idremito=idremito,
                     idpcabecera=idpcabecera, observacion=observacion)


def registra_ajuste(idarticulo, cantidad, observacion='',
                    origen=ORIGEN_AJUSTE, fecha=None):
    """Correccion o inventario inicial. El signo es lo que se quiso decir.

    Inventario inicial y ajuste manual son el mismo movimiento con distinto
    `origen`: el primero dice "asi arranca esto" y el segundo "esto se
    corrigio". La diferencia importa cuando alguien pregunta por que el stock
    quedo asi.
    """
    if Decimal(str(cantidad)) == 0:
        return None
    return _registra(idarticulo, cantidad, origen, TIPO_AJUSTE,
                     fecha=fecha, observacion=observacion)


def registra_inventario_inicial(idarticulo, cantidad, observacion=''):
    return registra_ajuste(idarticulo, cantidad,
                           observacion=observacion or 'Inventario inicial',
                           origen=ORIGEN_INICIAL)


def anula(movimiento, observacion=''):
    """Escribe el movimiento contrario en vez de borrar el original.

    Borrar el movimiento dejaria el stock en el valor que nunca existio y
    perderia el rastro de que se corrigio. Anulando, el historico cuenta que
    paso y el stock queda igual.
    """
    if movimiento is None:
        return None
    contrario = MovStock.create(
        fecha=movimiento.fecha,
        idarticulo=movimiento.idarticulo,
        cantidad=-movimiento.cantidad,
        tipo=movimiento.tipo,
        origen=movimiento.origen,
        idcabfact=movimiento.idcabfact,
        idremito=movimiento.idremito,
        idpcabecera=movimiento.idpcabecera,
        anula=movimiento,
        observacion=observacion or 'Anulacion',
    )
    movimiento.anula = contrario
    movimiento.save()
    return contrario


def revierte_de_comprobante(idremito=None, idcabfact=None, idpcabecera=None,
                            observacion=''):
    """Da de baja los movimientos de un comprobante, escribiendo los contrarios.

    Para cuando un remito se modifica: sus renglones se borran y se vuelven a
    escribir, asi que lo descontado antes hay que devolverlo antes de quitar
    los renglones viejos. Si se hiciera al reves, cada edicion del remito
    dejaria el stock mas bajo.

    Solo toca los movimientos que todavia no fueron anulados, asi que llamar
    dos veces no descuenta dos veces.
    """
    consulta = MovStock.select().where(MovStock.anula.is_null(True))
    if idremito is not None:
        consulta = consulta.where(MovStock.idremito == idremito)
    elif idcabfact is not None:
        consulta = consulta.where(MovStock.idcabfact == idcabfact)
    elif idpcabecera is not None:
        consulta = consulta.where(MovStock.idpcabecera == idpcabecera)
    else:
        return 0

    movimientos = list(consulta)
    for movimiento in movimientos:
        anula(movimiento, observacion=observacion or 'Comprobante modificado')
    return len(movimientos)


def descuenta_lado(lado):
    """Que signo corresponde al `lado` de un comprobante.

    'D' (factura, nota de debito) saca mercaderia; 'H' (nota de credito) la
    devuelve. El lado vacio es el de los proformas, que no mueven stock: se
    devuelve None y es el flujo el que decide, porque un remito proforma si
    mueve y su tipo de comprobante es justamente el que no tiene lado.
    """
    if lado == 'D':
        return -1
    if lado == 'H':
        return 1
    return None


# -- Los flujos: por donde entran las llamadas --------------------------------

def _pares(detalles):
    """Normaliza los renglones a (idarticulo, cantidad).

    Acepta las dos formas que usan los controladores: los objetos del modelo
    y las tuplas de la grilla. Asi el llamador no tiene que transformar nada y
    la comparacion de los tests es contra algo que los flujos hacen de verdad.

    Ojo con el nombre de la clave. `Detfact` y `DetFactProv` la llaman
    `idarticulo`, pero `DetalleRemito` la llama `producto`. Y por eso se mira
    el atributo crudo (`producto_id`) y no el relacionado: `detalle.producto`
    devuelve el Articulo entero, y de ahi habria que volver a sacar el id.
    """
    for detalle in detalles or []:
        if hasattr(detalle, "idarticulo"):
            yield detalle.idarticulo_id, detalle.cantidad
        elif hasattr(detalle, "producto_id"):
            yield detalle.producto_id, detalle.cantidad
        else:
            idarticulo, cantidad = detalle[0], detalle[1]
            yield idarticulo, cantidad


def aplica_factura(detalles, idcabfact, idremito=None, lado='D',
                   origen=ORIGEN_VENTA):
    """Aplica una factura al stock. Devuelve cuantos movimientos escribio.

    La regla del remito vive ACA y no en quien llama, y esa es toda la
    gracia: si el `if factura.idremito` estuviera en el controlador, cada
    pantalla que emita tendria que acordarse, y una que se olvide descuenta
    dos veces sin que nada falle.

    - lado 'D' (factura, nota de debito) saca. Si tiene remito, NO saca: esa
      mercaderia ya salio con el remito y volver a restarla es el error mas
      caro de esta feature, porque no se ve en ninguna pantalla.
    - lado 'H' (nota de credito) devuelve, tenga remito o no: si la mercaderia
      volvio, entra de nuevo.
    - lado vacio (proforma) no hace nada por si mismo. Un proforma de venta es
      un remito, y de eso se encarga aplica_remito().
    """
    signo = descuenta_lado(lado)
    if signo is None:
        return 0
    if signo < 0 and idremito is not None:
        return 0

    escritos = 0
    for idarticulo, cantidad in _pares(detalles):
        if signo < 0:
            mov = registra_salida(idarticulo, cantidad, origen=origen,
                                  idcabfact=idcabfact)
        else:
            mov = registra_entrada(idarticulo, cantidad, origen=origen,
                                   idcabfact=idcabfact)
        if mov is not None:
            escritos += 1
    return escritos


def aplica_remito(detalles, idremito, origen=ORIGEN_REMITO):
    """Aplica un remito. Siempre resta: el remito es la salida de la mercaderia.

    No importa que haya una factura despues: esa es la que se frena en
    aplica_factura(). Si el control estuviera al reves, el remito tendria que
    preguntar por facturas que todavia no existen.
    """
    escritos = 0
    for idarticulo, cantidad in _pares(detalles):
        mov = registra_salida(idarticulo, cantidad, origen=origen,
                              idremito=idremito)
        if mov is not None:
            escritos += 1
    return escritos


def aplica_compra(detalles, idpcabecera, origen=ORIGEN_COMPRA):
    """Aplica una factura de proveedor. Suma lo que se compro.

    Solo los renglones que tengan articulo elegido mueven stock: los que no
    lo tienen son gastos, impuestos o servicios que no entran al inventario.
    Por eso no usa `_pares`: un renglon sin articulo se tiene que saltar, y
    `_pares` no distingue "sin articulo" de "articulo vacio".
    """
    escritos = 0
    for detalle in detalles or []:
        if hasattr(detalle, "idarticulo_id"):
            idarticulo, cantidad = detalle.idarticulo_id, detalle.cantidad
        elif isinstance(detalle, dict):
            idarticulo = detalle.get("idarticulo")
            cantidad = detalle.get("cantidad")
        else:
            idarticulo, cantidad = detalle[0], detalle[1]
        if not idarticulo:
            continue
        mov = registra_entrada(idarticulo, cantidad, origen=origen,
                               idpcabecera=idpcabecera)
        if mov is not None:
            escritos += 1
    return escritos


# -- Varios ------------------------------------------------------------------

def marcar_como_controlados(articulos=None):
    """Marca el control de stock de los que faltan.

    Sin argumentos marca **solo los productos** (`concepto == '1'`), no todo
    lo que este en False. Es la situacion de arranque: alguien cargo veinte
    productos y no quiere acordarse de tildar veinte casillas.

    Y el filtro a productos es lo importante. Antes marcaba tambien los
    servicios, y en un catalogo de comercio general (que es para lo que esta
    armado el modulo) casi todos los servicios estan en False. El resultado
    era que cada venta de un mantenimientoaba un movimiento de stock, lo
    dejaba en negativo para siempre y llenaba la pantalla de Stock de
    "Negativo" en renglones que no son mercaderia.

    Esto NO contradice que `controlastock` sea explicito y no deducido: el
    filtro es para el atajo de masse, que no puede tener un boton de "dar de
    baja" al lado. Un producto que no se inventa se desmarca en Productos, y
    un servicio que si se quiere controlar se marca a mano, que es un caso
    raro y deliberado.

    Con `articulos` se marca la lista que se le pase y solo esa: el que elige
    sabe lo que hace.
    """
    if articulos is not None:
        ids = [a.idarticulo if hasattr(a, "idarticulo") else a for a in articulos]
        if not ids:
            return 0
        return Articulo.update(controlastock=True).where(
            Articulo.idarticulo.in_(ids)).execute()

    # El camino del atajo. Se pide la lista primero y recien despues se
    # actualiza: un UPDATE con el filtro directo contaria como "modificados"
    # las filas que ya estaban en True en MySQL (que devuelve las rows
    # matched y no las changed), y el controller usa ese numero para decir
    # "marque N".
    ids = [a.idarticulo for a in sin_controlar(incluir_servicios=False)]
    if not ids:
        return 0
    return Articulo.update(controlastock=True).where(
        Articulo.idarticulo.in_(ids)).execute()
