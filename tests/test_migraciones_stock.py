"""La migracion 9: el stock aparece en una base que ya tenia datos.

Que esta comprobando
--------------------
Que MigrarVersion9 hace su trabajo sobre una base VIEJA de verdad, y no solo
sobre una recien creada. Una instalacion nueva ya tiene el schema final porque
los modelos lo crean, asi que ahi la migracion no tiene nada que hacer y pasa
en verde sin probar nada. El caso que importa es el otro: una base con
facturas cargadas, los 283 comprobantes de un cliente real, que abre la app
despues de actualizar.

Como se arma la base vieja
--------------------------
Con la siembra real del proyecto, y despues se le saca lo del stock: se
borra la tabla `movstock` y las cuatro columnas nuevas. Se deja todo lo demas
intacto a proposito, para que la migracion corra sobre una base con los mismos
datos que tendria en produccion y no sobre un schema inventado por el test.

Las dos columnas que son clave foranea (`cabfact.idremito` y
`pdetalle.idarticulo`) no se pueden borrar con `ALTER TABLE ... DROP COLUMN`:
sqlite no deja dejar una FK apuntando a una columna que ya no existe, asi que
esas dos tablas se recrean. Ver `_quitar_columna`.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)


# Prepara una base vieja, migra y vuelca lo que quedo. Todo en un subprocess
# porque peewee tiene la base abierta y hay que soltar la conexion para poder
# tocar el schema con sqlite3 puro.
#
# Las rutas entran por el entorno y no se pegan en el guion. Pegadas, una
# carpeta de Windows ("C:\Users\...") llega al hijo con los backslashes sin
# escapar y Python los lee como secuencias de escape: "unicodeescape: truncated
# \UXXXXXXXX escape". Con el entorno no hay escaping que acertar.
GUION = '''
import json, os, sqlite3, sys

CARPETA = os.environ["PYFE_TEST_CARPETA"]
RAIZ = os.environ["PYFE_TEST_RAIZ"]
SALIDA = os.environ["PYFE_TEST_SALIDA"]

os.chdir(CARPETA)
sys.path.insert(0, RAIZ)
sys.argv = [sys.argv[0]]
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from modelos.ParametrosSistema import ParamSist
from controladores.MigracionBaseDatos import MigracionBaseDatos
from modelos.ModeloBase import db

# 1. Base nueva, con la siembra real del proyecto.
ParamSist.create_table(safe=True)
MigracionBaseDatos.__new__(MigracionBaseDatos).Migrar()
nombre_db = db.database
db.close()

# 2. Un remito, para poder afirmar que la migracion no pisa lo que ya estaba.
#    Ojo con los nombres: en 'remito' las FK se llaman 'cliente_id' y
#    'tipo_comprobante_id', no 'cliente' (peewee no pone column_name y usa el
#    nombre del campo con el _id de la tabla). Se verifica con PRAGMA y no de
#    memoria, porque adivinarlo hace fallar el armado por una razon que no dice
#    nada del stock.
c = sqlite3.connect(nombre_db)
cols_remito = [r[1] for r in c.execute('PRAGMA table_info("remito")')]
assert "cliente_id" in cols_remito, cols_remito
# Sin 'OR IGNORE' a proposito:peewee pone los defaults en Python, no en el
# CREATE TABLE, asi que toda columna NOT NULL va en el INSERT o el motor la
# rechaza. Con OR IGNORE eso pasaba en silencio y el remito no existia, y el
# fallo aparecia veinte lineas mas abajo como si la migracion lo hubiera
# borrado.
c.execute("INSERT INTO remito (idremito, cliente_id, fecha, ptovta, numero, "
          "forma_pago_id, tipo_comprobante_id, estado, observaciones) "
          "VALUES (1, 1, '2026-01-15', 1, '00000001', 1, 92, 'A', 'remito viejo')")
c.commit()
cuantos = c.execute("SELECT COUNT(*) FROM remito WHERE idremito=1").fetchone()[0]
assert cuantos == 1, "el remito viejo no se pudo sembrar ({})".format(cuantos)
c.close()

# 3. Dejarla como estaba antes del stock.
def partir_cuerpo(sql):
    i = sql.index("(", sql.upper().index("CREATE TABLE"))
    nivel = 0
    for j in range(i, len(sql)):
        if sql[j] == "(":
            nivel += 1
        elif sql[j] == ")":
            nivel -= 1
            if nivel == 0:
                return sql[:i], sql[i + 1:j], sql[j:]
    raise ValueError("no se pudo partir el CREATE TABLE")

def partes_primer_nivel(cuerpo):
    """Parte la definicion en columnas, sin cortar dentro de un DECIMAL(12, 2).

    La coma de "DECIMAL(12, 2)" no separa columnas: partir ahi produce partes
    como '"neto" DECIMAL(12' y deja un '2)' suelto, que es exactamente el
    'table cabfact__vieja has no column named 2)' que tiraba antes.
    """
    partes, actual, nivel = [], "", 0
    for caracter in cuerpo:
        if caracter == "(":
            nivel += 1
        elif caracter == ")":
            nivel -= 1
        if caracter == "," and nivel == 0:
            partes.append(actual.strip())
            actual = ""
        else:
            actual += caracter
    if actual.strip():
        partes.append(actual.strip())
    return partes

def quitar_columna(tabla, columna):
    sql = c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                    (tabla,)).fetchone()[0]
    pre, cuerpo, post = partir_cuerpo(sql)
    # peewee escribe las claves foraneas peladas, sin la palabra CONSTRAINT:
    # FOREIGN KEY ("idremito") REFERENCES "remito" ("idremito"). Un filtro que
    # buscase CONSTRAINT no sacaria ninguna y el CREATE de abajo tiraria
    # 'unknown column "idremito" in foreign key definition'.
    def es_de_esta_columna(parte):
        if parte.startswith('"' + columna + '"'):
            return True
        return (parte.upper().startswith("FOREIGN KEY")
                and '"' + columna + '"' in parte)

    queda = [p for p in partes_primer_nivel(cuerpo) if not es_de_esta_columna(p)]
    # El nombre va aparte: si se reusara el 'CREATE TABLE' que viene en `pre`
    # quedaria "CREATE TABLE x__vieja CREATE TABLE x (...)", que es lo que
    # tiraba 'near CREATE: syntax error'.
    c.execute('CREATE TABLE "{}__vieja" ({})'.format(tabla, ", ".join(queda)))
    columnas = [p.split()[0].strip('"') for p in queda
                if not p.upper().startswith(("CONSTRAINT", "FOREIGN KEY"))]
    quoted = ", ".join('"' + x + '"' for x in columnas)
    c.execute('INSERT INTO "' + tabla + '__vieja" (' + quoted + ") SELECT "
              + quoted + ' FROM "' + tabla + '"')
    c.execute('DROP TABLE "' + tabla + '"')
    c.execute('ALTER TABLE "{}__vieja" RENAME TO "{}"'.format(tabla, tabla))

c = sqlite3.connect(nombre_db)
c.execute("DROP TABLE movstock")
c.execute("ALTER TABLE articulos DROP COLUMN controlastock")
c.execute("ALTER TABLE articulos DROP COLUMN stockminimo")
quitar_columna("cabfact", "idremito")
quitar_columna("pdetalle", "idarticulo")
c.execute("UPDATE paramsist SET valor='8' WHERE parametro='VERSION_DB'")
c.commit()
c.close()

# 4. Que la app se arranque y migre sola, como en una actualizacion.
m = MigracionBaseDatos.__new__(MigracionBaseDatos)
m.Migrar()
primera = {
    "candidatas": len(m.migraciones),
    "fallidas": list(getattr(m, "migraciones_fallidas", [])),
}

# 4b. Y otra vez, que es lo que pasa en cada arranque siguiente: no puede
#     quedar trabajo, o la app se pone a migrar en cada inicio para siempre.
m2 = MigracionBaseDatos.__new__(MigracionBaseDatos)
m2.Migrar()
segunda = {
    "candidatas": len(m2.migraciones),
    "fallidas": list(getattr(m2, "migraciones_fallidas", [])),
}

# 5. Que quedo.
from modelos.ModeloBase import db as _db
_db.close()
c = sqlite3.connect(nombre_db)
tablas = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")]

def columnas(tabla):
    return [r[1] for r in c.execute('PRAGMA table_info("' + tabla + '")')]

articulo = c.execute("SELECT idarticulo, nombre, preciopub FROM articulos "
                     "ORDER BY idarticulo LIMIT 1").fetchone()
remito = c.execute("SELECT numero FROM remito WHERE idremito=1").fetchone()
pdetalle = c.execute("SELECT COUNT(*) FROM pdetalle").fetchone()[0]

datos = {
    "fallidas": primera["fallidas"],
    "candidatas": primera["candidatas"],
    "segunda": segunda,
    "version": ParamSist.ObtenerParametro("VERSION_DB"),
    "tablas": tablas,
    "movstock": columnas("movstock") if "movstock" in tablas else None,
    "articulos": columnas("articulos"),
    "cabfact": columnas("cabfact"),
    "pdetalle": columnas("pdetalle"),
    "articulo": list(articulo) if articulo else None,
    "remito": list(remito) if remito else None,
    "pdetalle_filas": pdetalle,
}
c.close()
with open(SALIDA, "w", encoding="utf-8") as f:
    json.dump(datos, f, ensure_ascii=False)
'''


@pytest.fixture
def base_vieja():
    carpeta = tempfile.mkdtemp(prefix="pyfe_stock_")
    shutil.copytree(os.path.join(RAIZ, "data"), os.path.join(carpeta, "data"),
                    ignore=shutil.ignore_patterns("*.db"))
    with open(os.path.join(carpeta, "sistema.ini"), "w", encoding="utf-8") as f:
        f.write("[param]\nbase = sqlite\nusa_nombre_db = S\n"
                "basedatos = stock\nhomo = S\n")
    salida = os.path.join(carpeta, "_stock.json")
    entorno = dict(os.environ,
                   PYFE_TEST_CARPETA=carpeta,
                   PYFE_TEST_RAIZ=RAIZ,
                   PYFE_TEST_SALIDA=salida)
    proceso = subprocess.run([sys.executable, "-c", GUION], cwd=carpeta,
                             env=entorno, capture_output=True)
    if proceso.returncode:
        # Sin esto, un fallo aca es un CalledProcessError que no dice nada:
        # el motivo esta en el stderr del hijo, que capture_output se come.
        raise AssertionError(
            "no se pudo armar la base vieja.\nstdout: {}\nstderr: {}".format(
                (proceso.stdout or b"").decode("utf-8", "replace"),
                (proceso.stderr or b"").decode("utf-8", "replace")))
    with open(salida, encoding="utf-8") as f:
        yield json.load(f)
    shutil.rmtree(carpeta, ignore_errors=True)


def test_una_base_vieja_no_falla_ninguna_migracion(base_vieja):
    """Si la migracion del stock falla, la app no arranca en una base vieja.

    Es el unico momento en que un cliente existente se topa con esto: al
    actualizar. Si falla aca, la base queda con la version sin sellar y el
    proximo arranque lo reintenta, pero entre tanto no se puede facturar.
    """
    assert base_vieja["fallidas"] == [], \
        "migrar el stock sobre una base con datos fallo: {}".format(
            base_vieja["fallidas"])


def test_la_version_se_avanza(base_vieja):
    assert base_vieja["version"] == "11", \
        "la base vieja quedo en version {!r}, no se sello como al dia".format(
            base_vieja["version"])


def test_la_base_vieja_gana_la_tabla_de_movimientos(base_vieja):
    """Sin `movstock` no hay stock: es la tabla de la que se deriva todo."""
    assert "movstock" in base_vieja["tablas"], \
        "la tabla de movimientos no se creo: {}".format(base_vieja["tablas"])

    columnas = base_vieja["movstock"] or []
    forColumna = ("idmovstock", "idarticulo", "cantidad", "tipo", "origen",
                  "idcabfact", "idremito", "idpcabecera", "anula",
                  "observacion")
    for columna in forColumna:
        assert columna in columnas, \
            "a movstock le falta la columna {}: {}".format(columna, columnas)


def test_la_base_vieja_gana_las_columnas_de_stock(base_vieja):
    """Las cuatro columnas que hacen que el stock se pueda usar de verdad."""
    assert "controlastock" in base_vieja["articulos"], \
        "articulos no gano controlastock: {}".format(base_vieja["articulos"])
    assert "stockminimo" in base_vieja["articulos"], \
        "articulos no gano stockminimo: {}".format(base_vieja["articulos"])
    assert "idremito" in base_vieja["cabfact"], \
        "cabfact no gano idremito: {}".format(base_vieja["cabfact"])
    assert "idarticulo" in base_vieja["pdetalle"], \
        "pdetalle no gano idarticulo: {}".format(base_vieja["pdetalle"])


def test_la_migracion_no_pisa_los_datos_que_ya_estaban(base_vieja):
    """Agregar columnas no puede tocar lo que hay.

    `controlastock` y `stockminimo` se agregan sobre una tabla con articulos
    cargados. Si la migracion los pisa, el cliente pierde su catalogo en el
    primer arranque despues de actualizar, y no hay forma de recuperarlo.
    """
    assert base_vieja["articulo"] is not None, \
        "la siembra dejo articulos vacios, el test no probaria nada"
    idarticulo, nombre, preciopub = base_vieja["articulo"]

    assert nombre, "el articulo quedo sin nombre"
    assert float(preciopub or 0) >= 0, \
        "el precio del articulo quedo en {!r}".format(preciopub)

    # Y el remito que estaba antes de migrar, sigue estando.
    assert base_vieja["remito"] is not None, \
        "desaparecio el remito que estaba antes de migrar"
    assert base_vieja["pdetalle_filas"] == 0, \
        "pdetalle quedo con filas fantasma: {}".format(
            base_vieja["pdetalle_filas"])


def test_migrar_dos_veces_no_genera_trabajo(base_vieja):
    """La primera vez hace el trabajo pendiente. La segunda, nada.

    En una base vieja hay trabajo de verdad: las cuatro columnas. Lo que no
    puede pasar es que la app se ponga a migrar en cada arranque para siempre,
    que es lo que haria si MigrarVersion9 no fuera idempotente y la version no
    quedara sellada.
    """
    assert base_vieja["candidatas"] == 4, \
        "una base a la que le faltan las cuatro columnas deberia tener 4 " \
        "migraciones, tiene {}: si sobran, esta agregando algo que no " \
        "corresponde; si faltan, se esta comiendo trabajo".format(
            base_vieja["candidatas"])

    segunda = base_vieja["segunda"]
    assert segunda["fallidas"] == [], \
        "la segunda corrida fallo: {}".format(segunda["fallidas"])
    assert segunda["candidatas"] == 0, \
        "la segunda corrida quiso migrar {} cosas mas: la version 9 no es " \
        "idempotente y la app va a migrar en cada arranque".format(
            segunda["candidatas"])
