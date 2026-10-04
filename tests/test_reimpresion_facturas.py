"""La reimpresion tiene que listar las facturas.

El sintoma
----------
Reimpresion de facturas salia vacia, con la base sembrada y las facturas
guardadas. El motivo no estaba en esa pantalla: el filtro de la linea 37 es
`if c.tipocomp.exporta`, y `exporta` estaba en cero para TODOS los tipos de
comprobante porque BitBooleanField guardaba como False el '1' que viene del
CSV.

Este test arma una factura guardada y comprueba que aparece en la lista. Con
el bug, la grilla queda en 0 filas aunque la factura exista.
"""

import os
import sys
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)


class _Falso(object):
    def __init__(self, **atributos):
        self.__dict__.update(atributos)


class _Fila(object):
    """Una fila del grid, como las que arma AgregaItem."""

    def __init__(self):
        self.filas = []

    def AgregaItem(self, items=None):
        self.filas.append(items)

    def setRowCount(self, n):
        pass


@pytest.fixture
def qt():
    from PyQt5.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _factura_de_prueba(tipo_exporta):
    return _Falso(
        fecha="2026-10-04",
        numero="100100000001",
        total=Decimal("25000"),
        idcabfact=1,
        tipocomp=_Falso(codigo=11, nombre="FACTURA C", exporta=tipo_exporta),
    )


def _controlador(qt, monkeypatch, fecha="04/10/2026", cliente="1"):
    import controladores.ReImprimeFactura as MOD

    c = MOD.ReImprimeFacturaController.__new__(MOD.ReImprimeFacturaController)
    c.view = _Falso()
    c.view.gridDatos = _Fila()
    c.view.controles = {
        "cliente": _Falso(text=lambda: cliente),
        "fecha": _Falso(date=lambda: _Falso(toPyDate=lambda: __import__(
            "datetime").date(2026, 10, 4))),
    }
    return c


def _monkey(monkeypatch, facturas):
    import modelos.Cabfact as MC
    import modelos.Tipocomprobantes as MT

    class Consulta(object):
        def join(self, *a, **k):
            return self

        def where(self, *a, **k):
            return self

        def __iter__(self):
            return iter(facturas)

    monkeypatch.setattr(MC.Cabfact, "select",
                        staticmethod(lambda *a, **k: Consulta()))
    return MT


def test_una_factura_c_aparece_en_la_lista(qt, monkeypatch):
    """El caso que reporto el operador: hay facturas y la lista sale vacia."""
    _monkey(monkeypatch, [_factura_de_prueba(True)])
    c = _controlador(qt, monkeypatch)
    c.CargaFacturasCliente()

    assert len(c.view.gridDatos.filas) == 1, \
        "la factura no aparece en la reimpresion"
    assert c.view.gridDatos.filas[0][1] == "100100000001"


def test_un_tique_no_aparece(qt, monkeypatch):
    """El filtro existe para eso: los tiques no se reimprimen desde aca."""
    _monkey(monkeypatch, [_factura_de_prueba(False)])
    c = _controlador(qt, monkeypatch)
    c.CargaFacturasCliente()

    assert c.view.gridDatos.filas == []


def test_sin_cliente_no_consulta_nada(qt, monkeypatch):
    """Sin cliente no hay nada que buscar, y no se toca la base."""
    _monkey(monkeypatch, [_factura_de_prueba(True)])
    c = _controlador(qt, monkeypatch, cliente="")
    c.CargaFacturasCliente()

    assert c.view.gridDatos.filas == []


def test_las_facturas_de_exporta_vienen_por_defecto_del_csv():
    """El '1' del CSV tiene que haber llegado a la base.

    Sin esto, la pantalla de arriba esta bien y la de abajo no, y parece un
    problema de cada una por separado.
    """
    import csv

    ruta = os.path.join(RAIZ, "data", "tipocomprobante.csv")
    with open(ruta, newline="", encoding="utf-8") as f:
        filas = {int(r[0]): int(r[4] or 0)
                 for r in list(csv.reader(f, delimiter=","))[1:] if r and r[0].strip()}

    assert filas[11] == 1, "el CSV no marca FACTURA C como exporta"
    assert filas[1] == 1, "el CSV no marca FACTURA A como exporta"
    assert filas[82] == 0, "el CSV deberia dejar el tique fuera"
