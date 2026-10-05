"""Prueba del stock contra MySQL de verdad (el de WSL).

Por que hace falta esto
----------------------
SQLite y MySQL no se parecen en las tres cosas que el stock usa:

1. `MigrarVersion9` agrega claves foraneas con `_clave_foranea`, que en sqlite
   es un no-op con un comentario y en MySQL hace un ALTER TABLE de verdad. La
   migracion **nunca se ejecuto contra MySQL** si solo se prueba en sqlite.
2. `BitBooleanField` declara `field_type = 'Bit'`. En MySQL BIT(1) devuelve
   `b'\\x01'`, en sqlite un entero. El `python_value` lo normaliza, pero
   conviene verlo funcionando.
3. `SUM` de un DECIMAL devuelve float en sqlite y DECIMAL exacto en MySQL, que
   es justo el ruido que `stock_de` viene a corregir.

Que hace
--------
Monta una carpeta con un `sistema.ini` propio que apunta a MySQL, corre las
migraciones, mira el schema, y corre los tests de stock ahi. No toca ni
`sistema.ini` ni `sistema.db` del proyecto.

Para correrlo hace falta el usuario de MySQL. Si todavia no existe:

    sudo mysql < /mnt/c/Programacion/PyFE/tools/_setup_mysql.sql
"""

import os
import shutil
import subprocess
import sys
import tempfile

ORIGEN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ORIGEN)

USUARIO = "pyfe"
PASSWORD = "pyfe_test_123"
BASE = "pyfe_stock_test"
HOST = "localhost"


def _prepara_carpeta():
    """Carpeta con datos/, sistema.ini en MySQL y el password cifrado."""
    carpeta = tempfile.mkdtemp(prefix="pyfe_mysql_")
    shutil.copytree(os.path.join(ORIGEN, "data"), os.path.join(carpeta, "data"))

    # El password se guarda con el esquema que el propio proyecto usa, en vez
    # de inventar uno: si el mecanismo de secretos estaria roto, esta prueba
    # lo delata en vez de esquivarlo con un atajo.
    from cryptography.fernet import Fernet
    clave = Fernet.generate_key().decode()
    cifrado = Fernet(key=clave.encode()).encrypt(PASSWORD.encode()).decode()

    with open(os.path.join(carpeta, "sistema.ini"), "w", encoding="utf-8") as f:
        f.write("[param]\n")
        f.write("base = mysql\n")
        f.write("basedatos = {}\n".format(BASE))
        f.write("usuario = {}\n".format(USUARIO))
        f.write("host = {}\n".format(HOST))
        f.write("password = {}\n".format(cifrado))
        f.write("key = {}\n".format(clave))
    return carpeta


def _corre(carpeta, guion, etiqueta):
    """Corre un guion en un proceso aparte, con la carpeta como directorio."""
    proceso = subprocess.run([sys.executable, "-c", guion], cwd=carpeta,
                             capture_output=True)
    salida = (proceso.stdout or b"").decode("utf-8", "replace")
    error = (proceso.stderr or b"").decode("utf-8", "replace")
    print("--- {} ---".format(etiqueta))
    if salida.strip():
        print(salida.strip())
    if proceso.returncode:
        print("FALLO (codigo {}):".format(proceso.returncode))
        print(error.strip()[-2500:])
    return proceso.returncode


MIGRAR = '''
import os, sys
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, {raiz!r})
sys.argv = [sys.argv[0]]
from modelos.ModeloBase import db
from modelos.ParametrosSistema import ParamSist
from controladores.MigracionBaseDatos import MigracionBaseDatos

print("motor:", type(db).__name__, "| base:", db.database)
ParamSist.create_table(safe=True)
m = MigracionBaseDatos.__new__(MigracionBaseDatos)
m.Migrar()
print("version:", ParamSist.ObtenerParametro("VERSION_DB"))
print("fallidas:", list(getattr(m, "migraciones_fallidas", [])))
'''

MIRAR = '''
import sys
sys.path.insert(0, {raiz!r})
from modelos.ModeloBase import db
from modelos.MovStock import MovStock
from modelos.Articulos import Articulo
from modelos.Cabfact import Cabfact
from modelos.DetFactProv import DetFactProv

for tabla in ("movstock", "articulos", "cabfact", "pdetalle"):
    columnas = [f.column_name for f in db.get_columns(tabla)]
    print("{{}}: {{}}".format(tabla, columnas))

print("FK de movstock:",
      [str(fk.column_name) + "->" + fk.dest_table for fk in db.get_foreign_keys("movstock")])
print("FK de cabfact hacia remito:",
      [str(fk.column_name) for fk in db.get_foreign_keys("cabfact")
       if fk.dest_table == "remito"])
print("FK de pdetalle hacia articulos:",
      [str(fk.column_name) for fk in db.get_foreign_keys("pdetalle")
       if fk.dest_table == "articulos"])
'''

STOCK = '''
import sys
from datetime import date
sys.path.insert(0, {raiz!r})
from modelos.Articulos import Articulo
from modelos.Cabfact import Cabfact
from modelos.ModeloBase import db
from modelos.Remitos import DetalleRemito, Remito
from modelos.Tipocomprobantes import TipoComprobante
from libs import stock

fallos = []

def chequea(que, obtenido, esperado):
    ok = obtenido == esperado
    print("{{}} {{}}: {{}} (esperado {{}})".format(
        "OK  " if ok else "FALLA", que, obtenido, esperado))
    if not ok:
        fallos.append(que)

# Catalogo minimo. Los ids NO se fuerzan: en MySQL el AUTO_INCREMENT sigue
# su cuenta aunque uno le pase un id explicito, asi que un idcliente=1 fijo
# termina siendo otro y las claves foraneas no encuentran al cliente. Se crea
# cada maestro y se usa el id que devolvio.
from modelos.Tipoiva import Tipoiva
from modelos.Unidades import Unidad
from modelos.Grupos import Grupo
from modelos.Localidades import Localidad
from modelos.Tipodoc import Tipodoc
from modelos.Tiporesp import Tiporesp
from modelos.Proveedores import Proveedor
from modelos.Cajeros import Cajero
from modelos.Formaspago import Formapago
from modelos.Impuestos import Impuesto
from modelos.Clientes import Cliente
from modelos.CentroCostos import CentroCosto


def primero(modelo, **campos):
    """El primero que exista, o uno nuevo."""
    fila = modelo.select().first()
    return fila if fila is not None else modelo.create(**campos)


iva21 = primero(Tipoiva, codigo="01", descrip="IVA GENERAL", iva=21)
primero(Tipoiva, codigo="02", descrip="10.5", iva=10.5)
comp_factura = primero(TipoComprobante, codigo=6, nombre="FACTURA B",
                        abreviatura="B", lado="D", exporta=0, ultcomp=0,
                        letra="B")
primero(TipoComprobante, codigo=92, nombre="Proforma", abreviatura="PRO",
        lado="", exporta=0, ultcomp=0, letra="X")
unidad = primero(Unidad, unidad="UN", descripcion="UNIDAD")
impuesto = primero(Impuesto, detalle="SIN PERCEPCION")
grupo = primero(Grupo, nombre="VARIOS", impuesto=impuesto.idimpuesto)
localidad = primero(Localidad, nombre="x", provincia="x", nacion="ARG")
tipodoc = primero(Tipodoc, codigo=0, tipo="2", nombre="DNI")
tiporesp = primero(Tiporesp, nombre="CF", factura=6, notacredito=8,
                   notadebito=7, condicion_iva_receptor_id=5)
proveedor = primero(Proveedor, nombre="SIN PROVEEDOR",
                    tiporesp=tiporesp.idtiporesp, idlocalidad=localidad.idlocalidad)
cajero = primero(Cajero, nombre="CAJERO")
formapago = primero(Formapago, detalle="EFECTIVO")
ctrocosto = primero(CentroCosto, nombre="GENERAL")
cliente = primero(Cliente, nombre="CF", domicilio="S/N",
                  localidad=localidad.idlocalidad, dni=11111111,
                  tipodocu=tipodoc.codigo, tiporesp=tiporesp.idtiporesp,
                  formapago=formapago.idformapago, percepcion=impuesto.idimpuesto)
print("cliente:", cliente.idcliente, "| formapago:", formapago.idformapago,
      "| grupo:", grupo.idgrupo)

Articulo.delete().execute()
gasolina = Articulo.create(nombre="GASOLINA", controlastock=True, stockminimo=5,
                           preciopub=100, costo=80, unidad="UN", grupo=1,
                           provppal=1, tipoiva="01", concepto="1")
servicio = Articulo.create(nombre="MANTENIMIENTO", controlastock=False,
                           stockminimo=0, preciopub=5000, costo=0, unidad="UN",
                           grupo=1, provppal=1, tipoiva="01", concepto="2")

# 1. El BIT vuelve bien de MySQL. Ahi vuelve b'\\x01', no True.
gasolina = Articulo.get_by_id(gasolina.idarticulo)
chequea("controlastock True", bool(gasolina.controlastock), True)
servicio = Articulo.get_by_id(servicio.idarticulo)
chequea("controlastock False", bool(servicio.controlastock), False)
chequea("stockminimo", float(gasolina.stockminimo), 5.0)

# 2. La suma. En sqlite hay que redondear el float de SUM; en MySQL el DECIMAL
#    ya viene exacto. El codigo tiene que dar lo mismo en los dos motores.
stock.registra_inventario_inicial(gasolina.idarticulo, 10)
stock.registra_salida(gasolina.idarticulo, 3, origen="VENTA")
stock.registra_entrada(gasolina.idarticulo, 0.1, origen="COMPRA")
stock.registra_entrada(gasolina.idarticulo, 0.2, origen="COMPRA")
chequea("10 - 3 + 0.1 + 0.2", stock.stock_de(gasolina.idarticulo), stock.Decimal("7.3"))
chequea("stockminimo 5, hay 7.3", stock.hay_faltantes(gasolina.idarticulo), False)

# 3. Un servicio no genera movimientos.
stock.registra_salida(servicio.idarticulo, 1)
chequea("un servicio no descuenta", stock.stock_de(servicio.idarticulo), stock.CERO)

# 4. El remito descuenta y la factura con remito NO vuelve a descontar. Es el
#    error mas caro de la feature y MySQL no lo perdona distinto que sqlite.
remito = Remito.create(cliente=cliente.idcliente, fecha=date(2026, 1, 15), ptovta=1,
                       numero="00000001", forma_pago=formapago.idformapago,
                       tipo_comprobante=92, estado="A", observaciones="")
DetalleRemito.create(remito=remito, producto=gasolina.idarticulo,
                     detalle="GASOLINA", cantidad=4, precio=100, tipo_iva="01")
factura = Cabfact.create(tipocomp=comp_factura.codigo, cliente=cliente.idcliente, numero="0001-00000001",
                         nombre="CF", domicilio="S/N", idremito=remito)
stock.aplica_remito(list(DetalleRemito.select().where(DetalleRemito.remito == remito)),
                    idremito=remito)
stock.aplica_factura([(gasolina.idarticulo, 4)], idcabfact=factura.idcabfact,
                     idremito=factura.idremito_id, lado="D")
chequea("remito + factura con remito: 7.3 - 4", stock.stock_de(gasolina.idarticulo),
        stock.Decimal("3.3"))

# 5. Anular: el stock vuelve y el rastro queda.
# El inventario inicial tiene origen INICIAL, no AJUSTE. Se busca el movimiento
# real en vez de adivinar por origen: si se busca uno que no existe, el get()
# revienta y parece que la anulacion esta rota.
mov = stock.MovStock.get(stock.MovStock.idarticulo == gasolina.idarticulo,
                         stock.MovStock.origen == "INICIAL")
antes = stock.stock_de(gasolina.idarticulo)
movimientos_antes = stock.MovStock.select().count()
stock.anula(mov, observacion="prueba")
chequea("anular devuelve el stock", stock.stock_de(gasolina.idarticulo),
        antes - stock.Decimal("10"))
chequea("anular deja el movimiento original y el contrario",
        stock.MovStock.select().count(), movimientos_antes + 1)

# 6. Reversa de remito: se devuelve lo descontado.
antes = stock.stock_de(gasolina.idarticulo)
stock.revierte_de_comprobante(idremito=remito.idremito)
chequea("revertir el remito devuelve 4", stock.stock_de(gasolina.idarticulo),
        antes + stock.Decimal("4"))

# 7. La transaccion: si algo falla adentro, no queda nada.
from modelos.ModeloBase import db as _db
antes_stock = stock.stock_de(gasolina.idarticulo)
antes_movs = stock.MovStock.select().count()
try:
    with _db.atomic():
        Cabfact.create(tipocomp=comp_factura.codigo, cliente=cliente.idcliente, numero="0001-00000002",
                       nombre="CF", domicilio="S/N")
        raise ValueError("se rompio adentro de la transaccion")
except ValueError:
    pass
chequea("la transaccion revierte la cabecera",
        Cabfact.select().where(Cabfact.numero == "0001-00000002").count(), 0)
chequea("la transaccion no toco el stock", stock.stock_de(gasolina.idarticulo),
        antes_stock)
chequea("la transaccion no dejo movimientos",
        stock.MovStock.select().count(), antes_movs)

# 8. La migracion es idempotente en MySQL tambien.
from controladores.MigracionBaseDatos import MigracionBaseDatos
m = MigracionBaseDatos.__new__(MigracionBaseDatos)
m.Migrar()
chequea("migrar dos veces no falla",
        list(getattr(m, "migraciones_fallidas", [])), [])

print()
if fallos:
    print("FALLARON:", ", ".join(fallos))
    sys.exit(1)
print("OK contra MySQL")
'''

MIGRAR_DOS_VECES = '''
import sys
sys.path.insert(0, {raiz!r})
from modelos.ModeloBase import db
from modelos.MovStock import MovStock
from modelos.Articulos import Articulo
from modelos.Cabfact import Cabfact
from modelos.DetFactProv import DetFactProv

for tabla in ("movstock", "articulos", "cabfact", "pdetalle"):
    # El atributo del nombre de la columna es 'name', no 'column_name' (peewee
    # 3.17). Igual que en ForeignKeyMetadata, depends de la version.
    columnas = []
    for c in db.get_columns(tabla):
        columnas.append(getattr(c, "name", None) or getattr(c, "column_name", ""))
    print("{{}}: {{}}".format(tabla, columnas))
print("FK de movstock:",
      [str(fk.column) + "->" + fk.dest_table for fk in db.get_foreign_keys("movstock")])
print("FK de cabfact->remito:",
      [str(fk.column) for fk in db.get_foreign_keys("cabfact")
       if fk.dest_table == "remito"])
print("FK de pdetalle->articulos:",
      [str(fk.column) for fk in db.get_foreign_keys("pdetalle")
       if fk.dest_table == "articulos"])
'''


CREAR_UNO_POR_UNO = '''
import sys
sys.path.insert(0, {raiz!r})
from peewee import SQL
from modelos.Articulos import Articulo
from modelos.CabFacProv import CabFactProv
from modelos.Cabfact import Cabfact
from modelos.Cajeros import Cajero
from modelos.CentroCostos import CentroCosto
from modelos.Clientes import Cliente
from modelos.CpbteRelacionado import CpbteRel
from modelos.Ctacte import CtaCte
from modelos.DetFactProv import DetFactProv
from modelos.Detfact import Detfact
from modelos.Emailcliente import EmailCliente
from modelos.Formaspago import Formapago
from modelos.Grupos import Grupo
from modelos.Impuestos import Impuesto
from modelos.Localidades import Localidad
from modelos.ModeloBase import db
from modelos.PercepcionesDGR import PercepDGR
from modelos.Proveedores import Proveedor
from modelos.Provincias import Provincia
from modelos.Tipocomprobantes import TipoComprobante
from modelos.Tipodoc import Tipodoc
from modelos.Tipoiva import Tipoiva
from modelos.Tiporesp import Tiporesp
from modelos.Unidades import Unidad

LISTA = [Tipodoc, Tipoiva, Tiporesp, Unidad, CentroCosto, Grupo, Impuesto,
         Localidad, Provincia, TipoComprobante, Articulo, Formapago, Cliente,
         Cajero, Cabfact, Detfact, CpbteRel, Proveedor, CabFactProv,
         DetFactProv, PercepDGR, CtaCte, EmailCliente]

# La lista COMPLETA de una, como hace MigrarVersion0. peewee ordena por
# dependencias antes de crear; hacerlo de a uno, como hizo una version
# anterior de este guion, falla solo por el orden y no dice nada del problema
# real. El except de MigrarVersion0 es mudo, asi que aca se ve que modelo se
# cae y por que.
try:
    db.create_tables(LISTA)
    print("OK: la lista completa se creo entera")
except Exception as e:
    print("FALLA ->", type(e).__name__, e)

tablas = set(r[0] for r in db.get_tables())
print("tablas creadas:", len(tablas), "de", len(LISTA))
print("faltan:", [m.__name__ for m in LISTA if m._meta.table_name not in tablas])
'''


def main():
    carpeta = _prepara_carpeta()
    print("carpeta de prueba:", carpeta)
    print("MySQL:", HOST, "base", BASE, "usuario", USUARIO)
    print()

    fallidas = []
    for etiqueta, guion in (("migraciones", MIGRAR),
                            ("schema y claves foraneas", MIGRAR_DOS_VECES),
                            ("stock contra MySQL", STOCK)):
        if _corre(carpeta, guion.format(raiz=ORIGEN), etiqueta):
            fallidas.append(etiqueta)

    print()
    if fallidas:
        print("FALLARON:", ", ".join(fallidas))
        return 1
    print("OK: migraciones, claves foraneas, bit, stock, transacciones y "
          "anulaciones andan contra MySQL.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
