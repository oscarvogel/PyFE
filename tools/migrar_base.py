"""Migrar la base de trabajo a la version actual.

Se usa cuando la base quedo en una version anterior y hay que adelantarla sin
arrancar la app entera. Es lo mismo que hace main.py al abrir, pero sin
levantar Qt ni la ventana.

Hay backup antes de correr: tools/migrar_base.py hace una copia con la
extension .bak y no pisa una que ya este.
"""

import os
import shutil
import sys

ORIGEN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ORIGEN)
os.chdir(ORIGEN)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from modelos.ModeloBase import db  # noqa: E402
from modelos.ParametrosSistema import ParamSist  # noqa: E402
from controladores.MigracionBaseDatos import MigracionBaseDatos  # noqa: E402

nombre = db.database
print("base:", nombre)
print("version antes:", ParamSist.ObtenerParametro("VERSION_DB"))

respaldo = str(nombre) + ".bak"
if os.path.exists(str(nombre)) and not os.path.exists(respaldo):
    shutil.copy(str(nombre), respaldo)
    print("respaldo:", respaldo)

m = MigracionBaseDatos.__new__(MigracionBaseDatos)
m.Migrar()

print("version despues:", ParamSist.ObtenerParametro("VERSION_DB"))
fallidas = list(getattr(m, "migraciones_fallidas", []))
print("migraciones fallidas:", fallidas)
if fallidas:
    sys.exit(1)
print("OK")
