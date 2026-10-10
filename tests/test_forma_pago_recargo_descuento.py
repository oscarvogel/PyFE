"""Issue #9: la forma de pago puede traer recargo o descuento %.

Formapago.descuento / Formapago.recargo son porcentajes. Hasta ahora se
guardaban en la base pero nunca se aplicaban al total.
"""
from decimal import Decimal

from controladores.venta_simple_totales import aplicar_forma_pago


def test_sin_recargo_ni_descuento_devuelve_igual():
    total, desc, rec = aplicar_forma_pago(Decimal("1000.00"), 0, 0)
    assert total == Decimal("1000.00")
    assert desc == Decimal("0.00")
    assert rec == Decimal("0.00")


def test_recargo_10_porciento_cuenta_corriente():
    # El caso de data/formapago.csv: CUENTA CORRIENTE recargo 10.
    total, desc, rec = aplicar_forma_pago(Decimal("1000.00"), 0, 10)
    assert rec == Decimal("100.00")
    assert desc == Decimal("0.00")
    assert total == Decimal("1100.00")


def test_descuento_15_porciento_tarjeta():
    total, desc, rec = aplicar_forma_pago(Decimal("1000.00"), 15, 0)
    assert desc == Decimal("150.00")
    assert total == Decimal("850.00")


def test_redondea_a_centavos():
    total, _, rec = aplicar_forma_pago(Decimal("100.00"), 0, Decimal("10.555"))
    # 10.555 -> 10.56 por redondeo half up.
    assert rec == Decimal("10.56")
    assert total == Decimal("110.56")


def test_valores_rotos_no_rompen_el_total():
    total, _, _ = aplicar_forma_pago(Decimal("500.00"), None, None)
    assert total == Decimal("500.00")
    total, _, _ = aplicar_forma_pago(Decimal("500.00"), -5, -10)
    assert total == Decimal("500.00")
