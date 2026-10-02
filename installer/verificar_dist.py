# coding=utf-8
"""Chequea que la carpeta dist tenga todo lo que la app necesita.

Sirve porque los datos (imagenes, conf) tienen que estar SUELTOS al lado
del .exe: el sistema.ini los referencia con rutas relativas, asi que si
no viajan sueltos la app arranca y falla al mostrar una pantalla.

Uso:  python installer\verificar_dist.py [carpeta]
"""

import os
import sys

CARPETAS_ESPERADAS = {
    "conf": ["afip_ca_info.crt"],
    "imagenes": None,          # cualquiera, pero tiene que haber
    "plantillas": None,
    "certificados": None,      # vacia esta bien: la llena el asistente
    "excel": None,
}

ARCHIVOS_ESPERADOS = [
    "main.exe",
    "sistema.ini.example",
]


def verificar(dist):
    problemas, avisos = [], []

    for nombre in ARCHIVOS_ESPERADOS:
        ruta = os.path.join(dist, nombre)
        if not os.path.exists(ruta):
            problemas.append("falta {}".format(nombre))

    for carpeta, requeridos in CARPETAS_ESPERADAS.items():
        ruta = os.path.join(dist, carpeta)
        if not os.path.isdir(ruta):
            problemas.append("falta la carpeta {}/".format(carpeta))
            continue
        archivos = [f for f in os.listdir(ruta)
                    if os.path.isfile(os.path.join(ruta, f))]
        if requeridos:
            for r in requeridos:
                if r not in archivos:
                    problemas.append("falta {}/{}".format(carpeta, r))
        elif not archivos and carpeta not in ("certificados", "excel"):
            avisos.append("{}/ esta vacia".format(carpeta))

    return problemas, avisos


def main():
    dist = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dist")

    print("Revisando:", dist)
    if not os.path.isdir(dist):
        print("ERROR: no existe. Corrir compila.bat primero.")
        return 1

    problemas, avisos = verificar(dist)

    for a in avisos:
        print("  aviso  :", a)
    for p in problemas:
        print("  FALTA  :", p)

    if problemas:
        print("\nLa distribucion esta incompleta. No empaquetar asi.")
        return 1
    print("\nDistribucion completa: se puede generar el instalador.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
