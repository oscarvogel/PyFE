from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


CENTAVOS = Decimal("0.01")


@dataclass(frozen=True)
class RenglonVenta:
    codigo: str
    detalle: str
    cantidad: Decimal
    precio_unitario: Decimal
    iva: Decimal


@dataclass(frozen=True)
class TotalesVenta:
    subtotal: Decimal
    iva: Decimal
    total: Decimal


def _moneda(valor):
    return Decimal(valor).quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def aplicar_forma_pago(total, descuento_pct=0, recargo_pct=0):
    """Aplica el recargo/descuento de la forma de pago al total.

    `descuento_pct` y `recargo_pct` son porcentajes (0-100) como los que
    guarda Formapago.descuento / Formapago.recargo. Devuelve
    (total_final, importe_descuento, importe_recargo), todo en moneda.

    Si vienen los dos, se compensan: neto = recargo - descuento.
    Con 0/0 devuelve el total sin cambios.
    """
    base = Decimal(total or 0)
    try:
        desc = Decimal(descuento_pct or 0)
    except Exception:
        desc = Decimal(0)
    try:
        rec = Decimal(recargo_pct or 0)
    except Exception:
        rec = Decimal(0)
    if desc < 0:
        desc = Decimal(0)
    if rec < 0:
        rec = Decimal(0)

    importe_descuento = _moneda(base * desc / Decimal("100")) if desc else Decimal("0.00")
    importe_recargo = _moneda(base * rec / Decimal("100")) if rec else Decimal("0.00")
    total_final = _moneda(base - importe_descuento + importe_recargo)
    return total_final, importe_descuento, importe_recargo


def calcular_totales(renglones, contribuyente_responsable_inscripto=True):
    subtotal = Decimal("0")
    iva_total = Decimal("0")
    total = Decimal("0")

    for renglon in renglones:
        importe_final = Decimal(renglon.cantidad) * Decimal(renglon.precio_unitario)
        total += importe_final

        if contribuyente_responsable_inscripto:
            divisor = Decimal("1") + (Decimal(renglon.iva) / Decimal("100"))
            neto = importe_final / divisor
            iva_total += importe_final - neto
            subtotal += neto
        else:
            subtotal += importe_final

    return TotalesVenta(
        subtotal=_moneda(subtotal),
        iva=_moneda(iva_total),
        total=_moneda(total),
    )
