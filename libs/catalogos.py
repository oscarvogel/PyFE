# coding=utf-8
"""Los catálogos de IVA, en un solo lugar.

Por que un modulo y no el CSV
-----------------------------
La lista de categorías de IVA vivía en tres lugares que no coincidían: 8 en el
asistente de primer arranque, 3 en el combo de Configuración, y 4 filas en
`data/tiporesp.csv`. Peor: si el `cat_iva` de una instalación era un código que
el combo no tenía, al abrir Configuración y guardar, el combo se vaciaba y
`cat_iva` quedaba en blanco (ver tests/test_catalogos_iva.py).

El CSV sigue siendo el que llena la base, pero la lista de référence es esta, y
un test obliga a que el CSV no se quede atrás.

De dónde salen los códigos
-------------------------
Condición frente al IVA del receptor, según el anexo 3.1 del manual del
web service de ARCA (WS BFEV1). Son 10, no 8: al asistente le faltaban el 7
(Sujeto No Categorizado) y el 16 (Monotributo Trabajador Independiente).

Ojo con la diferencia entre dos cosas que se parecían una sola:

* `WSFEv1.cuit` y `WSFEv1.cat_iva` son del EMISOR (esta empresa).
* `tiporesp.condicion_iva_receptor_id` es del RECEPTOR (cada cliente).

Los códigos de la condición del receptor y los de la categoría del emisor
comparten el mismo juego de números, que es por eso de que la lista del
asistente servant para las dos. Aquí está el del receptor, que es el que se
manda en cada comprobante.
"""

# codigo -> (nombre, admite comprobante clase A, admite clase B)
CONDICIONES_IVA_RECEPTOR = {
    1: ("IVA Responsable Inscripto", True, False),
    4: ("IVA Sujeto Exento", True, True),
    5: ("Consumidor Final", False, True),
    6: ("Responsable Monotributo", False, True),
    7: ("Sujeto No Categorizado", False, True),
    8: ("Proveedor del Exterior", False, True),
    9: ("Cliente del Exterior", False, True),
    10: ("IVA Liberado - Ley Nº 19.640", True, False),
    13: ("Monotributista Social", False, True),
    16: ("Monotributo Trabajador Independiente Promovido", True, False),
}

CONDICION_CONSUMIDOR_FINAL = 5


def nombre_condicion(codigo):
    """La etiqueta de una condición, o el código si no la conozco."""
    try:
        return CONDICIONES_IVA_RECEPTOR[int(codigo)][0]
    except (KeyError, TypeError, ValueError):
        return str(codigo)


# Que condicion de IVA del receptor va con cada tipo de responsable que siembra
# la base. Antes esto no estaba en ningun lado: `condicion_iva_receptor_id`
# no se cargaba desde el CSV y todas las filas quedaban en el default del
# modelo, que es 5 = Consumidor Final. O sea que a un Responsable Inscripto con
# CUIT se le mandaba 'Consumidor Final' a ARCA.
#
# La clave es el nombre tal cual queda en data/tiporesp.csv.
CONDICION_IVA_POR_TIPO_RESPONSABLE = {
    "MONOTRIBUTO": 6,
    "RESP. INSCRIPTO": 1,
    "CONSUMIDOR FINAL": 5,
    "EXENTO": 4,
}

# Codigos de condicion de IVA del emisor, en el orden en que se ofrecen. Es el
# mismo juego de numeros que el del receptor (ver nota de arriba del modulo).
CATEGORIAS_IVA_EMISOR = [
    (1, "1 - Responsable Inscripto"),
    (4, "4 - Responsable Exento"),
    (5, "5 - Responsable No Inscripto"),
    (6, "6 - Responsable Monotributo"),
    (7, "7 - Sujeto No Categorizado"),
    (8, "8 - Proveedor Exterior"),
    (9, "9 - Cliente Exterior"),
    (10, "10 - IVA Liberado - Ley Nº 19.640"),
    (13, "13 - Responsable Monotributo - Social"),
    (16, "16 - Monotributo Trabajador Independiente"),
]
