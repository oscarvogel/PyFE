"""La condicion de IVA del receptor, que es obligatoria ante ARCA.

Por que esta prueba existe
--------------------------
`condicion_iva_receptor_id` se agrego a la tabla `tiporesp` con default 5
(Consumidor Final). La siembra de `data/tiporesp.csv` no cargaba esa columna, y
como el default pisa lo que no se carga, **las cuatro filas quedaban en 5**: a
un Responsable Inscripto con CUIT se le mandaba "Consumidor Final" a ARCA,
incompatible con el tipo de documento 80. Y desde la RG 5616 el campo es
obligatorio: sin el, se rechaza el comprobante.

Estos tests no usan un fixture armado a mano: siembran una base de verdad con
el codigo de siembra y miran lo que queda. Un fixture con los valores correctos
pasa en verde aunque la siembra siga rota.
"""

import os
import shutil
import sqlite3
import sys
import tempfile

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from libs.catalogos import (CONDICION_CONSUMIDOR_FINAL,  # noqa: E402
                            CONDICION_IVA_POR_TIPO_RESPONSABLE,
                            CONDICIONES_IVA_RECEPTOR)


# -- El catalogo ------------------------------------------------------------

def test_el_catalogo_tiene_los_diez_codigos_de_arca():
    """El asistente ofrecia 8, pero ARCA define 10.

    Faltaban el 7 (Sujeto No Categorizado) y el 16 (Monotributo Trabajador
    Independiente Promovido).
    """
    assert set(CONDICIONES_IVA_RECEPTOR) == {1, 4, 5, 6, 7, 8, 9, 10, 13, 16}


def test_todo_tipo_responsable_apunta_a_un_codigo_del_catalogo():
    for nombre, codigo in CONDICION_IVA_POR_TIPO_RESPONSABLE.items():
        assert codigo in CONDICIONES_IVA_RECEPTOR, \
            "{} apunta a {} que no existe".format(nombre, codigo)


# -- El CSV y la siembra ----------------------------------------------------

def test_el_csv_trae_la_columna_que_habia_que_faltara():
    """Si el CSV no la trae, la siembra vuelve a dejar todo en el default."""
    import csv
    ruta = os.path.join(RAIZ, "data", "tiporesp.csv")
    with open(ruta, newline="", encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    assert "condicion_iva_receptor_id" in filas[0], \
        "el CSV no trae la columna y la siembra la va a perder"
    for fila in filas:
        esperado = CONDICION_IVA_POR_TIPO_RESPONSABLE[fila["nombre"]]
        assert int(fila["condicion_iva_receptor_id"]) == esperado, \
            "{} deberia venir con condicion {}".format(fila["nombre"], esperado)


@pytest.fixture
def base_sembrada():
    """Siembra una base nueva con el codigo real y la deja abierta."""
    import subprocess
    carpeta = tempfile.mkdtemp(prefix="pyfe_fase2_")
    shutil.copytree(os.path.join(RAIZ, "data"), os.path.join(carpeta, "data"),
                    ignore=shutil.ignore_patterns("*.db"))
    with open(os.path.join(carpeta, "sistema.ini"), "w", encoding="utf-8") as f:
        f.write("[param]\nbase = sqlite\nusa_nombre_db = S\n"
                "basedatos = fase2\nhomo = S\n")

    guion = (
        "import os, sys\n"
        "os.chdir({c!r})\n"
        "sys.path.insert(0, {r!r})\n"
        "sys.argv = [sys.argv[0]]\n"
        "os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')\n"
        "from modelos.ParametrosSistema import ParamSist\n"
        "from controladores.MigracionBaseDatos import MigracionBaseDatos\n"
        "ParamSist.create_table(safe=True)\n"
        "m = MigracionBaseDatos.__new__(MigracionBaseDatos)\n"
        "m.Migrar()\n"
        "print('{{}}'.format(m.CorregirCondicionIvaReceptor.__doc__ is not None))\n"
    ).format(c=carpeta, r=RAIZ)
    subprocess.run([sys.executable, "-c", guion], cwd=carpeta,
                   capture_output=True, check=True)
    return carpeta


def _condiciones(base_sembrada):
    c = sqlite3.connect(os.path.join(base_sembrada, "fase2.db"))
    try:
        return {r[0]: r[1] for r in
                c.execute("select nombre, condicion_iva_receptor_id from tiporesp")}
    finally:
        c.close()


def test_la_siembra_deja_cada_tipo_con_su_condicion(base_sembrada):
    """La prueba que faltaba: no un fixture, sino la siembra de verdad."""
    condiciones = _condiciones(base_sembrada)
    for nombre, esperado in CONDICION_IVA_POR_TIPO_RESPONSABLE.items():
        assert condiciones[nombre] == esperado, \
            "{} quedo con condicion {} y deberia tener {}".format(
                nombre, condiciones[nombre], esperado)


def test_un_responsable_inscripto_no_queda_como_consumidor_final(base_sembrada):
    """El caso concreto que rompia los comprobantes."""
    condiciones = _condiciones(base_sembrada)
    assert condiciones["RESP. INSCRIPTO"] != CONDICION_CONSUMIDOR_FINAL
    assert condiciones["MONOTRIBUTO"] != CONDICION_CONSUMIDOR_FINAL
    assert condiciones["EXENTO"] != CONDICION_CONSUMIDOR_FINAL
