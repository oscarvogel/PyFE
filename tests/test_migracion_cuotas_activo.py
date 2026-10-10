"""Migracion 12: activo por plan de cuotas.

Por que existe
--------------
La tabla cuotaspago nacio en la migracion 11 sin columna activo, y las
bases ya migraron asi (sistema.db esta en VERSION_DB 11). Al arrancar,
la 12 tiene que agregar la columna y dejar los planes existentes
activos, sin fallar y sin pedir nada.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)


GUION = '''
import json, sqlite3
import os, sys
os.chdir({carpeta!r})
sys.path.insert(0, {raiz!r})
sys.argv = [sys.argv[0]]
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from controladores.MigracionBaseDatos import MigracionBaseDatos
from modelos.ParametrosSistema import ParamSist

# Primera pasada: instala todo ( queda en 12, con activo ).
ParamSist.create_table(safe=True)
m = MigracionBaseDatos.__new__(MigracionBaseDatos)
m.Migrar()

# Se la deja como estaba en produccion: tabla sin activo, version 11.
base = os.path.join({carpeta!r}, "cuotas.db")
c = sqlite3.connect(base)
c.execute("ALTER TABLE cuotaspago DROP COLUMN activo")
c.execute("UPDATE paramsist SET valor='11' WHERE parametro='VERSION_DB'")
c.commit()
c.close()

# Segunda pasada: es lo que corre al abrir la app actualizada.
m2 = MigracionBaseDatos.__new__(MigracionBaseDatos)
m2.Migrar()

c = sqlite3.connect(base)
datos = {{
    "fallidas": list(getattr(m2, "migraciones_fallidas", [])),
    "version": ParamSist.ObtenerParametro("VERSION_DB"),
    "columnas": [r[1] for r in
                 c.execute('PRAGMA table_info("cuotaspago")')],
    "planes": c.execute(
        "SELECT idformapago, cuotas, recargo, activo FROM cuotaspago "
        "ORDER BY idformapago, cuotas").fetchall(),
}}
c.close()
with open({salida!r}, "w", encoding="utf-8") as f:
    json.dump(datos, f, ensure_ascii=False)
'''


def _carpeta():
    carpeta = tempfile.mkdtemp(prefix="pyfe_cuotas_")
    shutil.copytree(os.path.join(RAIZ, "data"), os.path.join(carpeta, "data"),
                    ignore=shutil.ignore_patterns("*.db"))
    with open(os.path.join(carpeta, "sistema.ini"), "w", encoding="utf-8") as f:
        f.write("[param]\nbase = sqlite\nusa_nombre_db = S\n"
                "basedatos = cuotas\nhomo = S\n")
    return carpeta


def test_upgrade_11_a_12_agrega_activo_y_activa_los_planes():
    carpeta = _carpeta()
    try:
        salida = os.path.join(carpeta, "_cuotas.json")
        subprocess.run(
            [sys.executable, "-c",
             GUION.format(carpeta=carpeta, raiz=RAIZ, salida=salida)],
            cwd=carpeta, capture_output=True, check=True)
        with open(salida, encoding="utf-8") as f:
            datos = json.load(f)
    finally:
        shutil.rmtree(carpeta, ignore_errors=True)

    assert datos["fallidas"] == [], \
        "migrar a 12 fallo: {}".format(datos["fallidas"])
    assert datos["version"] == "12"
    assert "activo" in datos["columnas"], \
        "cuotaspago no gano activo: {}".format(datos["columnas"])
    assert datos["planes"], "la migracion se comio los planes"
    assert all(p[3] == 1 for p in datos["planes"]), \
        "los planes existentes tienen que quedar activos: {}".format(
            datos["planes"])
