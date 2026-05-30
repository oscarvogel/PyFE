from decimal import Decimal

from controladores.venta_simple_totales import RenglonVenta, calcular_totales


def test_calcula_total_con_precio_final_e_iva_incluido():
    renglones = [
        RenglonVenta(
            codigo="1",
            detalle="Articulo prueba",
            cantidad=Decimal("2"),
            precio_unitario=Decimal("121.00"),
            iva=Decimal("21"),
        )
    ]

    totales = calcular_totales(renglones, contribuyente_responsable_inscripto=True)

    assert totales.subtotal == Decimal("200.00")
    assert totales.iva == Decimal("42.00")
    assert totales.total == Decimal("242.00")
