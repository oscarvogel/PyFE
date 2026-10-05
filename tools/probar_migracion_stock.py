"""Prueba de la migracion 9 sobre una base con las facturas reales.

No se toca sistema.db: se copia a una carpeta temporal, se migra la copia y se
compara antes y despues. El test de migraciones usa una base vacia, que es
justo el caso donde no puede haber datos que se pierdan ni rarezas de schema.
Esta prueba es la otra mitad: la base de un cliente, con 283 facturas y 2068
renglones que no se pueden perder.
"""

import os
import shutil
import sqlite3
import sys
import tempfile

ORIGEN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ORIGEN)

t = tempfile.mkdtemp(prefix="pyfe_migracion_real_")
shutil.copytree(os.path.join(ORIGEN, "data"), os.path.join(t, "data"))
shutil.copy(os.path.join(ORIGEN, "sistema.db"), os.path.join(t, "sistema.db"))
with open(os.path.join(t, "sistema.ini"), "w", encoding="utf-8") as f:
    f.write("[param]\nbase = sqlite\nusa_nombre_db = S\n"
            "basedatos = sistema\nhomo = S\n")
os.chdir(t)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def estado(c):
    def cuenta(tabla):
        return c.execute("select count(*) from " + tabla).fetchone()[0]

    def tiene(consulta):
        return bool(c.execute(consulta).fetchone())

    return {
        "facturas": cuenta("cabfact"),
        "renglones": cuenta("detfact"),
        "articulos": cuenta("articulos"),
        "remitos": cuenta("remito"),
        "compras": cuenta("pcabecera"),
        "movstock": tiene("select 1 from sqlite_master where name='movstock'"),
        "col_stockminimo": tiene("pragma table_info(articulos)"),
    }


def columnas(c, tabla):
    return [r[1] for r in c.execute("pragma table_info('" + tabla + "')")]


c = sqlite3.connect("sistema.db")
antes = estado(c)
version_antes = c.execute(
    "select valor from paramsist where parametro='VERSION_DB'").fetchone()[0]
articulos_antes = c.execute(
    "select idarticulo, nombre, preciopub, costo, codbarraart from articulos "
    "order by idarticulo").fetchall()
ultima_antes = c.execute(
    "select idcabfact, numero, total from cabfact order by idcabfact desc "
    "limit 1").fetchone()
print("ANTES   ", antes)
print("ANTES    version:", version_antes)
c.close()

from controladores.MigracionBaseDatos import MigracionBaseDatos

m = MigracionBaseDatos.__new__(MigracionBaseDatos)
m.Migrar()

from modelos.ModeloBase import db as _db
_db.close()

c = sqlite3.connect("sistema.db")
despues = estado(c)
version_despues = c.execute(
    "select valor from paramsist where parametro='VERSION_DB'").fetchone()[0]
articulos_despues = c.execute(
    "select idarticulo, nombre, preciopub, costo, codbarraart from articulos "
    "order by idarticulo").fetchall()
ultima_despues = c.execute(
    "select idcabfact, numero, total from cabfact order by idcabfact desc "
    "limit 1").fetchone()
print("DESPUES ", despues)
print("DESPUES version:", version_despues)
print("DESPUES columnas nuevas:",
      "controlastock" in columnas(c, "articulos"),
      "stockminimo" in columnas(c, "articulos"),
      "idremito" in columnas(c, "cabfact"),
      "idarticulo" in columnas(c, "pdetalle"))
print("DESPUES fallos:", list(getattr(m, "migraciones_fallidas", [])))
print()

errores = []
for clave in ("facturas", "renglones", "articulos", "remitos", "compras"):
    if antes[clave] != despues[clave]:
        errores.append("{}: {} -> {}".format(clave, antes[clave], despues[clave]))
if articulos_antes != articulos_despues:
    errores.append("los articulos cambiaron:\n  antes {}\n  despues {}".format(
        articulos_antes, articulos_despues))
if ultima_antes != ultima_despues:
    errores.append("la ultima factura cambio: {} -> {}".format(
        ultima_antes, ultima_despues))
if despues["movstock"] is not True:
    errores.append("no se creo movstock")
if version_despues != "9":
    errores.append("la version quedo en {}".format(version_despues))
if list(getattr(m, "migraciones_fallidas", [])):
    errores.append("migraciones fallidas")

print("carpeta de prueba:", t)
if errores:
    print()
    print("FALLAS:")
    for e in errores:
        print("  -", e)
    sys.exit(1)
print("OK: la base con datos reales migro sin perder nada.")
