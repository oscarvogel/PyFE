"""Issue #37: planes de cuotas por tarjeta.

Cada tarjeta define sus planes (cuotas + recargo %). Sin planes vale el
recargo base de la forma (#9).
"""
import os
import sys
from decimal import Decimal

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from tests.ayuda_stock import base_memoria  # noqa: E402

from controladores.forma_pago_cuotas import (es_tarjeta, planes_de_forma_pago,  # noqa: E402
                                             recargo_de_plan)
from controladores.venta_simple_totales import aplicar_forma_pago  # noqa: E402
from modelos.CuotasPago import CuotaPago  # noqa: E402
from modelos.Formaspago import Formapago  # noqa: E402


def _sembrar_tarjetas():
    # base_memoria ya trae EFECTIVO id 1: solo se agregan las tarjetas.
    Formapago.insert_many([
        {"idformapago": 3, "detalle": "VISA", "tarjeta": True},
        {"idformapago": 4, "detalle": "MASTERCARD", "tarjeta": True},
    ]).execute()
    CuotaPago.insert_many([
        {"formapago": 3, "cuotas": 1, "recargo": 0},
        {"formapago": 3, "cuotas": 3, "recargo": 15},
        {"formapago": 3, "cuotas": 6, "recargo": 25},
        {"formapago": 4, "cuotas": 1, "recargo": 0},
    ]).execute()


def test_efectivo_no_tiene_planes():
    with base_memoria():
        _sembrar_tarjetas()
        assert planes_de_forma_pago(1) == []
        assert not es_tarjeta(1)


def test_visa_tiene_sus_tres_planes_ordenados():
    with base_memoria():
        _sembrar_tarjetas()
        assert planes_de_forma_pago(3) == [
            (1, Decimal("0")), (3, Decimal("15")), (6, Decimal("25")),
        ]
        assert es_tarjeta(3)


def test_el_recargo_sale_del_plan_y_no_del_base():
    with base_memoria():
        _sembrar_tarjetas()
        assert recargo_de_plan(3, 3, recargo_base=0) == Decimal("15")
        assert recargo_de_plan(3, 6, recargo_base=0) == Decimal("25")
        assert recargo_de_plan(3, 1, recargo_base=0) == Decimal("0")


def test_sin_plan_para_esa_cuota_vale_el_base():
    with base_memoria():
        _sembrar_tarjetas()
        # VISA no tiene plan de 12: no se inventa un 0, vale el base.
        assert recargo_de_plan(3, 12, recargo_base=10) == Decimal("10")
        # Y sin base tampoco revienta.
        assert recargo_de_plan(1, 3, recargo_base=0) == Decimal("0")


def test_mil_pesos_en_3_pagos_de_visa_da_1150():
    with base_memoria():
        _sembrar_tarjetas()
        rec = recargo_de_plan(3, 3, recargo_base=0)
        total, _, importe = aplicar_forma_pago(Decimal("1000.00"), 0, rec)
        assert importe == Decimal("150.00")
        assert total == Decimal("1150.00")


def test_cuota_rara_no_rompe_el_total():
    with base_memoria():
        _sembrar_tarjetas()
        rec = recargo_de_plan(3, None, recargo_base=0)
        total, _, _ = aplicar_forma_pago(Decimal("1000.00"), 0, rec)
        assert total == Decimal("1000.00")


# -- Los ABM abren y muestran nombres, no ids -------------------------------
#
# OJO: la QApplication tiene que quedar REFERENCIADA mientras dure el modulo
# (fixture con scope module). Si se crea en una funcion y se suelta, CPython
# garbage-collectea el wrapper aunque el objeto C++ siga vivo, y la proxima
# construccion de una vista muere con 0xC0000409 sin backtrace. Es el mismo
# codigo de salida que documenta controladores/VentaSimple.py para los slots
# con firma incorrecta.

import pytest as _pytest


@_pytest.fixture(scope="module")
def app():
    from PyQt5.QtWidgets import QApplication
    aplicacion = QApplication.instance() or QApplication([])
    try:
        from libs.tema import aplicar_tema
        aplicar_tema(aplicacion)
    except Exception:
        pass
    return aplicacion


def test_abm_cuotas_muestra_el_detalle_y_no_revienta(app):
    with base_memoria():
        _sembrar_tarjetas()
        from vistas.ABMCuotasPago import ABMCuotasPagoView
        v = ABMCuotasPagoView()
        assert v.tableView.rowCount() == 4
        detalles = {v.tableView.ObtenerItem(fila=f, col=1)
                    for f in range(v.tableView.rowCount())}
        assert detalles == {"VISA", "MASTERCARD"}, detalles
        v.close()


def test_abm_formas_editar_visa_carga_sus_planes(app):
    with base_memoria():
        _sembrar_tarjetas()
        from vistas.ABMFormasPago import ABMFormasPagoView
        v = ABMFormasPagoView()
        v.show()
        app.processEvents()
        # La fila de VISA es la de id 3: segunda de la grilla (1, 3, 4).
        v.tableView.setCurrentCell(1, 0)
        v.Modifica()
        app.processEvents()
        assert v.gridPlanes.rowCount() == 3
        assert v.controles['tarjeta'].isChecked()
        assert v.gridPlanes.isVisible()
        assert dict(v.planes_editados()) == {1: Decimal("0"),
                                             3: Decimal("15"),
                                             6: Decimal("25")}
        v.close()


def test_abm_formas_sin_tarjeta_esconde_los_planes(app):
    with base_memoria():
        _sembrar_tarjetas()
        from vistas.ABMFormasPago import ABMFormasPagoView
        v = ABMFormasPagoView()
        v.show()
        app.processEvents()
        v.tableView.setCurrentCell(0, 0)  # EFECTIVO
        v.Modifica()
        app.processEvents()
        assert not v.controles['tarjeta'].isChecked()
        assert v.gridPlanes.rowCount() == 0
        assert not v.gridPlanes.isVisible()
        v.close()


def test_abm_formas_guarda_forma_y_planes_juntos(app):
    with base_memoria():
        _sembrar_tarjetas()
        from controladores.ABMFormasPago import ABMFormasPagoController
        c = ABMFormasPagoController()
        c.view.tipo = 'A'
        c.view.controles['detalle'].setText("NARANJA")
        c.view.controles['descuento'].setValue(0)
        c.view.controles['recargo'].setValue(0)
        c.view.controles['ctacte'].setChecked(False)
        c.view.controles['tarjeta'].setChecked(True)
        c.view.controles['mensual'].setChecked(False)
        c.view.gridPlanes.setRowCount(0)
        c.view.gridPlanes.AgregaItem(items=[1, Decimal("0")])
        c.view.gridPlanes.AgregaItem(items=[3, Decimal("20")])
        c.onClickBtnAceptar()
        forma = Formapago.get(Formapago.detalle == "NARANJA")
        assert bool(int(forma.tarjeta or 0))
        assert planes_de_forma_pago(forma.idformapago) == [
            (1, Decimal("0")), (3, Decimal("20"))]
        c.view.close()
