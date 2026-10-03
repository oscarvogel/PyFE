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
