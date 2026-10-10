"""`articulos.incre1`: el porcentaje de ganancia del articulo.

Que esta comprobando
--------------------
1. La cuenta: precio = costo x (1 + incre1/100).
2. Que cero significa "precio a mano", que es el estado en el que esta todo el
   catalogo que ya existia.
3. Que la vista calcula el precio mientras haya ganancia, y que el campo de
   precio queda en solo lectura para que el precio no se desincronice del costo.
4. Que al guardar se persiste la CUENTA y no lo que quedo escrito en el control.
5. Que la migracion 10 agrega la columna en una base que no la tiene, no hace
   nada en una que ya la tiene, y no se come trabajo en el arranque siguiente.

Dos formas de probar la vista, y por que dos
--------------------------------------------
La parte rapida llama a `RecalculaPrecio` directo sobre una instancia creada con
`__new__`. La parte lenta construye la vista DE VERDAD y mueve los controles
como el operador.

No es redundancia. `ArticulosView` hereda de un QWidget, y `__new__` sin
`__init__` deja un objeto sin su lado C++: ahí una conexion de senal a un metodo
ligado de esa instancia NO dispara, y un test que la usara pasaria en verde sin
estar probando nada. Los controles del caso rapido son los Spinners reales, con
sus metodos reales; lo unico que no se ejercita ahi es la conexion, y por eso
esa parte se prueba con la pantalla verdadera.

Ojo con `isEnabled()`: devuelve el estado efectivo, o sea el del control Y el de
sus padres. La pestana de detalle arranca deshabilitada, asi que sin
habilitarla todos los controles dan False y el test no probaria el bloqueo sino
la pestana.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)


# -- La cuenta (sin Qt, sin base) ---------------------------------------------
#
# Las comparaciones son contra `Decimal`, no contra float ni int: un Decimal no
# es igual a un float en Python, asi que `precio == 140` daria False con un
# resultado que esta bien. Mismo criterio que test_importar_articulos.

def test_cuarenta_por_ciento_sobre_el_costo():
    from libs.ganancia import precio_desde_incre1

    assert precio_desde_incre1(100, 40) == Decimal("140.0000")


def test_el_caso_de_la_planilla():
    """El mismo numero del docstring del importador, en escala de porcentaje.

    El importador calcula 10142 x 1.4 = 14198.80 a partir del multiplicador
    GANANCIA. El ABM calcula 10142 x (1 + 40/100) = 14198.80 a partir del
    porcentaje. Si las dos cuentas dieran distinto, el mismo producto tendria
    dos precios segun por donde haya entrado.
    """
    from libs.ganancia import precio_desde_incre1

    assert precio_desde_incre1(10142, 40) == Decimal("14198.8000")


def test_el_porcentaje_es_sobre_el_costo_y_no_sobre_el_precio():
    """100 de costo con 50% da 150, no 200.

    La cuenta equivocada (ganancia sobre el precio) da 200 y parece
    razonable, que es justo por lo que hay que probarla: un test que solo
    mira que "el precio subio" no la distingue.
    """
    from libs.ganancia import precio_desde_incre1

    assert precio_desde_incre1(100, 50) == Decimal("150.0000")


def test_el_precio_respeta_cuatro_decimales():
    """`preciopub` es DECIMAL(12,4) y MySQL cortaria lo que sobra.

    Un porcentaje con mas decimales es raro, pero el costo puede traerlos, y el
    redondeo tiene que ser el del modelo y no un capricho.
    """
    from libs.ganancia import precio_desde_incre1

    precio = precio_desde_incre1(Decimal("100"), Decimal("33.33333"))
    # 100 x 1.3333333 = 133.33333; a cuatro decimales queda 133.3333.
    assert precio == Decimal("133.3333")
    assert str(precio).split(".")[1] == "3333"


def test_sin_costo_no_inventa_un_precio_de_cero():
    """Devolver 0 seria guardar un producto con precio cero sin avisar."""
    from libs.ganancia import precio_desde_incre1

    assert precio_desde_incre1(None, 40) is None


def test_cero_no_es_ganancia():
    """Cero es 'precio a mano', no 'vender a costo'."""
    from libs.ganancia import margen_activo

    assert margen_activo(0) is False
    assert margen_activo(None) is False


def test_un_porcentaje_negativo_no_es_una_orden_de_vender_por_debajo_del_costo():
    """Un negativo se trata como no cargado.

    Si se tomara como cuenta, -50 sobre 100 daria un precio de 50 y el
    catalogo tendria productos a la mitad de su costo, que es una decision
    comercial que se toma en el precio, no escribiendo un numero negativo en un
    campo de porcentaje.
    """
    from libs.ganancia import margen_activo

    assert margen_activo(-50) is False


def test_un_porcentaje_chico_es_ganancia():
    from libs.ganancia import margen_activo

    assert margen_activo(0.5) is True


# -- El modelo -----------------------------------------------------------------

def test_el_modelo_tiene_el_campo_con_default_cero():
    """El default 0 es lo que hace que ningun articulo previo cambie de comportamiento.

    Si el default fuera NULL, los articulos que ya estan en la base tendrian un
    margen desconocido y el ABM no podria decir si el precio se calcula o se
    tipea.
    """
    from modelos.Articulos import Articulo

    assert Articulo.incre1.column_name == "incre1"
    assert Articulo.incre1.default == 0


# -- La vista: la reaccion del control (llamando al metodo) -------------------

@pytest.fixture
def qt():
    from PyQt5.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture
def vista(qt):
    """Solo los tres controles que manda la cuenta.

    `__new__` evita el `__init__`, que arma la pantalla entera y consulta los
    catalogos. No se falsea ningun metodo de los que se prueban: los Spinners
    son los de `libs.Spinner` y la cuenta es la de `libs.ganancia`.
    """
    from libs.Spinner import Spinner
    from vistas.Articulos import ArticulosView

    v = ArticulosView.__new__(ArticulosView)
    v.controles = {"costo": Spinner(), "incre1": Spinner(decimales=2),
                   "preciopub": Spinner()}
    return v


def test_cargar_ganancia_calcula_el_precio(vista):
    vista.controles["costo"].setValue(100)
    vista.controles["incre1"].setValue(40)
    vista.RecalculaPrecio()

    assert vista.controles["preciopub"].value() == 140


def test_cargar_ganancia_deja_el_precio_en_solo_lectura(vista):
    """Si el precio se pudiera editar, dejaria de caminar con el costo.

    El porcentaje promete que el precio sale del costo. Con el campo editable,
    el operador puede cargar un precio que no sale de la cuenta que tiene escrita
    al lado, y no queda ninguna marca de que lo hizo a mano.
    """
    vista.controles["costo"].setValue(100)
    vista.controles["incre1"].setValue(40)
    vista.RecalculaPrecio()

    assert vista.controles["preciopub"].isEnabled() is False


def test_cambiar_el_costo_recalcula_el_precio(vista):
    """El precio sigue al costo mientras haya ganancia cargada."""
    vista.controles["costo"].setValue(200)
    vista.controles["incre1"].setValue(40)
    vista.RecalculaPrecio()

    assert vista.controles["preciopub"].value() == 280


def test_volver_a_cero_deja_el_precio_a_mano(vista):
    """Volver a 0 es volver al modo en el que estan todos los articulos viejos.

    Si el precio quedara bloqueado con el valor calculado, el operador no
    podria ni corregirlo ni desactivarlo.
    """
    vista.controles["costo"].setValue(100)
    vista.controles["incre1"].setValue(40)
    vista.RecalculaPrecio()
    vista.controles["incre1"].setValue(0)
    vista.RecalculaPrecio()

    assert vista.controles["preciopub"].isEnabled() is True


def test_sin_ganancia_el_precio_no_se_toca(vista):
    """El estado por defecto: el precio es lo que cargo el operador."""
    vista.controles["preciopub"].setValue(999)
    vista.RecalculaPrecio()

    assert vista.controles["preciopub"].value() == 999


# -- Guardado, senales y migracion, contra una base de verdad -----------------

# Todo en un subprocess: peewee deja la base abierta y hay que soltar la
# conexion para poder tocar el schema con sqlite3 puro. Las rutas entran por el
# entorno y no se pegan en el guion, porque una carpeta de Windows con
# backslashes llega al hijo como secuencias de escape.
GUION = '''
import json, os, sqlite3, sys

CARPETA = os.environ["PYFE_TEST_CARPETA"]
RAIZ = os.environ["PYFE_TEST_RAIZ"]
SALIDA = os.environ["PYFE_TEST_SALIDA"]

os.chdir(CARPETA)
sys.path.insert(0, RAIZ)
sys.argv = [sys.argv[0]]
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication
app = QApplication([])

from modelos.ParametrosSistema import ParamSist
from controladores.MigracionBaseDatos import MigracionBaseDatos
from modelos.ModeloBase import db
from modelos.Articulos import Articulo
from libs.Spinner import Spinner
from vistas.Articulos import ArticulosView

# 1. Base nueva, con la siembra real del proyecto.
ParamSist.create_table(safe=True)
m0 = MigracionBaseDatos.__new__(MigracionBaseDatos)
m0.Migrar()
nombre_db = db.database
nueva = {
    "candidatas": len(m0.migraciones),
    "fallidas": list(getattr(m0, "migraciones_fallidas", [])),
}

# Articulos con costo y precio a mano, que es el estado de todo el catalogo que
# ya existia. Los id arrancan en 900 porque la siembra ya usa 1 y 2.
Articulo.create(idarticulo=900, nombre="Producto viejo", costo=100,
                preciopub=999, incre1=0)
Articulo.create(idarticulo=901, nombre="Producto con margen", costo=100,
                preciopub=140, incre1=40)
db.close()

# 2. Dejarla como estaba antes de incre1: sin la columna, en version 9.
c = sqlite3.connect(nombre_db)
c.execute("ALTER TABLE articulos DROP COLUMN incre1")
c.execute("UPDATE paramsist SET valor='9' WHERE parametro='VERSION_DB'")
c.commit()
c.close()

# 3. Que la app se arranque y migre sola, como en una actualizacion.
m = MigracionBaseDatos.__new__(MigracionBaseDatos)
m.Migrar()
primera = {
    "candidatas": len(m.migraciones),
    "fallidas": list(getattr(m, "migraciones_fallidas", [])),
}

# 3b. Y otra vez, que es lo que pasa en cada arranque siguiente.
m2 = MigracionBaseDatos.__new__(MigracionBaseDatos)
m2.Migrar()
segunda = {
    "candidatas": len(m2.migraciones),
    "fallidas": list(getattr(m2, "migraciones_fallidas", [])),
}

# 4. La pantalla DE VERDAD, con los controles conectados como los conecta
#    ArmaCarga. Aca si se prueban las senales, que en el caso rapido no se
#    pueden probar.
v = ArticulosView()
# isEnabled() mira tambien los padres, y la pestana de detalle arranca
# deshabilitada: sin habilitarla todos los controles darian False.
v.tabDetalle.setEnabled(True)

v.controles["costo"].setValue(100)
v.controles["incre1"].setValue(40)
senales = {
    "precio_con_ganancia": v.controles["preciopub"].value(),
    "bloqueado_con_ganancia": v.controles["preciopub"].isEnabled(),
}
v.controles["costo"].setValue(200)
senales["precio_al_cambiar_el_costo"] = v.controles["preciopub"].value()
v.controles["incre1"].setValue(0)
senales["habilitado_sin_ganancia"] = v.controles["preciopub"].isEnabled()

# 5. Guardar por el codigo de verdad, sobre una instancia sin pantalla: lo que
#    se prueba es el guardado, y ArmaTabla/btnCancelarClicked piden el formulario.
class CampoFalso(object):
    """Un control que no participa de la cuenta, con su contrato de widget."""
    def __init__(self, valor):
        self._valor = valor
    def text(self):
        return self._valor
    def value(self):
        return 0

g = ArticulosView.__new__(ArticulosView)
g.tipo = "A"
g.controles = {
    "idarticulo": CampoFalso(""),
    "nombre": CampoFalso("Producto nuevo"),
    "nombreticket": CampoFalso("Nuevo"),
    "unidad": CampoFalso("UN"),
    "grupo": CampoFalso(1),
    "costo": Spinner(),
    "incre1": Spinner(decimales=2),
    "preciopub": Spinner(),
    "provppal": CampoFalso(1),
    "tipoiva": CampoFalso("01"),
    "modificaprecios": CampoFalso(False),
    "concepto": CampoFalso("1"),
    "codbarra": CampoFalso(""),
    "controlastock": CampoFalso(False),
    "stockminimo": Spinner(),
}
g.ArmaTabla = lambda: None
g.btnCancelarClicked = lambda: None

# Con ganancia: el precio se guarda calculado, no el del control.
g.controles["costo"].setValue(100)
g.controles["incre1"].setValue(40)
g.controles["preciopub"].setValue(7)      # desincronizado a proposito
g.btnAceptarClicked()

# Sin ganancia: el precio va tal cual lo cargo el operador.
g.tipo = "A"
g.controles["nombre"]._valor = "Producto a mano"
g.controles["costo"].setValue(100)
g.controles["incre1"].setValue(0)
g.controles["preciopub"].setValue(999)
g.btnAceptarClicked()

# 6. Que quedo.
from modelos.ModeloBase import db as _db
_db.close()
c = sqlite3.connect(nombre_db)

def columnas(tabla):
    return [r[1] for r in c.execute('PRAGMA table_info("' + tabla + '")')]

def buscar(nombre):
    fila = c.execute("SELECT nombre, costo, preciopub, incre1 FROM articulos "
                     "WHERE nombre = ?", (nombre,)).fetchone()
    return list(fila) if fila else None

datos = {
    "nueva": nueva,
    "primera": primera,
    "segunda": segunda,
    "version": ParamSist.ObtenerParametro("VERSION_DB"),
    "articulos": columnas("articulos"),
    "senales": senales,
    "vistos": {n: buscar(n) for n in
               ("Producto viejo", "Producto con margen")},
    "guardados": {n: buscar(n) for n in
                  ("Producto nuevo", "Producto a mano")},
}
c.close()
with open(SALIDA, "w", encoding="utf-8") as f:
    json.dump(datos, f, ensure_ascii=False)
'''


@pytest.fixture(scope="module")
def base_real():
    carpeta = tempfile.mkdtemp(prefix="pyfe_incre1_")
    shutil.copytree(os.path.join(RAIZ, "data"), os.path.join(carpeta, "data"),
                    ignore=shutil.ignore_patterns("*.db"))
    with open(os.path.join(carpeta, "sistema.ini"), "w", encoding="utf-8") as f:
        f.write("[param]\nbase = sqlite\nusa_nombre_db = S\n"
                "basedatos = incre1\nhomo = S\n")
    salida = os.path.join(carpeta, "_incre1.json")
    entorno = dict(os.environ,
                   PYFE_TEST_CARPETA=carpeta,
                   PYFE_TEST_RAIZ=RAIZ,
                   PYFE_TEST_SALIDA=salida)
    proceso = subprocess.run([sys.executable, "-c", GUION], cwd=carpeta,
                             env=entorno, capture_output=True)
    if proceso.returncode:
        raise AssertionError(
            "no se pudo correr el guion.\nstdout: {}\nstderr: {}".format(
                (proceso.stdout or b"").decode("utf-8", "replace"),
                (proceso.stderr or b"").decode("utf-8", "replace")))
    with open(salida, encoding="utf-8") as f:
        yield json.load(f)
    shutil.rmtree(carpeta, ignore_errors=True)


# -- La migracion -------------------------------------------------------------

def test_una_instalacion_nueva_no_genera_sql_de_migracion(base_real):
    """El modelo crea la columna, asi que en una base nueva no hay nada que hacer.

    Si la migracion generara SQL aca, cada instalacion nueva imprimiria un
    traceback al arrancar. Es el mismo motivo por el que MigrarVersion9 no
    aparece en la lista de migraciones que corren en una base recien creada.
    """
    assert base_real["nueva"]["fallidas"] == [], \
        "una instalacion nueva fallo: {}".format(base_real["nueva"]["fallidas"])
    assert base_real["nueva"]["candidatas"] == 0, \
        "una instalacion nueva genero {} migraciones: los modelos ya crean " \
        "la columna".format(base_real["nueva"]["candidatas"])


def test_la_base_vieja_gana_la_columna(base_real):
    assert "incre1" in base_real["articulos"], \
        "articulos no gano incre1: {}".format(base_real["articulos"])


def test_la_migracion_no_falla(base_real):
    assert base_real["primera"]["fallidas"] == [], \
        "migrar incre1 sobre una base con datos fallo: {}".format(
            base_real["primera"]["fallidas"])


def test_la_migracion_hace_exactamente_un_trabajo(base_real):
    """Solo la columna que falta.

    Si hiciera mas, estaria tocando cosas que no le corresponden; si hiciera
    menos, se estaria comiendo trabajo.
    """
    assert base_real["primera"]["candidatas"] == 1, \
        "una base a la que le falta incre1 deberia tener 1 migracion, tiene " \
        "{}: {}".format(base_real["primera"]["candidatas"],
                        base_real["primera"]["fallidas"])


def test_la_version_se_avanza(base_real):
    assert base_real["version"] == "11", \
        "la base vieja quedo en version {!r}, no se sello como al dia".format(
            base_real["version"])


def test_migrar_dos_veces_no_genera_trabajo(base_real):
    """La app no se pone a migrar en cada arranque para siempre."""
    segunda = base_real["segunda"]
    assert segunda["fallidas"] == [], \
        "la segunda corrida fallo: {}".format(segunda["fallidas"])
    assert segunda["candidatas"] == 0, \
        "la segunda corrida quiso migrar {} cosas mas: la migracion 10 no " \
        "es idempotente".format(segunda["candidatas"])


def test_la_migracion_no_pisa_los_precios_que_ya_estaban(base_real):
    """Agregar una columna no puede cambiar como se vende lo que ya estaba.

    Este es el punto de una base vieja: si la migracion recalculara precios,
    el catalogo entero cambiaria de precio en el primer arranque despues de
    actualizar, sin que nadie lo haya pedido.

    Ojo con lo que pasa con el margen: la base vieja NO TIENE la columna, asi
    que su valor no puede sobrevivir al `DROP COLUMN` con el que este test
    arma el escenario. Vuelve en 0, que es el default, y eso es lo correcto:
    "no hay regla cargada", el precio a mano. Lo que se afirma aca es que el
    PRECIO quedo como estaba, que es lo unico que no se puede romper.
    """
    visto = base_real["vistos"]["Producto viejo"]
    assert visto is not None, "desaparecio el articulo viejo"
    nombre, costo, preciopub, incre1 = visto
    assert incre1 == 0, \
        "al articulo que no tenia margen le aparecio uno: {}".format(incre1)
    assert float(preciopub) == 999, \
        "al articulo sin margen le recalcularon el precio: {}".format(preciopub)

    conmargen = base_real["vistos"]["Producto con margen"]
    assert conmargen is not None, "desaparecio el articulo con margen"
    _, costo, preciopub, incre1 = conmargen
    assert float(preciopub) == 140, \
        "la migracion toco el precio de un articulo que ya estaba: {}".format(
            preciopub)


# -- La pantalla de verdad ----------------------------------------------------

def test_la_pantalla_tiene_el_campo_de_ganancia(base_real):
    """Si el control no esta, no hay donde cargar el porcentaje."""
    assert "incre1" in base_real["articulos"], \
        "no se probo el control: la columna no llego a la base"


def test_cargar_ganancia_en_la_pantalla_calcula_el_precio(base_real):
    """La senal de verdad: el operador escribe y el precio se mueve solo."""
    assert base_real["senales"]["precio_con_ganancia"] == 140, \
        "cargar 40 con costo 100 no dio 140: {}".format(
            base_real["senales"]["precio_con_ganancia"])


def test_en_la_pantalla_el_precio_queda_bloqueado(base_real):
    assert base_real["senales"]["bloqueado_con_ganancia"] is False, \
        "con ganancia cargada el precio se puede editar: el precio y el " \
        "costo dejarian de caminar juntos sin que nadie lo note"


def test_en_la_pantalla_cambiar_el_costo_recalcula(base_real):
    assert base_real["senales"]["precio_al_cambiar_el_costo"] == 280, \
        "cambiar el costo a 200 con 40% no recalculo el precio: {}".format(
            base_real["senales"]["precio_al_cambiar_el_costo"])


def test_en_la_pantalla_volver_a_cero_devuelve_el_precio_a_mano(base_real):
    assert base_real["senales"]["habilitado_sin_ganancia"] is True, \
        "con la ganancia en 0 el precio quedo bloqueado: el operador no " \
        "podria volver a cargarlo a mano"


# -- El guardado --------------------------------------------------------------

def test_guardar_persiste_la_cuenta_y_no_lo_que_habia_en_el_control(base_real):
    """Con ganancia cargada, lo que se guarda es la cuenta.

    El control estaba en 7 a proposito, desincronizado. Si se guardara lo que
    habia ahi, el producto quedaria con precio 7 mientras el operador ve 140 en
    pantalla.
    """
    fila = base_real["guardados"]["Producto nuevo"]
    assert fila is not None, "no se guardo el producto"
    nombre, costo, preciopub, incre1 = fila
    assert float(incre1) == 40, "no se guardo el margen: {}".format(incre1)
    assert float(preciopub) == 140, \
        "se guardo el precio del control en vez de la cuenta: {}".format(preciopub)


def test_sin_margen_se_guarda_el_precio_que_cargo_el_operador(base_real):
    """Sin margen, el precio a mano se respeta: no se recalcula contra el costo."""
    fila = base_real["guardados"]["Producto a mano"]
    assert fila is not None, "no se guardo el producto a mano"
    nombre, costo, preciopub, incre1 = fila
    assert float(incre1) == 0, "aparecio un margen donde no habia: {}".format(incre1)
    assert float(preciopub) == 999, \
        "un producto sin margen fue recalculado contra el costo: {}".format(preciopub)