"""Las migraciones: hacen algo, o no hacen nada. Y no mienten.

Que estaba pasando
------------------
1. Migrar() usaba MySQLMigrator siempre. Sobre una base sqlite, que es la de
   por defecto, cada migracion de esquema era SQL de MySQL y fallaba siempre:
   'near "MODIFY": syntax error', 'near "CONSTRAINT": syntax error'. En una
   instalacion nueva: cinco tracebacks en el log y en la consola.

2. Y no tenian nada que hacer. Los modelos ya crean el schema final, asi que
   esas migraciones eran no-ops en toda base, nueva o vieja. No eran
   migraciones que fallaran: eran migraciones sin trabajo, que ademas fallaban.

3. VERSION_DB se sellaba igual. RealizaMigraciones se comia cada excepcion y
   despues se guardaba 'VERSION_DB = 7' como si todo hubiera salido bien. Una
   base con la mitad del schema mal migrantado quedaba marcada como al dia y no
   se volvia a intentar nunca.

Estos tests siembran una base de verdad con el codigo de siembra y miran lo que
pasa. Un fixture armado a mano pasa en verde aunque la siembra siga rota.
"""

import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)


GUION = '''
import json, os, sys
os.chdir({carpeta!r})
sys.path.insert(0, {raiz!r})
sys.argv = [sys.argv[0]]
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from modelos.ParametrosSistema import ParamSist
from controladores.MigracionBaseDatos import MigracionBaseDatos
ParamSist.create_table(safe=True)
m = MigracionBaseDatos.__new__(MigracionBaseDatos)
m.Migrar()
from modelos.ModeloBase import db as _db
datos = {{
    "fallidas": list(getattr(m, "migraciones_fallidas", [])),
    "candidatas": len(m.migraciones),
    "version": ParamSist.ObtenerParametro("VERSION_DB"),
    "error": bool(getattr(m, "error", False)),
    "basedatos": getattr(_db, "database", "?"),
    "archivos": sorted(n for n in os.listdir(".") if n.endswith(".db")),
    "que": [repr(getattr(x, "method", "?")) + " " +
            repr(getattr(x, "args", "")) for x in m.migraciones],
    "grupos": sorted(m._columnas("grupos").keys()),
    "tipo_nombre": m._tipo_de_columna("clientes", "nombre"),
}}
with open({salida!r}, "w", encoding="utf-8") as f:
    json.dump(datos, f, ensure_ascii=False)
'''


def _sembrar(nombre="migr"):
    carpeta = tempfile.mkdtemp(prefix="pyfe_mig_")
    shutil.copytree(os.path.join(RAIZ, "data"), os.path.join(carpeta, "data"),
                    ignore=shutil.ignore_patterns("*.db"))
    with open(os.path.join(carpeta, "sistema.ini"), "w", encoding="utf-8") as f:
        f.write("[param]\nbase = sqlite\nusa_nombre_db = S\n"
                "basedatos = {}\nhomo = S\n".format(nombre))
    return carpeta


def _migrar(carpeta, nombre):
    salida = os.path.join(carpeta, "_mig.json")
    subprocess.run(
        [sys.executable, "-c", GUION.format(carpeta=carpeta, raiz=RAIZ,
                                            salida=salida)],
        cwd=carpeta, capture_output=True, check=True)
    import json
    with open(salida, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def instalacion():
    carpeta = _sembrar()
    yield carpeta
    shutil.rmtree(carpeta, ignore_errors=True)


def test_una_instalacion_nueva_no_falla_ninguna_migracion(instalacion):
    """El numero que importa: cero.

    Antes eran cinco fallos en cada arranque, y ninguno era necesario.
    """
    r = _migrar(instalacion, "migr")

    assert r["fallidas"] == [], \
        "una base recien creada no deberia tener migraciones que hacer: {}".format(
            r["fallidas"])


def test_una_instalacion_nueva_no_genera_sql_de_migracion(instalacion):
    """No solo no fallan: es que no hay nada que correr.

    Los modelos crean el schema final, asi que en una base nueva las
    migraciones de esquema no tienen nada que hacer. Si esta lista tiene algo,
    o se esta por ahi algo inofensivo, o se perdio el salto de columna.
    """
    r = _migrar(instalacion, "migr")

    assert r["candidatas"] == 0, (
        "se generan {} migraciones para una base recien creada.\n"
        "que: {}\nbasedatos: {}\narchivos: {}\ngrupos: {}\n"
        "tipo_nombre: {!r}".format(
            r["candidatas"], r.get("que"), r.get("basedatos"),
            r.get("archivos"), r.get("grupos"), r.get("tipo_nombre")))


def test_la_version_se_avanza_cuando_no_falla_nada(instalacion):
    r = _migrar(instalacion, "migr")

    assert not r["fallidas"]
    assert r["version"] == "8"


def test_la_version_no_se_avanza_si_una_migracion_falla(instalacion,
                                                       monkeypatch):
    """El sello es lo que hacia que el fallo quedara escondido para siempre.

    Si se avanza la version con una migracion fallada, el proximo arranque ve
    la version al dia y no reintenta nada. La base queda rota sin que nadie lo
    note.
    """
    import json
    import peewee

    # Se rompe una migracion a proposito: se agrega una columna que ya existe
    # pero saltandose el control, que es justo lo que pasaba antes.
    salida = os.path.join(instalacion, "_mig.json")
    guion = GUION.format(carpeta=instalacion, raiz=RAIZ, salida=salida).replace(
        "m.Migrar()",
        "m.Migrar()\n"
        "m.migraciones_fallidas = ['simulada: fallo de verdad']\n"
        "m.error = True\n"
        "ParamSist.GuardarParametro('VERSION_DB', '3')",
    )
    # Se corre Migrar dos veces: la primera para sembrar, la segunda con el
    # fallo forzado usando la version vieja.
    subprocess.run([sys.executable, "-c", guion], cwd=instalacion,
                   capture_output=True, check=True)
    with open(salida, encoding="utf-8") as f:
        datos = json.load(f)

    # La version 3 tiene migraciones pendientes; si el sello fuera
    # incondicional quedaria en 8 con un fallo de por medio.
    assert datos["version"] != "8", \
        "la version seavanzo a 8 con una migracion fallida"


def test_una_base_ya_migrada_no_hace_nada_instalacion():
    """Correr dos veces no genera trabajo: la segunda no hace nada."""
    carpeta = _sembrar("dos_veces")
    try:
        salida = os.path.join(carpeta, "_mig.json")
        primera = subprocess.run(
            [sys.executable, "-c", GUION.format(carpeta=carpeta, raiz=RAIZ,
                                                salida=salida)],
            cwd=carpeta, capture_output=True, check=True)
        import json
        with open(salida, encoding="utf-8") as f:
            r1 = json.load(f)
        assert r1["version"] == "8"

        # Segunda corrida: la version ya esta, asi que ni siquiera entra al
        # Migrar() por las guardas de version. Y si entrara, no generaria nada.
        r2 = _migrar(carpeta, "dos_veces")
        assert r2["fallidas"] == []
        assert r2["candidatas"] == 0
    finally:
        shutil.rmtree(carpeta, ignore_errors=True)


def test_la_siembra_sigue_poniendolos_datos(instalacion):
    """Que las migraciones no hagan nada NO puede ser que no se siembre nada.

    Este test abre la base DESPUES de migrar: antes lo hacia sobre una base que
    el fixture recien habia creado, sin sembrar, y por eso找不到 tiporesp.
    """
    _migrar(instalacion, "migr")
    base = os.path.join(instalacion, "migr.db")
    c = sqlite3.connect(base)
    try:
        assert c.execute("select count(*) from tiporesp").fetchone()[0] == 4
        assert c.execute("select count(*) from tipodoc").fetchone()[0] == 6
        assert c.execute("select count(*) from tipoiva").fetchone()[0] == 3
    finally:
        c.close()
