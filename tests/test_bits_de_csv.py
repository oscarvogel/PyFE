"""Los bits de los CSV tienen que guardarse como booleanos de verdad.

El bug
------
BitBooleanField.db_value hacia `value == 1` en sqlite. Desde un CSV el valor
llega como TEXTO, y en Python '1' == 1 es False. O sea que TODOS los bits de
los CSV se guardaban en cero: cargar 15 filas y devolver 15, como si hubiera
ido bien, y sin ningun error en el log.

Lo que rompia
-------------
tipocomp.exporta. El CSV lo pone en 1 para las facturas A, B, C y sus notas, y
en 0 para los tiques. Con todo en cero, cuatro pantallas quedaban vacias:

  - Reimpresion de facturas (filtra por exporta)
  - Libro IVA Ventas (idem)
  - RG 3685 ventas (idem)
  - RG 3685 compras (idem)

La primera que se descubre es la reimpresion, porque es la que se usa cuando
algo sale mal y no hay nada que reimprimir.

Estos tests siembran con el codigo real y con los CSV reales del repo. Un
fixture con los valores ya puestos passes en verde aunque la siembra siga rota.
"""

import csv
import os
import subprocess
import sys
import tempfile

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)


# -- El normalizador, que es la parte pura ---------------------------------

@pytest.mark.parametrize("valor,esperado", [
    (1, True), (0, False), (True, True), (False, False),
    ("1", True), ("0", False), ("", False), (" 1 ", True),
    ("S", True), ("s", True), ("N", False), ("n", False),
    ("si", True), ("sí", True), ("no", False), ("SI", True),
    ("true", True), ("false", False), ("True", True),
    (b"\x01", True), (b"\x00", False), (b"\1", True),
    (None, False),
])
def test_el_normalizador_entende_todas_las_formas(valor, esperado):
    """El caso que rompia todo era '1' desde un CSV."""
    from modelos.ModeloBase import _a_bit

    assert _a_bit(valor) is esperado, \
        "{!r} deberia ser {}".format(valor, esperado)


# -- La siembra real --------------------------------------------------------

GUION_SIEMBRA = '''
import os, sys, sqlite3
os.chdir({carpeta!r})
sys.path.insert(0, {raiz!r})
sys.argv = [sys.argv[0]]
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from modelos.ModeloBase import ModeloBase
ModeloBase().getDb()
from modelos.ParametrosSistema import ParamSist
ParamSist.create_table(safe=True)
from controladores.MigracionBaseDatos import MigracionBaseDatos
MigracionBaseDatos.__new__(MigracionBaseDatos).Migrar()
'''


@pytest.fixture(scope="module")
def base_sembrada():
    """Siembra una base con el codigo y los CSV del repo, no inventados."""
    carpeta = tempfile.mkdtemp(prefix="pyfe_bits_")
    import shutil
    shutil.copytree(os.path.join(RAIZ, "data"),
                    os.path.join(carpeta, "data"),
                    ignore=shutil.ignore_patterns("*.db"))
    with open(os.path.join(carpeta, "sistema.ini"), "w", encoding="utf-8") as f:
        f.write("[param]\nbase = sqlite\nusa_nombre_db = S\n"
                "basedatos = bits\nhomo = S\n")
    subprocess.run([sys.executable, "-c",
                    GUION_SIEMBRA.format(carpeta=carpeta, raiz=RAIZ)],
                   cwd=carpeta, capture_output=True, check=True)
    yield os.path.join(carpeta, "bits.db")
    shutil.rmtree(carpeta, ignore_errors=True)


def _exporta(base, codigo):
    import sqlite3
    c = sqlite3.connect(base)
    try:
        fila = c.execute("select exporta from tip_comp where codigo = ?",
                         (codigo,)).fetchone()
        return None if fila is None else fila[0]
    finally:
        c.close()


@pytest.mark.parametrize("codigo,nombre", [
    (1, "FACTURA A"), (6, "FACTURA B"), (11, "FACTURA C"),
    (12, "NOTA DEBITO C"), (13, "NOTA CREDITO C"),
])
def test_las_facturas_quedan_marcadas(base_sembrada, codigo, nombre):
    """A, B, C y sus notas: el CSV los pone en 1 y tienen que quedar en 1."""
    valor = _exporta(base_sembrada, codigo)
    assert valor == 1, \
        "{} (codigo {}) quedo con exporta={!r}; el CSV lo pone en 1".format(
            nombre, codigo, valor)


@pytest.mark.parametrize("codigo", [0, 39, 42, 81, 82, 83])
def test_los_tiques_y_el_efectivo_quedan_en_cero(base_sembrada, codigo):
    """El filtro de exporta existe para dejar afuera los tiques."""
    assert _exporta(base_sembrada, codigo) == 0


def test_coincide_con_el_csv_del_repo(base_sembrada):
    """La base sembrada tiene que coincidir con el CSV, fila por fila.

    El CSV es la fuente de verdad de los maestros: si la base difiere, la base
    esta mal, y es mas util que fijar numeros sueltos porque detecta cualquier
    columna que se vuelva a perder.
    """
    with open(os.path.join(RAIZ, "data", "tipocomprobante.csv"),
              newline="", encoding="utf-8") as f:
        filas = list(csv.reader(f, delimiter=","))

    for fila in filas[1:]:
        if not fila or not fila[0].strip():
            continue
        codigo = int(fila[0])
        esperado = int(fila[4] or 0)
        assert _exporta(base_sembrada, codigo) == esperado, \
            "el codigo {} quedo distinto al CSV".format(codigo)
