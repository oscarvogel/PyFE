# coding=utf-8
"""Revisa que no queden caracteres CJK o hieroglifos colados en los fuentes.

Varias veces se me colaron caracteres chinos dentro de comentarios y docstrings
al escribir codigo y documentos. No rompen la ejecucion, pero quedan como basura
visible para quien lea el archivo. Este script los encuentra y los muestra con
contexto para poder corregirlos.
"""
from __future__ import print_function

import os
import re
import sys
import unicodedata

RAIZ = None
for _nivel in range(4):
    _candidato = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                               *([".."] * _nivel)))
    if os.path.isfile(os.path.join(_candidato, "main.py")):
        RAIZ = _candidato
        break
if RAIZ is None:
    RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Sin esto el script recorre una carpeta vacia y dice "OK" sin haber mirado
# nada: es peor que no existir, porque parece que limpio.

CARPETAS = ("vistas", "libs", "controladores", "modelos", "tests", "tools", "docs")
SUELTOS = ("main.py", "compila.bat", "installer/verificar_dist.py")


def es_basura(caracter):
    """CJK, hiragana, katakana, hangul y el rango de letras CJK extendidas."""
    cp = ord(caracter)
    return (
        0x3040 <= cp <= 0x30FF      # hiragana + katakana
        or 0x4E00 <= cp <= 0x9FFF   # CJK unificado
        or 0x3400 <= cp <= 0x4DBF   # CJK extension A
        or 0xAC00 <= cp <= 0xD7AF   # hangul
        or 0xFF00 <= cp <= 0xFFEF   # fullwidth
        or 0x3000 <= cp <= 0x303F   # puntuacion CJK
    )


def archivos():
    for carpeta in CARPETAS:
        base = os.path.join(RAIZ, carpeta)
        if not os.path.isdir(base):
            continue
        for raiz, _dirs, files in os.walk(base):
            for nombre in files:
                if nombre.endswith((".py", ".md", ".css", ".bat", ".txt")):
                    yield os.path.join(raiz, nombre)
    for nombre in SUELTOS:
        ruta = os.path.join(RAIZ, nombre)
        if os.path.isfile(ruta):
            yield ruta


def main():
    assert os.path.isdir(os.path.join(RAIZ, "vistas")), (
        "RAIZ apunto a {} y no parece la raiz del proyecto".format(RAIZ))

    hallazgos = []
    archivos_revisados = 0
    for ruta in sorted(archivos()):
        with open(ruta, "rb") as f:
            crudo = f.read()
        try:
            texto = crudo.decode("utf-8")
        except UnicodeDecodeError:
            continue
        archivos_revisados += 1
        for numero, linea in enumerate(texto.splitlines(), start=1):
            if any(es_basura(c) for c in linea):
                limpias = "".join(
                    "?" if es_basura(c) else c for c in linea).strip()
                hallazgos.append("{}:{}: {}".format(
                    os.path.relpath(ruta, RAIZ), numero, limpias[:110]))

    print("archivos revisados:", archivos_revisados)
    if hallazgos:
        print("caracteres fuera de lugar (CJK/hangul): {}".format(len(hallazgos)))
        for h in hallazgos:
            print("  ", h)
        return 1
    print("OK: no hay caracteres CJK ni hangul en los fuentes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
