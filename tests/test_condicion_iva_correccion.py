"""La correccion de condicion de IVA sobre una base que ya esta sembrada.

Es el otro lado de `tests/test_condicion_iva_receptor.py`: alla se siembra una
base nueva y se mira que salga bien. Acá se parte de una base con los valores
viejos, la de toda instalacion creada antes del arreglo, y se mira que:
  - se corrija lo que quedo en el default,
  - no se pise lo que alguien ya corrigio a mano,
  - no rompa el tipo de consumidor final,
  - y que correrla dos veces no siga cambiando cosas.
"""

import os
import sys

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from libs.catalogos import CONDICION_CONSUMIDOR_FINAL  # noqa: E402

# Lo que dejo la siembra vieja: las cuatro filas en el default.
BASE_VIEJA = [
    (1, "MONOTRIBUTO", 82, 13, 12),
    (2, "RESP. INSCRIPTO", 81, 13, 12),
    (3, "CONSUMIDOR FINAL", 82, 13, 12),
    (4, "EXENTO", 82, 13, 12),
]


@pytest.fixture
def base_con_tipos(monkeypatch):
    """Una tabla tiporesp con los valores de la siembra vieja."""
    from peewee import SqliteDatabase
    from modelos.Tiporesp import Tiporesp

    db = SqliteDatabase(":memory:")
    Tiporesp._meta.set_database(db)
    db.create_tables([Tiporesp])
    for (idtiporesp, nombre, factura, nc, nd) in BASE_VIEJA:
        Tiporesp.create(idtiporesp=idtiporesp, nombre=nombre, factura=factura,
                        notacredito=nc, notadebito=nd)
    yield db
    Tiporesp._meta.set_database(_base_original())


def _base_original():
    from modelos.ModeloBase import db
    return db


def _migracion():
    from controladores.MigracionBaseDatos import MigracionBaseDatos
    return MigracionBaseDatos.__new__(MigracionBaseDatos)


def _condiciones():
    from modelos.Tiporesp import Tiporesp
    return {t.nombre: t.condicion_iva_receptor_id for t in Tiporesp.select()}


def _poner(nombre, valor):
    from modelos.Tiporesp import Tiporesp
    t = Tiporesp.get(Tiporesp.nombre == nombre)
    t.condicion_iva_receptor_id = valor
    t.save()


def test_corrige_los_que_quedaron_en_el_default(base_con_tipos):
    _migracion().CorregirCondicionIvaReceptor()
    condiciones = _condiciones()
    assert condiciones["MONOTRIBUTO"] == 6
    assert condiciones["RESP. INSCRIPTO"] == 1
    assert condiciones["EXENTO"] == 4


def test_no_toca_el_consumidor_final(base_con_tipos):
    """Su condicion correcta ES 5, asi que tiene que quedar como estaba."""
    _migracion().CorregirCondicionIvaReceptor()
    assert _condiciones()["CONSUMIDOR FINAL"] == CONDICION_CONSUMIDOR_FINAL


def test_no_pisa_lo_que_alguien_ya_cambio_a_mano(base_con_tipos):
    """Un Cliente del Exterior puesto a mano se respeta.

    Este es el punto de la correccion: el default 5 es indistinguible de un 5
    puesto a mano, pero un valor distinto si se distingue, y ahi no se decide
    nada desde codigo.
    """
    _poner("RESP. INSCRIPTO", 9)
    _migracion().CorregirCondicionIvaReceptor()
    assert _condiciones()["RESP. INSCRIPTO"] == 9


def test_un_tipo_que_el_catalogo_no_conoce_queda_como_esta(base_con_tipos):
    from modelos.Tiporesp import Tiporesp
    Tiporesp.create(idtiporesp=9, nombre="ALGO QUE HIZO EL USUARIO",
                    factura=82, notacredito=13, notadebito=12)
    _migracion().CorregirCondicionIvaReceptor()
    assert _condiciones()["ALGO QUE HIZO EL USUARIO"] == CONDICION_CONSUMIDOR_FINAL


def test_correrla_dos_veces_no_cambia_nada(base_con_tipos):
    _migracion().CorregirCondicionIvaReceptor()
    primera = _condiciones()
    _migracion().CorregirCondicionIvaReceptor()
    assert _condiciones() == primera
