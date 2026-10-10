from dataclasses import dataclass


@dataclass(frozen=True)
class ClienteVentaSimple:
    nombre: str
    documento: str
    tipo_doc_afip: int
    es_consumidor_final: bool


def cliente_consumidor_final():
    return ClienteVentaSimple(
        nombre="Consumidor Final",
        documento="",
        tipo_doc_afip=99,
        es_consumidor_final=True,
    )


def id_cliente_consumidor_final():
    """Id del cliente generico CONSUMIDOR FINAL, o None si no existe.

    La venta rapida lo necesita al emitir con el tilde de consumidor
    final: la factura B guarda un cliente real (cabfact.cliente es FK y
    Validacion() exige el campo), y este es el registro semilla para eso
    (creatablas.py, data/clientes.csv).

    Se busca por NOMBRE y tipo, no por id: los ids varian por instalacion.
    El id 1 se prueba primero porque es el de la siembra, pero solo vale
    si su tipo es Consumidor Final.
    """
    from modelos.Clientes import Cliente
    from modelos.Tiporesp import Tiporesp
    try:
        tipos_cf = [t.idtiporesp for t in Tiporesp.select()
                    if (t.nombre or "").strip().upper() == "CONSUMIDOR FINAL"]
    except Exception:
        return None
    if not tipos_cf:
        return None
    try:
        primero = Cliente.get_or_none(Cliente.idcliente == 1)
        if (primero is not None and primero.tiporesp_id in tipos_cf
                and (primero.nombre or "").strip().upper() == "CONSUMIDOR FINAL"):
            return primero.idcliente
    except Exception:
        pass
    try:
        # El nombre se compara en Python y no en SQL para no depender de
        # como cada base compara mayusculas y espacios: son pocos.
        candidatos = (Cliente.select()
                      .where(Cliente.tiporesp.in_(tipos_cf))
                      .order_by(Cliente.idcliente))
        for candidato in candidatos:
            if (candidato.nombre or "").strip().upper() == "CONSUMIDOR FINAL":
                return candidato.idcliente
    except Exception:
        pass
    return None
