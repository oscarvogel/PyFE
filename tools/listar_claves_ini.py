# coding=utf-8
"""Lista las claves del sistema.ini que el codigo realmente lee.

Sirve para armar una configuracion de prueba completa: si falta una clave, la
pantalla que la usa se cae al abrirla. Ya paso con [WSFEv1] cat_iva.
"""
from __future__ import print_function

import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

PATRONES = {
    "WSFEv1": re.compile(r"clave='([A-Za-z_0-9]+)'\s*,\s*key='WSFEv1'"),
    "FACTURA": re.compile(r"clave='([A-Za-z_0-9]+)'\s*,\s*key='FACTURA'"),
    "param": re.compile(r"clave='([A-Za-z_0-9]+)'\s*,\s*key='param'"),
    "WSAA": re.compile(r"clave='([A-Za-z_0-9]+)'\s*,\s*key='WSAA'"),
    "RESPALDO": re.compile(r"clave='([A-Za-z_0-9]+)'\s*,\s*key='RESPALDO'"),
}

# Las que se convierten con int()/float() sin proteccion: un valor vacio o con
# un typo ahi tumba la pantalla entera.
NUMERICAS = re.compile(r"(int|float)\(\s*LeerIni\(")


def claves_por_seccion():
    resultado = {seccion: {} for seccion in PATRONES}
    numericas = []
    for carpeta in ("libs", "vistas", "controladores", "modelos"):
        base = os.path.join(RAIZ, carpeta)
        if not os.path.isdir(base):
            continue
        for nombre in sorted(os.listdir(base)):
            if not nombre.endswith(".py"):
                continue
            ruta = os.path.join(base, nombre)
            with open(ruta, "rb") as f:
                crudo = f.read()
            try:
                texto = crudo.decode("utf-8")
            except UnicodeDecodeError:
                continue
            for seccion, patron in PATRONES.items():
                for m in patron.finditer(texto):
                    resultado[seccion].setdefault(m.group(1), set()).add(
                        "{}/{}".format(carpeta, nombre))
            for i, linea in enumerate(texto.splitlines(), 1):
                if NUMERICAS.search(linea):
                    clave = patron_clave(linea)
                    if clave:
                        numericas.append((clave, "{}/{}:{}".format(
                            carpeta, nombre, i)))
    return resultado, numericas


def patron_clave(linea):
    m = re.search(r"clave='([A-Za-z_0-9]+)'", linea)
    if m:
        return m.group(1)
    m = re.search(r"LeerIni\('([A-Za-z_0-9]+)'", linea)
    if m:
        return m.group(1)
    return None


def main():
    resultado, numericas = claves_por_seccion()

    print("Claves que el codigo lee, por seccion:")
    for seccion in ("param", "WSFEv1", "FACTURA", "WSAA", "RESPALDO"):
        claves = resultado[seccion]
        print("")
        print("  [{}]  {} claves".format(seccion, len(claves)))
        print("    " + ", ".join(sorted(claves)))

    print("")
    print("=" * 70)
    print("Claves convertidas con int()/float() sin proteccion:")
    print("  Una vacia, o con un typo, tumba la pantalla que la usa.")
    for clave, donde in sorted(set(numericas)):
        print("  {:<18} {}".format(clave, donde))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
