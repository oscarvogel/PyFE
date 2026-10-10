"""Planes de cuotas por forma de pago (issue #37). Sin Qt: testeable solo."""

from decimal import Decimal


def planes_de_forma_pago(forma_id):
    """[(cuotas, recargo %)] de la forma, ordenados. [] si no tiene planes.

    Nunca revienta: si la tabla no existe (base vieja sin migrar) devuelve [].
    """
    try:
        from modelos.CuotasPago import CuotaPago
        filas = (CuotaPago.select()
                 .where(CuotaPago.formapago == int(forma_id))
                 .order_by(CuotaPago.cuotas))
        return [(int(f.cuotas), Decimal(str(f.recargo or 0))) for f in filas]
    except Exception:
        return []


def recargo_de_plan(forma_id, cuotas_elegidas, recargo_base=0):
    """% de recargo del plan elegido, o el base de la forma si no hay plan.

    `cuotas_elegidas` es el N de cuotas del selector (1 = contado). Si la
    forma no tiene ese plan cargado, se devuelve el recargo base (#9) para
    no dejar el total en cero por un dato que falta.
    """
    try:
        cuotas = int(cuotas_elegidas or 1)
    except Exception:
        cuotas = 1
    for cant, rec in planes_de_forma_pago(forma_id):
        if cant == cuotas:
            return rec
    try:
        return Decimal(str(recargo_base or 0))
    except Exception:
        return Decimal(0)


def es_tarjeta(forma_id):
    """True si la forma tiene flag tarjeta. False ante cualquier duda."""
    try:
        from modelos.Formaspago import Formapago
        fp = Formapago.get_by_id(int(str(forma_id).strip()))
        return bool(int(fp.tarjeta or 0))
    except Exception:
        return False
