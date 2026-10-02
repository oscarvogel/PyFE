# coding=utf-8
"""Agrega a los formatos de factura el campo CUIT.L y el pie de credito.

CUIT.L: el rotulo del CUIT del emisor, que antes venia pegado al dato desde
el codigo ('CUIT: 20179461154'). Ahora el numero va solo y con guiones, y el
rotulo esta en su propio campo, como ya pasa con Fecha, Direccion, Localidad.

creditoSoftware: la linea de pie 'Desarrollo de <empresa> · <sitio> ·
WhatsApp <numero>'. Va en un pie de pagina, no en el bloque del emisor: el
bloque del emisor identifica a quien factura (el cliente); esta linea es un
credito de quien hizo el programa.

    python tools/agregar_rotulo_cuit.py
"""
from __future__ import print_function

import io
import os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLANTILLAS = os.path.join(RAIZ, "plantillas")

NOMBRE_CAMPO = "CUIT.L"
TEXTO_ROTULO = "CUIT:"

# Pie de credito. Se apoya a la izquierda y ocupa lo que hay libre abajo de
# todo, que es la posicion habitual de un credito de software en un
# comprobante: chico, al pie, y sin mezclarse con los datos fiscales.
NOMBRE_PIE = "creditoSoftware"
TAMANIO_PIE = 5
# y del pie, medido sobre el A4 de 297 mm: queda 4 mm de margen abajo.
Y_PIE = 291.0
ALTO_PIE = 4.0


def _posiciones():
    """(archivo, x_inicio_del_valor, y, alto, x_fin) leidos del propio formato."""
    return {
        "factura_marca.csv": (122, 31, 4, 207),
        "factura_qr.csv": (105.6, 32.9, 5, 207),
    }


def agregar(archivo, x_valor, y, alto, x_fin):
    ruta = os.path.join(PLANTILLAS, archivo)
    with io.open(ruta, "r", encoding="utf-8", errors="replace") as f:
        lineas = f.read().splitlines()

    if any(linea.startswith("'" + NOMBRE_CAMPO + "'") for linea in lineas):
        return "ya estaba"

    # El rotulo se apoya contra el valor y mide 24 mm, que es lo que tardan
    # 'CUIT:' y su margen en Arial de 8 a 10 pt.
    ancho_rotulo = 24
    x1 = x_valor - ancho_rotulo - 2
    # La misma fuente, tamano y color que el valor del CUIT de ese formato.
    valor = [l for l in lineas if l.startswith("'CUIT';")]
    if not valor:
        return "no se encontro el campo CUIT"

    # Se copia el estilo del valor y se cambian tipo, posicion y texto.
    partes = valor[0].split(";")
    if len(partes) < 16:
        return "formato inesperado ({} columnas): {}".format(len(partes), valor[0])
    # Las columnas del formato, en el orden en que las lee el generador:
    #   0 campo      1 tipo       2 x1        3 y1        4 x2       5 y2
    #   6 fuente     7 tamano     8 negrita   9 cursiva  10 subray
    #  11 color_fg  12 color_bg  13 alinea   14 texto    15 prioridad
    fuente = partes[6]
    tamano = partes[7]
    estilo = partes[8:13]          # negrita, cursiva, subrayado, fg, bg
    prioridad = partes[15]

    nuevo = ("'{campo}';'T';{x1:.2f};{y:.2f};{x2:.2f};{yf:.2f};{fuente};{tamano};"
             "{e0};{e1};{e2};{e3};{e4};'I';'{texto}';{prio}").format(
        campo=NOMBRE_CAMPO, x1=x1, y=y, x2=x_valor - 2, yf=y + alto,
        fuente=fuente, tamano=tamano,
        e0=estilo[0], e1=estilo[1], e2=estilo[2], e3=estilo[3], e4=estilo[4],
        texto=TEXTO_ROTULO, prio=prioridad)

    # Se inserta justo antes de la linea del valor del CUIT.
    for i, linea in enumerate(lineas):
        if linea.startswith("'CUIT';"):
            lineas.insert(i, nuevo)
            break

    with io.open(ruta, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(lineas) + "\n")
    return nuevo


def agregar_pie(archivo):
    """Agrega la linea de credito al pie del formato."""
    ruta = os.path.join(PLANTILLAS, archivo)
    with io.open(ruta, "r", encoding="utf-8", errors="replace") as f:
        lineas = f.read().splitlines()

    if any(linea.startswith("'" + NOMBRE_PIE + "'") for linea in lineas):
        return "ya estaba"

    # x hasta 150 mm: a 5 pt entra la linea entera sin tocar la columna de
    # totales, que arranca en x=152.
    nuevo = ("'{campo}';'T';10.00;{y:.2f};150.00;{yf:.2f};'Arial';{tam};0;0;0;"
             "0x666666;0xFFFFFF;'I';'';0").format(
        campo=NOMBRE_PIE, y=Y_PIE, yf=Y_PIE + ALTO_PIE, tam=TAMANIO_PIE)

    with io.open(ruta, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(lineas) + "\n" + nuevo + "\n")
    return nuevo


def main():
    for archivo, (x_valor, y, alto, x_fin) in _posiciones().items():
        print("{:<22} CUIT.L -> {}".format(archivo, agregar(archivo, x_valor, y, alto, x_fin)))
        print("{:<22} pie    -> {}".format(archivo, agregar_pie(archivo)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
