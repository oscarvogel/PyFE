# coding=utf-8
"""Prueba 2: emitir una factura de HOMOLOGACION de verdad.

No reimplementa nada: usa el mismo `crear_factura_wsfe` de
controladores/Facturas.py que usa la pantalla de emision. Si esto autoriza,
el camino fiscal de la app esta bien; si no, el codigo de observacion de ARCA
dice exactamente que sobra o que falta.

Que NO se toque nada real
-------------------------
El proceso corre dentro de _prueba_facturacion/, donde sistema.ini tiene
homo = S. En homologacion las facturas no existen para ARCA y no le facturan a
nadie. El sistema.ini del repo, que esta en produccion, no se lee.

Uso
---
    python tools/probar_emision.py
    python tools/probar_emision.py --tipo 6 --pto 1   # probar Factura B
"""
from __future__ import print_function

import argparse
import datetime
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTORNO = os.path.join(RAIZ, "_prueba_facturacion")

if not os.path.isdir(ENTORNO):
    print("El entorno de prueba no existe. Corré primero:")
    print("    python tools/armar_prueba_facturacion.py")
    sys.exit(1)

os.chdir(ENTORNO)
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

# Los argumentos se leen ANTES de tocar sys.argv. LeerIni() usa
# argparse.parse_known_args() sobre sys.argv, y si se trunca antes, esta
# herramienta se queda sin sus propias opciones y emite siempre el importe
# por defecto sin avisar.
p = argparse.ArgumentParser()
p.add_argument("--tipo", type=int, default=6,
               help="tipo de comprobante. Para este CUIT: 6 = Factura B, "
                    "1 = Factura A. El 82 (Tique) NO esta habilitado.")
p.add_argument("--pto", type=int, default=0, help="punto de venta; 0 = el del sistema.ini")
p.add_argument("--numero", type=int, default=0, help="numero a emitir; 0 = el siguiente")
p.add_argument("--total", default="4500.00", help="importe total")
p.add_argument("--nombre", default="CLIENTE DE PRUEBA", help="nombre del cliente")
p.add_argument("--doc", default="11111111", help="documento del cliente")
p.add_argument("--tipo-doc", type=int, default=96, help="96 = DNI, 80 = CUIT, 99 = sin identificar")
args = p.parse_args()

sys.argv = [sys.argv[0]]

# Varios modulos arman widgets al importarse, asi que hace falta una
# QApplication antes de importarlos. offscreen porque esta prueba no dibuja
# nada: habla con ARCA, no con la pantalla.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt5.QtWidgets import QApplication  # noqa: E402
APLICACION = QApplication.instance() or QApplication(sys.argv)

from libs.Utiles import LeerIni  # noqa: E402
from libs.instalacion import cuit_emisor  # noqa: E402
from controladores.Facturas import FacturaController  # noqa: E402
from controladores.FE import FEv1  # noqa: E402
from libs.Utiles import DeCodifica  # noqa: E402


def linea(titulo):
    print("")
    print("=== {} ===".format(titulo))


modo = "HOMOLOGACION" if LeerIni("homo") == "S" else "PRODUCCION"
if LeerIni("homo") != "S":
    print("CORTANDO: esto solo emite en homologacion. El sistema.ini leido "
          "tiene homo = {}, y en produccion eso factura de verdad.".format(modo))
    sys.exit(1)

cuit = cuit_emisor()
pto = args.pto or int(LeerIni(clave="pto_vta", key="WSFEv1") or 1)
cat_iva = int(LeerIni(clave="cat_iva", key="WSFEv1") or 6)

linea("QUE SE VA A EMITIR")
print("modo            : {}  (no factura a nadie)".format(modo))
print("CUIT emisor     : {}".format(cuit))
print("comprobante     : {}".format(args.tipo))
print("punto de venta  : {}".format(pto))
print("categoria IVA   : {}".format(cat_iva))
print("cliente         : {} ({})".format(args.nombre, args.doc))
print("importe total   : {}".format(args.total))

wsfe = FEv1()

def _base_tiene_tablas():
    """Existe la base CON contenido.

    No alcanza con mirar el archivo: peewee crea el .db vacío en cuanto se
    conecta, asi que un intento anterior fallido deja un archivo de cero bytes
    que hace creer que la base ya esta.
    """
    if not os.path.isfile("sistema.db"):
        return False
    import sqlite3
    conexion = sqlite3.connect("sistema.db")
    try:
        cur = conexion.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        return len(cur.fetchall()) > 0
    finally:
        conexion.close()


linea("0. BASE DE DATOS")
# La app crea la base y siembra los maestros la primera vez que arranca. Esta
# prueba la usa de verdad, asi que se crea igual: si el camino de datos
# estuviera roto, el fallo tiene que aparecer aca y no enmascarado.
if not _base_tiene_tablas():
    print("no hay base con contenido: se crea con la app")
    # Mismo orden que controladores/Main.py::iniciar (CreaTablas -> Migraciones).
    # Al reves, la migracion revienta con "no such table: paramsist", porque
    # paramsist es la que guarda la version de la base.
    from modelos.Clientes import FichaCliente
    from modelos.ParametrosSistema import ParamSist
    from controladores.MigracionBaseDatos import MigracionBaseDatos
    ParamSist.create_table(safe=True)
    FichaCliente.create_table()
    MigracionBaseDatos().Migrar()
    print("base creada")
else:
    print("sistema.db ya existe")

from modelos.Clientes import Cliente  # noqa: E402

# Cliente real de la base, no un stub: crear_factura_wsfe lee la condicion de
# IVA del receptor desde ahi, y un objeto falso taparia justo ese error.
controlador_cliente = Cliente.get_or_none(Cliente.idcliente == 1)
if controlador_cliente is None:
    print("ERROR: la base no tiene el cliente de prueba (idcliente 1).")
    print("       Los datos maestros no se sembraron; revisa la carpeta data/.")
    sys.exit(1)
cliente = controlador_cliente
print("cliente de la base: {} (id {})".format(cliente.nombre, cliente.idcliente))
print("tipo de documento : {}".format(cliente.tipodocu))
print("tipo de resp.    : {} (id {})".format(
    cliente.tiporesp.nombre, cliente.tiporesp.idtiporesp))
print("condicion IVA rec.: {}".format(cliente.tiporesp.condicion_iva_receptor_id))

linea("1. AUTENTICAR")
try:
    ticket = wsfe.Autenticar()
except Exception as exc:
    print("FALLO la autenticacion: {}".format(exc))
    sys.exit(1)
if not ticket:
    print("FALLO: ARCA no devolvio ticket de acceso.")
    print("       {}".format(DeCodifica(getattr(wsfe, "ErrMsg", ""))))
    sys.exit(1)
print("OK ticket de acceso")
wsfe.SetTicketAcceso(ta_string=ticket)
wsfe.Cuit = cuit

linea("2. CONECTAR AL SERVICIO DE FACTURACION")
try:
    ok = wsfe.Conectar("")
except Exception as exc:
    print("FALLO la conexion: {}".format(exc))
    sys.exit(1)
if not ok:
    print("FALLO: no se pudo conectar. {}".format(DeCodifica(wsfe.ErrMsg)))
    sys.exit(1)
print("OK conexion establecida")

linea("3. ARMAR Y ENVIAR LA FACTURA")

if args.numero:
    numero = args.numero
    print("numero pedido a mano: {}".format(numero))
else:
    # Mismo criterio que la pantalla de emision (ObtieneNumeroFactura): se le
    # pregunta a ARCA cual fue el ultimo comprobante y se usa el siguiente.
    # Probar con un numero al azar devuelve 10016 y no dice nada util.
    ultimo = FEv1().UltimoComprobante(tipo=args.tipo, ptovta=pto)
    try:
        ultimo = int(ultimo)
    except (TypeError, ValueError):
        ultimo = 0
    numero = ultimo + 1
    print("ultimo autorizado por ARCA: {}  ->  se emite el {}".format(ultimo, numero))

hoy = datetime.date.today().strftime("%Y%m%d")
total = args.total

# Misma cuenta que hace CreaFE: si el emisor es responsable inscripto, el neto
# se separa del IVA y hay que mandar el detalle de alicuotas. Si no, el total
# ya lo incluye.
ALICUOTA = 21.0
if cat_iva == 1:
    neto = str(round(float(total) / (1 + ALICUOTA / 100), 2))
    iva = str(round(float(total) - float(neto), 2))
else:
    neto = total
    iva = "0.00"

# Se usa el metodo de la app, no una copia: esto es lo que ejecuta la pantalla
# de emision cuando apretás "Emitir".
controlador = object.__new__(FacturaController)
controlador.cliente = cliente

print("total {} -> neto {} + IVA {}".format(total, neto, iva))
try:
    ok = controlador.crear_factura_wsfe(
        wsfe,
        concepto=1,
        tipo_doc=cliente.tipodocu or args.tipo_doc,
        nro_doc=str(cliente.dni or cliente.cuit or args.doc).replace("-", ""),
        tipo_cbte=args.tipo,
        punto_vta=pto,
        cbt_desde=numero,
        cbt_hasta=numero,
        imp_total=total,
        imp_tot_conc="0.00",
        imp_neto=neto,
        imp_iva=iva,
        imp_trib="0.00",
        imp_op_ex="0.00",
        fecha_cbte=hoy,
        fecha_venc_pago="",
        fecha_serv_desde="",
        fecha_serv_hasta="",
        moneda_id="PES",
        moneda_ctz="1.000",
    )
except Exception as exc:
    print("FALLO al armar la factura: {}".format(exc))
    sys.exit(1)

if not ok:
    print("FALLO al armar: {}".format(DeCodifica(getattr(wsfe, "ErrMsg", ""))))
    sys.exit(1)
print("OK factura armada y enviada")

# El detalle de alicuotas. Para responsable inscripto sin esto ARCA rechaza
# la factura: es el mismo bloque que corre CreaFE antes de pedir el CAE.
if cat_iva == 1 and float(iva) > 0:
    codigo_alicuota = FEv1.TASA_IVA[str(float(ALICUOTA))]
    print("agregando IVA: codigo {} base {} importe {}".format(
        codigo_alicuota, neto, iva))
    wsfe.AgregarIva(codigo_alicuota, round(float(neto), 2), round(float(iva), 2))

linea("4. PEDIR EL CAE")
cae = wsfe.CAESolicitar()

if wsfe.ErrMsg:
    print("ERROR de ARCA: {}".format(DeCodifica(wsfe.ErrMsg)))
    sys.exit(1)

if wsfe.Resultado == "R":
    print("RECHAZADA")
    print("codigo de observacion : {}".format(wsfe.CodObservacion))
    print("motivo               : {}".format(DeCodifica(wsfe.Obs)))
    print("")
    print("Las observaciones mas comunes:")
    print("  10016 - el numero de comprobante ya se uso en ese punto de venta")
    print("  10048 - el comprobante tiene que ir en una venta a nombre de un")
    print("           responsable inscripto (probar con --tipo 1 o 6)")
    print("  10011 - falta algun dato obligatorio del comprobante")
    sys.exit(1)

linea("5. RESULTADO")
print("RESULTADO   : {}".format(wsfe.Resultado))
print("CAE         : {}".format(cae))
print("vence CAE   : {}".format(wsfe.Vencimiento))
print("numero      : {} - {} punto de venta {}".format(numero, numero, pto))
print("")
print("AUTORIZADA. En homologacion no existe para AFIP, asi que se puede")
print("repetir sin consequence. Para probar otro numero, pasar --numero.")
