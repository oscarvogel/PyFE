# coding=utf-8
"""Carga productos de ejemplo en la base de la copia de prueba.

Sirve para ver la pantalla de venta con importes de verdad: una tabla vacia no
muestra si los numeros se leen bien, si los titulos quedan alineados ni si las
columnas se reparten de forma razonable.

Solo toca la base del sandbox, que es una copia vacia.
"""
from __future__ import print_function

import os
import sqlite3
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(RAIZ, "_sandbox_prueba", "sistema.db")

ARTICULOS = [
    ("TORN-0001", "Tornillo hexagonal 1/4 pulg con arandela", "UN", 1250.50, 485000.00, 1),
    ("ARAND-114", "Arandela plana M6 zincada", "UN", 85.90, 103.94, 2),
    ("TUE-880", "Tubo de acero 3/4 pulg x 6m", "UN", 18450.00, 336117.00, 3),
    ("SERV-INST", "Mano de obra - instalacion", "UN", 485000.00, 485000.00, 4),
]


def main():
    if not os.path.isfile(BASE):
        raise SystemExit(
            "No existe la base del sandbox.\nEjecutar antes: "
            "python tools/armar_sandbox.py")
    conexion = sqlite3.connect(BASE)
    cur = conexion.cursor()

    cur.execute("SELECT idimpuesto FROM impuestos ORDER BY idimpuesto")
    impuestos = cur.fetchall()
    idiva = impuestos[0][0] if impuestos else 5
    cur.execute("SELECT idgrupo FROM grupos ORDER BY idgrupo")
    grupos = cur.fetchall()
    idgrupo = grupos[0][0] if grupos else 1

    cur.execute("SELECT COUNT(*) FROM articulos")
    antes = cur.fetchone()[0]

    for codigo, nombre, unidad, precio, concepto, numero in ARTICULOS:
        cur.execute("SELECT idarticulo FROM articulos WHERE codbarraart = ?",
                    (codigo,))
        if cur.fetchone():
            continue
        cur.execute(
            "INSERT INTO articulos (nombre, nombreticket, unidad, idgrupo,"
            " costo, provppal, tipoiva, modificaprecios, preciopub, concepto,"
            " codbarraart) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (nombre, nombre, unidad, idgrupo, precio, 0, idiva, 1, precio,
             concepto, numero))
    conexion.commit()

    cur.execute("SELECT COUNT(*) FROM articulos")
    print("productos en la base de prueba: {} -> {}".format(
        antes, cur.fetchone()[0]))
    conexion.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
