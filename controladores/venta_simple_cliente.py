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
