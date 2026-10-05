# coding=utf-8
"""Carga productos de ejemplo en la base de la copia de prueba.

Sirve para ver la pantalla de venta con importes de verdad: una tabla vacia no
muestra si los numeros se leen bien, si los titulos quedan alineados ni si las
columnas se reparten de forma razonable.

Solo toca la base del sandbox, que es una copia vacia.

OJO: este script quedo pisado por `tools/sembrar_stock.py`, que siembra lo
mismo y mejor (con minimos, movimientos, un remito y todos los estados que puede
mostrar la columna "Estado"), y ademas se autoverifica. Correr los dos deja
duplicados en el catalogo: nombres iguales con codigos de barra distintos.

Por eso ahora esto delega y nada mas. Queda como atajo para quien ya lo tenia
en un acceso directo, no como una segunda forma de sembrar.
"""
from __future__ import print_function

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)


def main():
    if not os.path.isdir(os.path.join(RAIZ, "_sandbox_prueba")):
        raise SystemExit(
            "No existe la base del sandbox.\nEjecutar antes: "
            "python tools/armar_sandbox.py")

    print("Este script quedo reemplazado por sembrar_stock.py. Delegando...")
    import sembrar_stock

    return sembrar_stock.main()


if __name__ == "__main__":
    raise SystemExit(main())
