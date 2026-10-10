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
