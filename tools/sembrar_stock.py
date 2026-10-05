# coding=utf-8
"""Siembra datos de stock para probar el modulo a mano.

Para que sirve
--------------
Para abrir la app contra el sandbox y tener algo REAL en las tres pantallas de
stock, con todos los estados que puede mostrar una fila. Con los articulos de
siempre no se ve ni la mitad: nunca hay uno en negativo, nunca hay un remito, y
el boton de marcar productos no tiene con que fallar.

Que deja
--------
- 10 productos con control de stock y minimo, repartidos en todos los estados
  que muestra la columna "Estado": OK, Falta, Sin stock y Negativo.
- Un producto que NO se controla pero es producto (`concepto` 1): el caso para
  el que no sirve una regla que adivine, y el que "Marcar productos" tiene que
  marcar.
- Dos servicios (`concepto` 2) que NO se controlan: los que "Marcar productos"
  tiene que dejar afuera.
- Un remito con su factura. El remito descuenta y la factura NO vuelve a
  descontar: es la regla mas cara del modulo, y aca queda guardada en los
  datos. Las pilas tienen que quedar en 5, no en -5.
- Una venta anulada, para que la columna "Anulado" no salga toda vacia.
- Un ajuste con observacion real, que es el unico flujo donde el operador
  escribe cualquier frase.

Que verifica
------------
No se limita a escribir y decir "listo". Al final vuelve a leer el stock de
cada articulo con `libs.stock.stock_de` y lo compara con el numero que el
catalogo declara arriba, y ademas con el estado que da
`controladores.Stock.estado_de`. Si algo no da, sale con codigo 1 y la
diferencia.

Eso es lo que lo hace util como prueba del modulo: el estado final esta
declarado y comprobado, no es un INSERT que produce datos plausibles.

Porque NO toca la base de trabajo
--------------------------------
Porque ya paso lo peor: una migracion de prueba corrio sobre la base de
trabajo y perdio 37 ventas (ver `docs/STOCK.md`). La carpeta destino se fija
con `PYFE_CARPETA_DATOS`, que `libs/rutas.py` lee antes que el directorio de
trabajo, y el script **se niega a correr** si esa carpeta resulta ser la de la
instalacion o la del usuario. Ademas copia la base a un `.bak` con hora antes
de escribir.

Sobre las fechas
----------------
Los movimientos que salen de un comprobante (venta, remito, compra) quedan con
la fecha de hoy, porque `aplica_factura`, `aplica_remito` y `aplica_compra` no
tienen parametro de fecha: escriben con la de hoy. Solo los movimientos
directos (el inventario inicial y el ajuste) se fechan atras, que es donde
tener una linea de tiempo ayuda a reconocer la pantalla.

Como usarlo
-----------
    python tools/sembrar_stock.py              # siembra el sandbox
    python tools/sembrar_stock.py --revisar    # solo muestra, no escribe
    python tools/sembrar_stock.py --rehacer    # borra lo sembrado y rehace
    python tools/sembrar_stock.py --carpeta X  # siembra otra carpeta
"""

import argparse
import os
import shutil
import sys
from datetime import date, timedelta

ORIGEN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ORIGEN)

SANDBOX_POR_DEFECTO = os.path.join(ORIGEN, "_sandbox_prueba")
MARCA = "SEMILLA-STOCK"


# --------------------------------------------------------------------------
# Los datos
# --------------------------------------------------------------------------
#
# Cada articulo declara sus movimientos y el stock que TIENE que quedar. La
# suma se comprueba contra el stock real, que es la suma de la tabla de
# movimientos: si un flujo estuviera roto, el numero no daria y el script avisa.
#
# Los movimientos son tuplas: (origen, cantidad, documento, dias_atras,
# observacion). La cantidad va con signo, como en la tabla.

CATALOGO = [
    # -- Controlados ----------------------------------------------------
    {
        "codbarra": "TORN-0001",
        "nombre": "Tornillo hexagonal 1/4 pulg con arandela",
        "concepto": "1", "controla": True, "minimo": 50,
        "preciopub": 1250.50, "costo": 485.00,
        "stock": 160, "estado": "OK",
        "movimientos": [
            ("INICIAL", 100, None, -25, "Conteo de apertura"),
            ("COMPRA", 50, "compra-1", 0, ""),
            ("COMPRA", 30, "compra-2", 0, ""),
            ("VENTA", -20, "venta-1", 0, ""),
        ],
    },
    {
        # El mas faltante: 85 contra un minimo de 200.
        "codbarra": "ARAND-114",
        "nombre": "Arandela plana M6 zincada",
        "concepto": "1", "controla": True, "minimo": 200,
        "preciopub": 85.00, "costo": 22.50,
        "stock": 85, "estado": "Falta",
        "movimientos": [
            ("INICIAL", 300, None, -25, "Conteo de apertura"),
            ("VENTA", -100, "venta-1", 0, ""),
            ("VENTA", -115, "venta-2", 0, ""),
        ],
    },
    {
        "codbarra": "TUE-880",
        "nombre": "Tubo de acero 3/4 pulg x 6 m",
        "concepto": "1", "controla": True, "minimo": 10,
        "preciopub": 84500.00, "costo": 61200.00,
        "stock": 4, "estado": "Falta",
        "movimientos": [
            ("INICIAL", 12, None, -25, "Conteo de apertura"),
            ("VENTA", -8, "venta-2", 0, ""),
        ],
    },
    {
        # Minimo 0 y stock 0: el unico que sale "Sin stock" y no "Falta". Con
        # minimo 0, `estado_de` no puede marcar falta, porque 0 es "no pediste
        # nada" y no "pediste cero".
        "codbarra": "CABLE-25",
        "nombre": "Cable NYY 2 x 2,5 mm",
        "concepto": "1", "controla": True, "minimo": 0,
        "preciopub": 5400.00, "costo": 3980.00,
        "stock": 0, "estado": "Sin stock",
        "movimientos": [
            ("INICIAL", 50, None, -25, "Conteo de apertura"),
            ("VENTA", -50, "venta-3", 0, ""),
        ],
    },
    {
        # El del remito. El remito saca 10 y la factura del remito NO saca mas.
        # Si esa regla se rompe, aca queda en -5 y el script lo dice.
        "codbarra": "PILA-AA",
        "nombre": "Pila AA alcalina blister x4",
        "concepto": "1", "controla": True, "minimo": 20,
        "preciopub": 4900.00, "costo": 3450.00,
        "stock": 5, "estado": "Falta",
        "movimientos": [
            ("INICIAL", 30, None, -25, "Conteo de apertura"),
            ("REMITO", -10, "remito-1", 0, ""),
            ("VENTA", -15, "venta-3", 0, ""),
        ],
    },
    {
        # Tiene una venta anulada: el stock queda igual que el conteo, pero el
        # historico muestra la anulacion y el motivo, que es lo que un operador
        # necesita ver para entender por que el stock no bajo.
        "codbarra": "LIJA-180",
        "nombre": "Lija al agua N 180",
        "concepto": "1", "controla": True, "minimo": 40,
        "preciopub": 1250.00, "costo": 640.00,
        "stock": 60, "estado": "OK",
        "movimientos": [
            ("INICIAL", 60, None, -25, "Conteo de apertura"),
            ("VENTA", -10, "venta-1", 0, ""),
            ("ANULA", 10, "venta-1", -11,
             "Se facturo de mas por error de tipeo"),
        ],
    },
    {
        "codbarra": "MASILLA-5",
        "nombre": "Masilla acrilica 5 kg",
        "concepto": "1", "controla": True, "minimo": 6,
        "preciopub": 18500.00, "costo": 13200.00,
        "stock": 1, "estado": "Falta",
        "movimientos": [
            ("INICIAL", 3, None, -25, "Conteo de apertura"),
            ("VENTA", -1, "venta-2", 0, ""),
            ("AJUSTE", -1, None, -4,
             "Rotura: dos baldes derramados en el estante del fondo"),
        ],
    },
    {
        # Negativo a proposito: hay 20 y se vendio 22. Es el estado que mas
        # confunde al operador, y sale de vender sin stock, no de un error de
        # calculo.
        "codbarra": "REMACHE-4",
        "nombre": "Remache popper 4 x 30 caja x100",
        "concepto": "1", "controla": True, "minimo": 5,
        "preciopub": 23500.00, "costo": 16900.00,
        "stock": -2, "estado": "Negativo",
        "movimientos": [
            ("INICIAL", 20, None, -25, "Conteo de apertura"),
            ("VENTA", -22, "venta-3", 0, ""),
        ],
    },
    {
        "codbarra": "CARTON-90",
        "nombre": "Carton corrugado 90 x 60",
        "concepto": "1", "controla": True, "minimo": 0,
        "preciopub": 1850.00, "costo": 950.00,
        "stock": 500, "estado": "OK",
        "movimientos": [
            ("INICIAL", 500, None, -25, "Conteo de apertura"),
        ],
    },
    {
        "codbarra": "ACEITE-3",
        "nombre": "Aceite de motor 3L",
        "concepto": "1", "controla": True, "minimo": 8,
        "preciopub": 32500.00, "costo": 24100.00,
        "stock": 10, "estado": "OK",
        "movimientos": [
            ("INICIAL", 5, None, -25, "Conteo de apertura"),
            ("COMPRA", 10, "compra-1", 0, ""),
            ("VENTA", -5, "venta-3", 0, ""),
        ],
    },

    # -- No controlados -------------------------------------------------
    {
        # Producto que no se inventaria: es un consumo interno. Es `concepto` 1,
        # asi que "Marcar productos" SI lo marca, y eso es lo correcto.
        "codbarra": "TINTA-01",
        "nombre": "Tinta universal negra 1L",
        "concepto": "1", "controla": False, "minimo": 0,
        "preciopub": 28900.00, "costo": 19700.00,
        "stock": 0, "estado": "Sin controlar",
        "movimientos": [],
    },
    {
        "codbarra": "SERV-INST",
        "nombre": "Mano de obra - instalacion",
        "concepto": "2", "controla": False, "minimo": 0,
        "preciopub": 485000.00, "costo": 0,
        "stock": 0, "estado": "Sin controlar",
        "movimientos": [],
    },
    {
        "codbarra": "SERV-VIS",
        "nombre": "Visita tecnica",
        "concepto": "2", "controla": False, "minimo": 0,
        "preciopub": 65000.00, "costo": 0,
        "stock": 0, "estado": "Sin controlar",
        "movimientos": [],
    },
]

DOCUMENTOS = {
    "compra-1": {"tipo": "compra", "numero": "0001-00000012"},
    "compra-2": {"tipo": "compra", "numero": "0001-00000013"},
    "venta-1": {"tipo": "venta", "numero": "0001-00000045"},
    "venta-2": {"tipo": "venta", "numero": "0001-00000046"},
    "venta-3": {"tipo": "venta", "numero": "0001-00000047"},
    "remito-1": {"tipo": "remito", "numero": 1},
}


# --------------------------------------------------------------------------
# Seguridad
# --------------------------------------------------------------------------

def _carpetas_prohibidas():
    """Donde este script no debe escribir nunca.

    La de la instalacion es la base de trabajo, con las ventas del cliente. La
    del usuario es `%LOCALAPPDATA%\\Asiento`, donde cae la app instalada. Las dos
    estan prohibidas aunque alguien pase `--carpeta` con esa ruta.
    """
    candidatas = [
        os.path.abspath(ORIGEN),
        os.path.abspath(os.path.join(os.environ.get("LOCALAPPDATA", ""),
                                     "Asiento")),
    ]
    return [p for p in candidatas if p and os.path.isdir(p)]


def verificar_destino(carpeta):
    destino = os.path.abspath(carpeta)
    prohibidas = {os.path.normcase(p) for p in _carpetas_prohibidas()}
    if os.path.normcase(destino) in prohibidas:
        raise SystemExit(
            "Este script no escribe en:\n  {}\n\n"
            "Ahi esta la base de trabajo. Para probar el modulo se usa el "
            "sandbox:\n  python tools/sembrar_stock.py\n\n"
            "Si de verdad queres tocar la base de trabajo, el stock se cambia "
            "desde Stock -> Ajustes de stock, que deja movimiento y es "
            "reversible.".format(destino))
    return destino


def respaldo(destino, nombre):
    """Copia la base antes de escribir, con fecha, para no pisar la anterior."""
    ruta = os.path.join(destino, nombre)
    if not os.path.isfile(ruta):
        return None
    sello = date.today().strftime("%Y%m%d")
    copia = "{}.antes-semilla-{}".format(ruta, sello)
    indice = 1
    while os.path.exists(copia):
        copia = "{}.antes-semilla-{}-{}".format(ruta, sello, indice)
        indice += 1
    shutil.copy2(ruta, copia)
    return copia


def _asegurar_ini(destino):
    """Crea el `sistema.ini` del sandbox si no esta.

    Sin esto el sandbox no arranca: `modelos/ModeloBase` decide entre sqlite y
    MySQL leyendo `[param] base`, y si la clave no esta entra por MySQL, pide
    un password interactivo que una herramienta no puede pedir, y falla.

    Se escribe lo minimo, con `homo = S` para que nada intente pegarle a
    homologacion, y `iniciosistema` apuntando al sandbox mismo para que la app
    abierta desde ahi lea esta configuracion y no la de la instalacion.

    `configurado = S` y una `empresa` de verdad estan para que la app NO abra
    el asistente de primer arranque: `es_primer_arranque()` mira el marcador y
    el nombre de empresa, y sin esto hay que atravesar el asistente cada vez
    que se quiere ver una pantalla de stock.
    """
    ruta = os.path.join(destino, "sistema.ini")
    if os.path.isfile(ruta):
        return False

    with open(ruta, "w", encoding="utf-8", newline="\r\n") as archivo:
        archivo.write(
            "; Creado por tools/sembrar_stock.py. Es el sandbox: no tiene\n"
            "; nada que ver con la configuracion de la instalacion.\n"
            "[param]\n"
            "iniciosistema = {}/\n"
            "nombre_sistema = Asiento (PRUEBA)\n"
            "empresa = FERRETERIA PRUEBA\n"
            "configurado = S\n"
            "basedatos = \n"
            "usuario = \n"
            "host = localhost\n"
            "homo = S\n"
            "base = sqlite\n"
            "email_contador = contador@example.com\n".format(destino))
    print("Creado:", os.path.relpath(ruta, ORIGEN))
    return True


# --------------------------------------------------------------------------
# Siembra
# --------------------------------------------------------------------------

def _asegurar_maestros():
    """Los datos de cabecera, creados si faltan y nunca pisados.

    El sandbox ya viene con la migracion que carga tipos de comprobante,
    impuestos, formas de pago y unidades, asi que casi todo esta. Lo que se
    crea aca es lo que la app no genera sola: un cliente, un proveedor y un
    cajero con nombre reconocible, para que la pantalla no muestre "CONSUMIDOR
    FINAL" en todas las facturas de prueba.

    Cada uno se busca antes de crear, y se crea solo si no esta: correr el
    script dos veces no puede duplicar el cliente.
    """
    from modelos.Cajeros import Cajero
    from modelos.Clientes import Cliente
    from modelos.Formaspago import Formapago
    from modelos.Grupos import Grupo
    from modelos.Impuestos import Impuesto
    from modelos.Localidades import Localidad
    from modelos.Proveedores import Proveedor
    from modelos.Tipocomprobantes import TipoComprobante
    from modelos.Tipodoc import Tipodoc
    from modelos.Tiporesp import Tiporesp
    from modelos.Tipoiva import Tipoiva
    from modelos.Unidades import Unidad

    faltantes = []

    # -- Lo que la migracion ya trae ------------------------------------
    # Se busca por codigo y no se crea nada nuevo: la migracion carga la lista
    # real de tipos de comprobante de ARCA, y crear uno con un codigo que ya
    # existe revienta por la restriccion UNIQUE. Ademas, los codigos tienen
    # numero asignado por ARCA y no se inventan.
    tipoiva = Tipoiva.get_or_none(Tipoiva.codigo == "01")
    if tipoiva is None:
        tipoiva = Tipoiva.create(codigo="01", descrip="IVA GENERAL", iva=21)

    tc_factura = TipoComprobante.get_or_none(TipoComprobante.codigo == 6)
    if tc_factura is None:
        tc_factura = TipoComprobante.create(
            codigo=6, nombre="FACTURA B", abreviatura="B", lado="D",
            exporta=0, ultcomp=100, letra="B")

    tc_proforma = TipoComprobante.get_or_none(TipoComprobante.codigo == 92)
    if tc_proforma is None:
        tc_proforma = TipoComprobante.create(
            codigo=92, nombre="Proforma", abreviatura="PRO", lado="",
            exporta=0, ultcomp=0, letra="X")

    # La compra se registra con FACTURA A (codigo 1). El filtro por `lado` no
    # sirve: en esta tabla `lado` es el del comprobante de VENTA, no el del
    # comprobante del proveedor.
    tc_compra = TipoComprobante.get_or_none(TipoComprobante.codigo == 1)
    if tc_compra is None:
        # La migracion lo carga de los CSV de datos. Si no esta, se crea con los
        # mismos datos: es una fila maestra, no un dato del cliente, y sin ella
        # no se puede registrar una compra.
        tc_compra = TipoComprobante.create(
            codigo=1, nombre="FACTURA A", abreviatura="A", lado="D",
            exporta=0, ultcomp=100, letra="A")

    formapago = Formapago.get_or_none(Formapago.idformapago == 1)
    if formapago is None:
        formapago = Formapago.create(idformapago=1, detalle="EFECTIVO")

    impuesto = Impuesto.get_or_none(Impuesto.idimpuesto == 1)
    if impuesto is None:
        impuesto = Impuesto.create(idimpuesto=1, detalle="SIN PERCEPCION",
                                   porcentaje=0, minimo=0)

    unidad = Unidad.get_or_none(Unidad.unidad == "UN")
    if unidad is None:
        unidad = Unidad.create(unidad="UN", descripcion="UNIDAD")

    # CONSUMIDOR FINAL es el id 3 en esta instalacion. Se busca por nombre y no
    # por id fijo, porque el id depende de que datos se cargaron.
    tiporesp = (Tiporesp.get_or_none(Tiporesp.nombre == "CONSUMIDOR FINAL") or
                Tiporesp.get_or_none(Tiporesp.idtiporesp == 1))
    if tiporesp is None:
        tiporesp = Tiporesp.create(idtiporesp=1, nombre="CONSUMIDOR FINAL",
                                   factura=6, notacredito=8, notadebito=7,
                                   condicion_iva_receptor_id=5)

    # -- Lo que la app no genera sola -----------------------------------
    # Cliente, proveedor, cajero y grupo con nombre reconocible: si no, todas
    # las facturas de prueba salen con "CONSUMIDOR FINAL" y no se distingue una
    # de otra. Cada uno se busca antes de crear, asi que correr el script dos
    # veces no duplica nada.
    grupo = Grupo.get_or_none(Grupo.nombre == "FERRETERIA")
    if grupo is None:
        faltantes.append("grupo FERRETERIA")
        grupo = Grupo.create(nombre="FERRETERIA", impuesto=impuesto)

    localidad = Localidad.get_or_none(Localidad.nombre == "Rosario")
    if localidad is None:
        faltantes.append("localidad Rosario")
        localidad = Localidad.create(nombre="Rosario",
                                     provincia="Santa Fe",
                                     nacion="Argentina")

    tipodoc = Tipodoc.get_or_none(Tipodoc.codigo == 96)
    if tipodoc is None:
        tipodoc = Tipodoc.get_or_none(Tipodoc.codigo == 0)

    cliente = Cliente.get_or_none(Cliente.dni == 203040506)
    if cliente is None:
        faltantes.append("cliente CORRALON LA BAHIA")
        cliente = Cliente.create(nombre="CORRALON LA BAHIA",
                                 domicilio="AV. SAN MARTIN 1245",
                                 localidad=localidad, cuit="", dni=203040506,
                                 tipodocu=tipodoc, tiporesp=tiporesp,
                                 formapago=formapago, percepcion=impuesto)

    proveedor = Proveedor.get_or_none(
        Proveedor.nombre == "SUMINISTROS DEL LITORAL")
    if proveedor is None:
        faltantes.append("proveedor SUMINISTROS DEL LITORAL")
        proveedor = Proveedor.create(nombre="SUMINISTROS DEL LITORAL",
                                     domicilio="RUTA 9 KM 306",
                                     cuit="30123456789",
                                     tiporesp=tiporesp,
                                     idlocalidad=localidad)

    cajero = Cajero.get_or_none(Cajero.nombre == "CAJERO PRUEBA")
    if cajero is None:
        faltantes.append("cajero")
        cajero = Cajero.create(nombre="CAJERO PRUEBA")

    return {
        "tipoiva": tipoiva, "tc_factura": tc_factura,
        "tc_proforma": tc_proforma, "tc_compra": tc_compra,
        "formapago": formapago, "grupo": grupo, "unidad": unidad,
        "localidad": localidad, "tipodoc": tipodoc, "tiporesp": tiporesp,
        "cliente": cliente, "proveedor": proveedor, "cajero": cajero,
        "creados_a_mano": faltantes,
    }


def sembrar():
    """Escribe el catalogo y los movimientos.

    Los movimientos se escriben con las funciones de `libs.stock` del flujo que
    los produce (`aplica_factura`, `aplica_remito`, `aplica_compra`) y no con un
    INSERT. Es la diferencia entre comprobar que el modulo anda y comprobar
    que un INSERT anda: la regla del remito vive adentro de `aplica_factura`, y
    un seed que la esquivara no la estaria probando.
    """
    from libs import stock
    from modelos.Articulos import Articulo
    from modelos.CabFacProv import CabFactProv
    from modelos.Cabfact import Cabfact
    from modelos.MovStock import MovStock
    from modelos.Remitos import DetalleRemito, Remito

    hoy = date.today()

    def hace(dias):
        return hoy - timedelta(days=dias)

    m = _asegurar_maestros()

    # -- Articulos -------------------------------------------------------
    print("Articulos")
    por_codigo = {}
    for fila in CATALOGO:
        articulo = Articulo.get_or_none(
            Articulo.codbarra == fila["codbarra"])
        if articulo is None:
            articulo = Articulo.create(
                nombre=fila["nombre"],
                nombreticket=fila["nombre"][:30],
                codbarra=fila["codbarra"],
                concepto=fila["concepto"],
                controlastock=fila["controla"],
                stockminimo=fila["minimo"],
                preciopub=fila["preciopub"],
                costo=fila["costo"],
                unidad=m["unidad"].unidad,
                grupo=m["grupo"],
                provppal=m["proveedor"],
                tipoiva=m["tipoiva"].codigo,
            )
        por_codigo[fila["codbarra"]] = articulo
        print("  {:<12} {:<38} concepto={} controla={} minimo={}".format(
            fila["codbarra"], fila["nombre"][:38], fila["concepto"],
            "si" if fila["controla"] else "no", fila["minimo"]))

    # -- Documentos ------------------------------------------------------
    def cabecera_factura(numero, idremito=None):
        # `tipoiva` de Cabfact es un FK a Tiporesp, no a Tipoiva. Es raro, pero
        # es como esta armado el modelo y hay que respetarlo.
        return Cabfact.create(
            fecha=hoy, numero=str(numero),
            nombre=m["cliente"].nombre, domicilio=m["cliente"].domicilio,
            tipocomp=m["tc_factura"], cliente=m["cliente"],
            tipoiva=m["tiporesp"], formapago=m["formapago"],
            cajero=m["cajero"], cae="", concepto="1",
            total=0, neto=0, iva=0, idremito=idremito)

    ids = {}
    print("Documentos")
    for nombre, datos in DOCUMENTOS.items():
        if datos["tipo"] == "compra":
            cabecera = CabFactProv.create(
                fecha=hoy, fechaem=hoy, idproveedor=m["proveedor"],
                tipocomp=m["tc_compra"], numero=datos["numero"])
            ids[nombre] = ("compra", cabecera.idpcabfact)
        elif datos["tipo"] == "venta":
            cabecera = cabecera_factura(datos["numero"])
            ids[nombre] = ("venta", cabecera.idcabfact)
        else:
            ids[nombre] = ("remito", None)
        print("  {:<12} {:<8} {}".format(nombre, datos["tipo"],
                                         datos["numero"]))

    # El remito y su factura. La factura lleva `idremito`, y por eso NO tiene
    # que descontar: esa mercaderia ya salio con el remito.
    remito = Remito.create(
        cliente=m["cliente"], fecha=hoy, ptovta=1, numero=1,
        forma_pago=m["formapago"], tipo_comprobante=m["tc_proforma"],
        estado="P", observaciones="Remito de la factura siguiente")

    factura_del_remito = cabecera_factura("0001-00000048",
                                          idremito=remito.idremito)
    print("  factura del remito lleva idremito={}".format(remito.idremito))

    # -- Movimientos -----------------------------------------------------
    # Se juntan por documento y se aplican con la funcion del flujo, no renglon
    # por renglon: `aplica_factura` recibe la lista completa de una vez, como
    # la recibe el emisor de la app.
    por_comprobante = {}
    directos = []
    anulaciones = []

    for fila in CATALOGO:
        articulo = por_codigo[fila["codbarra"]]
        for origen, cantidad, documento, dias, observacion in fila["movimientos"]:
            if origen in ("INICIAL", "AJUSTE"):
                directos.append((articulo, origen, cantidad, dias,
                                  observacion))
            elif origen == "ANULA":
                anulaciones.append((articulo, documento, dias, observacion))
            else:
                clave = (documento, origen)
                por_comprobante.setdefault(clave, []).append(
                    (articulo, abs(cantidad)))

    print("Movimientos")
    for (documento, origen), filas in sorted(por_comprobante.items(),
                                              key=lambda x: str(x[0])):
        _tipo_doc, id_doc = ids[documento]
        detalles = [(a.idarticulo, c) for a, c in filas]

        if origen == "VENTA":
            stock.aplica_factura(detalles, id_doc, lado="D",
                                 origen=stock.ORIGEN_VENTA)
            rotulo = "Factura {}".format(DOCUMENTOS[documento]["numero"])
        elif origen == "REMITO":
            DetalleRemito.insert_many([
                {"remito": remito.idremito, "producto": a.idarticulo,
                 "detalle": a.nombre, "cantidad": c,
                 "precio": a.preciopub, "tipo_iva": m["tipoiva"].codigo}
                for a, c in filas]).execute()
            stock.aplica_remito(detalles, remito.idremito)
            rotulo = "Remito {}".format(DOCUMENTOS[documento]["numero"])
        else:
            stock.aplica_compra(detalles, id_doc)
            rotulo = "Compra {}".format(DOCUMENTOS[documento]["numero"])

        print("  {:<12} {:<8} {:<18} {}".format(
            documento, origen, rotulo,
            " ".join(a.codbarra for a, _c in filas)))

    for articulo, origen, cantidad, dias, observacion in directos:
        stock.registra_ajuste(
            articulo.idarticulo, cantidad,
            observacion="{} - {}".format(MARCA, observacion),
            origen=(stock.ORIGEN_INICIAL if origen == "INICIAL"
                    else stock.ORIGEN_AJUSTE),
            fecha=hace(dias))
        print("  {:<12} {:<8} {:<18} {}".format(
            "-", origen, "Conteo" if origen == "INICIAL" else "Ajuste",
            articulo.codbarra))

    # La factura del remito no tiene que escribir NADA. Se comprueba aca y no
    # solo al final por el stock: si escribiera, el movimiento existiria aunque
    # el total por casualidad diera.
    escritos = stock.aplica_factura(
        [(por_codigo["PILA-AA"].idarticulo, 10)],
        factura_del_remito.idcabfact, idremito=remito.idremito, lado="D")
    if escritos:
        raise SystemExit(
            "La factura del remito escribio {} movimientos. La regla de no "
            "volver a descontar esta rota y el remito se esta cobrando dos "
            "veces.".format(escritos))
    print("  factura del remito: 0 movimientos (correcto, el remito ya "
          "desconto)")

    for articulo, documento, dias, observacion in anulaciones:
        _tipo_doc, id_doc = ids[documento]
        original = (MovStock
                    .select()
                    .where((MovStock.idarticulo == articulo.idarticulo) &
                           (MovStock.idcabfact == id_doc))
                    .where(MovStock.anula.is_null(True))
                    .first())
        if original is None:
            raise SystemExit(
                "No encontre el movimiento a anular de {} en {}".format(
                    articulo.codbarra, documento))
        contrario = stock.anula(
            original,
            observacion="{} - {}".format(MARCA, observacion))
        if contrario is not None:
            # `anula` copia la fecha del original; se corren las dos para que
            # la anulacion quede un dia despues de la venta que corrige.
            MovStock.update(fecha=hace(dias)).where(
                MovStock.idmovstock == contrario.idmovstock).execute()
            MovStock.update(fecha=hace(dias)).where(
                MovStock.idmovstock == original.idmovstock).execute()
        print("  {:<12} {:<8} {:<18} {}".format(
            documento, "ANULA", "Anulacion", articulo.codbarra))

    return {"maestros": m, "por_codigo": por_codigo, "ids": ids,
            "remito": remito, "factura_del_remito": factura_del_remito}


# --------------------------------------------------------------------------
# Verificacion
# --------------------------------------------------------------------------

def verificar(silencioso=False):
    """Relee el stock y lo compara con lo que el catalogo declara.

    Devuelve la lista de diferencias, vacia si todo dio. `silencioso` existe
    para que se pueda llamar desde un test sin ensuciar la salida.
    """
    from libs import stock
    from controladores.Stock import estado_de
    from modelos.Articulos import Articulo

    if not silencioso:
        print()
        print("Stock que va a ver el operador")
        print("  {:<12} {:>8} {:>7} {:>9}  {}".format(
            "codigo", "stock", "minimo", "esperado", "estado"))

    diferencias = []
    for fila in CATALOGO:
        articulo = Articulo.get_or_none(
            Articulo.codbarra == fila["codbarra"])
        if articulo is None:
            diferencias.append(
                "{}: no quedo cargado".format(fila["codbarra"]))
            continue

        hay = stock.stock_de(articulo.idarticulo)
        estado = estado_de(articulo, hay)

        marca = ""
        if hay != fila["stock"]:
            marca = "  <- se esperaba {}".format(fila["stock"])
            diferencias.append(
                "{}: stock {} y se esperaba {}{}".format(
                    fila["codbarra"], hay, fila["stock"], marca))
        if estado != fila["estado"]:
            marca = "  <- se esperaba '{}'".format(fila["estado"])
            diferencias.append(
                "{}: estado '{}' y se esperaba '{}'".format(
                    fila["codbarra"], estado, fila["estado"]))

        if not silencioso:
            print("  {:<12} {:>8} {:>7} {:>9}  {}{}".format(
                fila["codbarra"], hay, fila["minimo"], fila["stock"], estado,
                marca))

    return diferencias


def resumen_faltantes():
    """Lo que devuelve `stock.faltantes()`: lo que esta por debajo del minimo.

    Ojo con una confusion que es facil: esto NO es lo mismo que la casilla
    "Solo faltantes" de la pantalla de Stock. La casilla mira el ESTADO y mete
    tambien "Sin stock"; esta mira el MINIMO, y un producto con minimo 0 no
    aparece nunca (0 es "no pediste nada").

    Y los negativos si aparecen, que es lo correcto: un producto en -2 esta
    siete unidades por debajo de un minimo de 5.
    """
    from libs import stock

    faltantes = stock.faltantes()
    print()
    print("Los que estan por debajo del minimo (stock.faltantes())")
    if not faltantes:
        print("  (ninguno)")
        return []
    for fila in faltantes:
        print("  {:<12} hay {:<5} minimo {:<5} faltan {}".format(
            fila["articulo"].codbarra, fila["stock"], fila["minimo"],
            fila["faltante"]))
    return [f["articulo"].codbarra for f in faltantes]


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _deshacer():
    """Deja la base como estaba, para poder sembrar de nuevo.

    Borra por ARTICULO y no por la marca de la observacion. Eso antes estaba
    mal, y se noto: los movimientos que escriben `aplica_factura`,
    `aplica_compra` y `aplica_remito` van con la observacion vacia, porque esas
    funciones no la toman. Solo los movimientos directos (el conteo inicial y el
    ajuste) llevan la marca.

    Con el filtro por marca, `--rehacer` borraba la mitad de lo sembrado y el
    seed siguiente sumaba encima: el stock quedaba exactamente al doble. El
    propio script avisaba "se esperaba 160" en nueve filas, pero `--revisar`
    salia con codigo 0 y el aviso pasaba inadvertido.

    Los documentos (facturas, remito) tambien se van, y se reconocen por el
    cliente del seed: sin eso el sandbox acumula comprobantes de prueba para
    siempre y `ultcomp` queda corrido.

    Va todo con los modelos y no con SQL a mano, por una razon concreta: los
    nombres de columna no son los que uno adivina. En esta base
    `detalleremito` usa `producto_id` y `remito_id`, y `remito` usa
    `cliente_id`; solo `cabfact` tiene `idCliente`, porque el modelo lo declara
    asi. Un `delete from detalleremito where producto = ?` falla y, peor,
    un nombre bien escrito a mano en otra base borra otra cosa.

    En la app un movimiento no se borra nunca. Esta es una base de prueba y
    `--rehacer` tiene que poder arrancar de cero.
    """
    from modelos.Articulos import Articulo
    from modelos.CabFacProv import CabFactProv
    from modelos.Cabfact import Cabfact
    from modelos.Clientes import Cliente
    from modelos.Detfact import Detfact
    from modelos.MovStock import MovStock
    from modelos.Remitos import DetalleRemito, Remito

    codigos = [fila["codbarra"] for fila in CATALOGO]
    articulos = list(
        Articulo.select().where(Articulo.codbarra.in_(codigos)))
    ids = [a.idarticulo for a in articulos]

    total = 0

    if ids:
        # Primero los hijos: `movstock` y `detalleremito` apuntan a los
        # articulos y al remito, y sqlite no siempre hace cumplir eso.
        total += MovStock.delete().where(
            MovStock.idarticulo.in_(ids)).execute()
        total += Detfact.delete().where(
            Detfact.idarticulo.in_(ids)).execute()

    cliente = Cliente.get_or_none(Cliente.dni == 203040506)
    if cliente is not None:
        remitos = [r.idremito for r in Remito.select().where(
            Remito.cliente == cliente)]
        if remitos:
            total += DetalleRemito.delete().where(
                DetalleRemito.remito.in_(remitos)).execute()
            total += Remito.delete().where(
                Remito.idremito.in_(remitos)).execute()

        total += Cabfact.delete().where(
            Cabfact.cliente == cliente).execute()

        numeros_compra = [d["numero"] for d in DOCUMENTOS.values()
                          if d["tipo"] == "compra"]
        if numeros_compra:
            total += CabFactProv.delete().where(
                CabFactProv.numero.in_(numeros_compra)).execute()

    if ids:
        # El vinculo de anulacion: si se borran los dos movimientos, los dos
        # `anula` quedan apuntando a filas que no existen.
        MovStock.update(anula=None).where(
            MovStock.anula.is_null(False)).execute()
        total += Articulo.delete().where(
            Articulo.codbarra.in_(codigos)).execute()

    print("  {} articulo(s) y {} fila(s) de la siembra borrados".format(
        len(ids), total))


def main():
    analizador = argparse.ArgumentParser(
        description="Siembra datos de stock para probar el modulo a mano.")
    analizador.add_argument(
        "--carpeta", default=SANDBOX_POR_DEFECTO,
        help="carpeta de datos a sembrar (default: el sandbox)")
    analizador.add_argument(
        "--revisar", action="store_true",
        help="solo muestra el estado actual, no escribe nada")
    analizador.add_argument(
        "--rehacer", action="store_true",
        help="borra lo sembrado antes de sembrar de nuevo")
    argumentos = analizador.parse_args()

    destino = verificar_destino(argumentos.carpeta)
    if not os.path.isdir(destino):
        raise SystemExit(
            "No existe '{}'.\nArmalo primero con:\n"
            "  python tools/armar_sandbox.py".format(destino))

    # Antes de nada: sin sistema.ini, `modelos.ModeloBase` entra por MySQL y
    # falla pidiendo un password que aca no hay a quien pedir.
    _asegurar_ini(destino)

    os.environ["PYFE_CARPETA_DATOS"] = destino
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])

    from libs.rutas import carpeta_datos, ruta_base
    base = ruta_base("sistema.db")
    print("Carpeta de datos:", carpeta_datos())
    print("Base:", base)

    from modelos.ModeloBase import db

    if argumentos.revisar:
        if not os.path.isfile(base):
            raise SystemExit("No hay base todavia en {}".format(base))
        db.connect(reuse_if_open=True)
        diferencias = verificar()
        resumen_faltantes()
        db.close()
        print()
        if diferencias:
            # Esto antes salia con codigo 0 y por ahi se escapo un seed
            # sembrado dos veces: los numeros daban el doble, el aviso se
            # imprimia, y el que lo leia no se enteraba. Un chequeo que
            # encuentra una diferencia y no la hace pasar es un chequeo
            # que no le sirve al que lo pide.
            print("DIFERENCIAS (lo sembrado no es lo que el catalogo declara):")
            for diferencia in diferencias:
                print("  -", diferencia)
            print()
            print("Lo mas probable es que este sembrado dos veces. Corré:")
            print("  python tools/sembrar_stock.py --rehacer")
            return 1
        print("OK: el stock de la base es el que el catalogo declara.")
        return 0

    copia = respaldo(destino, "sistema.db")
    if copia:
        print("Respaldo:", os.path.relpath(copia, ORIGEN))

    # La migracion va antes: el seed escribe en 'movstock' y en tablas que en
    # un sandbox viejo todavia no existen.
    print("Migrando la base...")
    db.connect(reuse_if_open=True)
    from controladores.MigracionBaseDatos import MigracionBaseDatos
    MigracionBaseDatos().Migrar()

    if argumentos.rehacer:
        print("Deshaciendo la siembra anterior...")
        _deshacer()

    sembrar()

    diferencias = verificar()
    resumen_faltantes()

    db.close()

    print()
    if diferencias:
        print("DIFERENCIAS (algo del modulo no dio lo esperado):")
        for diferencia in diferencias:
            print("  -", diferencia)
        return 1

    print("OK: el stock de la base es el que el catalogo declara.")
    return 0


if __name__ == "__main__":
    sys.exit(main())