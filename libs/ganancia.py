# coding=utf-8
"""El porcentaje de ganancia del articulo (`incre1`) y el precio que produce.

Por que vive aca y no en la vista
---------------------------------
La misma disciplina que `libs/importararticulos.py`: la parte que decide si un
costo de 10142 con 40% de ganancia tiene que dejar un precio de 14198.80 no
importa Qt, asi que va en un modulo sin PyQt5 y se puede probar sin QApplication,
que es la unica forma de saber que anda.

Que es incre1
-------------
El porcentaje de ganancia de la lista 1. 40 significa 40%: el precio al publico
sale de costo x 1.40. Es un PORCENTAJE y no el multiplicador 1.4 que usa la
columna GANANCIA del importador. Son la misma idea con distinta escala, y en el
ABM va la que el operador entiende de una vistazo: 14198.80 sobre un costo de
10142 es "40% de ganancia" y no "1.4".

Que significa que valga cero
---------------------------
Cero (o menos) significa "no hay regla cargada": el precio al publico se tipea a
mano, como se ha tipeado siempre. No es "vender a costo". Es el estado en el que
estan todos los articulos que ya existian en la base, y por eso agregar esta
columna no cambia el comportamiento de ninguno de ellos: si el operador no
carga un porcentaje, el precio sigue siendo el que estaba, y el campo de precio
sigue editable.

Un Spinner no puede estar vacio, asi que el cero es la unica forma de decir
"apagado". Un operador que quiere vender a costo tipea el costo como precio.
"""

from decimal import Decimal

# El redondeo es el de `preciopub`, que es DECIMAL(12,4): si se calculara con
# mas decimales el numero entra y el motor lo guarda truncado, y el operador ve
# un precio distinto del que se calculo. Mismo criterio que
# `importararticulos.calcula_precio`.
CUATRO_DECIMALES = Decimal("0.0001")

CIEN = Decimal("100")
UNO = Decimal("1")


def margen_activo(incre1):
    """Si hay un porcentaje cargado que gobierne el precio.

    Falso para 0, para None y para los negativos. Un porcentaje negativo se
    trata como "no cargado" y no como una orden de vender por debajo del costo:
    descontar es una decision comercial que se toma en el precio, no escribiendo
    un numero negativo en un campo de porcentaje.
    """
    if incre1 is None:
        return False
    try:
        return Decimal(str(incre1)) > 0
    except Exception:
        return False


def precio_desde_incre1(costo, incre1):
    """El precio al publico: costo x (1 + incre1/100), a 4 decimales.

    Devuelve None si no hay costo, para que el que llama decida que hacer en vez
    de inventar un 0 y guardar un producto con precio cero sin querer.

    OJO: esta funcion no consulta si el margen esta activo. Con incre1 en 0
    devuelve el costo, que es la cuenta correcta pero no el comportamiento que
    se quiere: el precio a mano lo decide el operador. El que llama tiene que
    preguntar con `margen_activo` primero, como hace la vista.
    """
    if costo is None:
        return None

    d_costo = Decimal(str(costo))
    d_incre1 = Decimal(str(incre1 or 0))

    factor = UNO + (d_incre1 / CIEN)
    return (d_costo * factor).quantize(CUATRO_DECIMALES)