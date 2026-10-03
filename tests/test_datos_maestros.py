"""La siembra de datos maestros al crear la base.

Por que esta probada
--------------------
Instalando el ejecutable en una maquina nueva, la base se creaba VACIA: sin
alicuotas de IVA, sin tipos de comprobante, sin formas de pago. La app
arrancaba igual y no habia forma de emitir nada.

La causa era que la migracion lee "data/tipoiva.csv" con ruta relativa, y la
carpeta data/ no viajaba al .exe. Peor: `cargar_csv` hacia `open(archivo)` sin
ninguna proteccion, asi que el primer faltante cortaba TODA la siembra. El
error quedaba en el log, lejos de la pantalla, y de paso se perdian los
maestros que si estaban.

Estos tests fijan las dos cosas: que falte un archivo no corte el resto, y que
la distribucion lleve la carpeta data/.
"""
import os
import sys

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

# Los maestros que la app necesita para poder emitir. Si uno falta, la
# instalacion nueva no sirve.
MAESTROS_IMPRESCINDIBLES = [
    "tipoiva.csv",          # alicuotas de IVA
    "tipodoc.csv",          # DNI, CUIT, etc
    "tiporesp.csv",         # responsable inscripto, consumidor final, ...
    "tipocomprobante.csv",  # que comprobante se puede emitir
    "formapago.csv",        # formas de pago
    "provincias.csv",
    "localidades.csv",
    "unidad.csv",
    "impuestos.csv",
    "centrocostos.csv",
    "grupos.csv",
]


def test_los_maestros_imprescindibles_estan_en_el_repo():
    faltantes = [m for m in MAESTROS_IMPRESCINDIBLES
                 if not os.path.isfile(os.path.join(RAIZ, "data", m))]
    assert not faltantes, "faltan los CSV maestros: {}".format(faltantes)


def test_la_distribucion_lleva_la_carpeta_data():
    """Si data/ no viaja al .exe, la base nueva queda vacia."""
    dist = os.path.join(RAIZ, "dist", "data")
    if not os.path.isdir(os.path.join(RAIZ, "dist")):
        pytest.skip("todavia no se compilo")
    assert os.path.isdir(dist), \
        "dist/data no existe: una instalacion nueva queda sin datos maestros"
    faltantes = [m for m in MAESTROS_IMPRESCINDIBLES
                 if not os.path.isfile(os.path.join(dist, m))]
    assert not faltantes, "en dist/data faltan: {}".format(faltantes)


def test_cargar_csv_sin_el_archivo_no_rompe_nada(monkeypatch):
    """Un faltante tiene que avisar y seguir, no cortarlo todo."""
    monkeypatch.setattr(sys, "argv", [sys.argv[0]])
    from controladores.MigracionBaseDatos import MigracionBaseDatos

    migracion = MigracionBaseDatos.__new__(MigracionBaseDatos)

    errores = []
    import logging
    monkeypatch.setattr(logging, "error", lambda *a, **k: errores.append(a))

    cargados = migracion.cargar_csv(
        archivo="data/no-existe-este-archivo.csv", campos=None, modelo=None)

    assert cargados == 0
    assert errores, "un faltante tiene que quedar registrado en el log"


def test_cargar_csv_trae_las_filas(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", [sys.argv[0]])
    from controladores.MigracionBaseDatos import MigracionBaseDatos

    csv = tmp_path / "prueba.csv"
    csv.write_text("id,detalle\n1,EFECTIVO\n2,TARJETA\n", encoding="utf-8")

    migracion = MigracionBaseDatos.__new__(MigracionBaseDatos)

    filas = []
    modelos = {}

    class ModeloFalso(object):
        @staticmethod
        def insert_many(datos, fields=None):
            modelos["datos"] = datos
            modelos["fields"] = fields
            return Ejecutable()

    class Ejecutable(object):
        @staticmethod
        def execute():
            return 1

    # El cwd tiene que ser la raiz para que data/... se resuelva.
    monkeypatch.chdir(RAIZ)
    import shutil
    destino = os.path.join(RAIZ, "data", "prueba-temporal.csv")
    shutil.copy(str(csv), destino)
    try:
        cargados = migracion.cargar_csv(
            archivo="data/prueba-temporal.csv",
            campos=["id", "detalle"], modelo=ModeloFalso)
    finally:
        os.remove(destino)

    assert cargados == 2
    assert modelos["datos"] == [("1", "EFECTIVO"), ("2", "TARJETA")]
    assert filas == []
