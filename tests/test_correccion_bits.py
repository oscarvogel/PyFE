"""La correccion de bits sobre bases que ya quedaron mal.

Contexto
--------
BitBooleanField guardaba como False el '1' del CSV, asi que en toda base creada
hasta ahora los bits de los maestros estan en cero. El caso visible es
tipocomp.exporta, que deja la reimpresion, el Libro IVA Ventas y los RG 3685 con
la lista vacia.

La correccion vuelve a leer el CSV y arregla SOLO las filas que difieren. Estos
tests parten de una base con todo en cero, como quedo con el bug, y comprueban
que queda como manda el CSV. Correrla dos veces no tiene que cambiar nada.
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

# La base vieja: la tabla existe, cargada, y con los bits en cero.
BASE_VIEJA = [
    (1, "FACTURA A", "A", "D", 0, 0, "A"),
    (6, "FACTURA B", "B", "D", 0, 0, "B"),
    (11, "FACTURA C", "C", "D", 0, 0, "C"),
    (12, "NOTA DEBITO C", "NCC", "D", 0, 0, "C"),
    (13, "NOTA CREDITO C", "NCC", "H", 0, 0, "C"),
    (82, "TIQUE FACTURA B", "", "D", 0, 0, "B"),
    (300, "TIPO DEL USUARIO", "", "", 0, 0, ""),
]

# Lo que el CSV dice de esos mismos codigos.
SEGUN_CSV = {
    1: True, 6: True, 11: True, 12: True, 13: True,
    82: False, 300: None,      # 300 no esta en el CSV
}


@pytest.fixture
def base_con_zeros(monkeypatch, tmp_path):
    """La base como quedo con el bug, con el CSV del repo al lado."""
    import csv
    import shutil

    from peewee import SqliteDatabase
    from modelos.Tipocomprobantes import TipoComprobante

    shutil.copytree(os.path.join(RAIZ, "data"), str(tmp_path / "data"),
                    ignore=shutil.ignore_patterns("*.db"))
    monkeypatch.chdir(tmp_path)

    original = TipoComprobante._meta.database
    db = SqliteDatabase(":memory:")
    TipoComprobante._meta.set_database(db)
    db.create_tables([TipoComprobante])
    for fila in BASE_VIEJA:
        TipoComprobante.create(codigo=fila[0], nombre=fila[1],
                               abreviatura=fila[2], lado=fila[3],
                               exporta=fila[4], ultcomp=fila[5], letra=fila[6])
    yield db, TipoComprobante
    TipoComprobante._meta.set_database(original)


def _correccion():
    from controladores.MigracionBaseDatos import MigracionBaseDatos
    return MigracionBaseDatos.__new__(MigracionBaseDatos)


def test_la_correccion_arma_las_facturas(base_con_zeros):
    _, TipoComprobante = base_con_zeros

    corregidas = _correccion().CorregirBitsDeMaestros()

    # 1, 6, 11, 12 y 13: las cinco facturas que el CSV arma. El tique y el tipo
    # del usuario se quedan en cero.
    assert corregidas == 5, "debio corregir 5 filas, corrigio {}".format(corregidas)
    for codigo, esperado in SEGUN_CSV.items():
        if esperado is None:
            continue
        tipo = TipoComprobante.get_by_id(codigo)
        assert tipo.exporta == esperado, \
            "{} quedo con exporta={} y el CSV dice {}".format(
                tipo.nombre, tipo.exporta, esperado)


def test_el_tique_se_queda_en_cero(base_con_zeros):
    _, TipoComprobante = base_con_zeros
    _correccion().CorregirBitsDeMaestros()

    # El filtro de la reimpresion existe justamente para dejar los tiques
    # afuera. Si este se armara, empezarian a aparecer facturas que no son.
    assert TipoComprobante.get_by_id(82).exporta is False


def test_un_tipo_que_no_esta_en_el_csv_no_se_toca(base_con_zeros):
    _, TipoComprobante = base_con_zeros
    _correccion().CorregirBitsDeMaestros()

    # Puede ser uno que creo el administrador: no se inserta ni se borra.
    assert TipoComprobante.get_or_none(TipoComprobante.codigo == 300) is not None
    assert TipoComprobante.get_by_id(300).exporta is False


def test_correrla_dos_veces_no_cambia_nada(base_con_zeros):
    _, TipoComprobante = base_con_zeros
    m = _correccion()

    m.CorregirBitsDeMaestros()
    primera = {t.codigo: t.exporta for t in TipoComprobante.select()}

    segunda = m.CorregirBitsDeMaestros()
    despues = {t.codigo: t.exporta for t in TipoComprobante.select()}

    assert segunda == 0, "la segunda corrida corrigio algo: {}".format(segunda)
    assert despues == primera


def test_sin_el_csv_no_hace_nada(base_con_zeros, monkeypatch):
    """Si data/ no esta, se avisa en el log y se sigue: no se rompe el arranque."""
    _, TipoComprobante = base_con_zeros
    os.remove(os.path.join("data", "tipocomprobante.csv"))

    assert _correccion().CorregirBitsDeMaestros() == 0
    assert TipoComprobante.get_by_id(1).exporta is False
