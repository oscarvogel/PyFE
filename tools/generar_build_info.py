# coding=utf-8
"""Escribe la identidad del build antes de compilar, y la saca despues.

Que hace
--------
`release.ps1` lo corre antes de `compila.bat` para que la app compilada sepa
que producto es y que version tiene, y lo corre de nuevo al terminar para
dejar el repo como estaba. Es el mismo esquema que usa femag: los valores se
reemplazan temporalmente y en el arbol queda la version de desarrollo.

NO reescribe `libs/build_info.py` desde una plantilla: le cambia las dos
lineas de identidad y verifica despues que quedaran bien. Ese archivo tiene
`manifest_url_for`, `es_build_productivo` y `changelog_url_for`, y perderlas
dejaria la app compilada sin poder consultar actualizaciones.

Por que se reescriben dos archivos
----------------------------------
- `libs/build_info.py` es la que LEE el actualizador al arrancar. Si no
  estuviera el timestamp adentro, la app instalada no podria compararse con
  el manifiesto y nunca avisaria de una actualizacion.
- `version.txt` es la que lee PyInstaller (`--version-file`) y la que muestra
  Windows en Propiedades del .exe. Sin tocarla, el archivo instalado seguiria
  diciendo 0.9.0 mientras el manifiesto dice 2026.10.05.08.37.00, que es
  justamente la confusion que hizo falta este mecanismo para evitar.

Ojo con `version.txt`: NO es un .ini. PyInstaller lo lee con `eval()` y tiene
que ser UNA expresion de Python y nada mas. Agregarle una linea suelta rompe
la compilacion con "Failed to deserialize VSVersionInfo" (esta verificado:
un archivo con timestamp parsea y serializa bien, son 928 bytes de recurso).

Uso
---
    python tools/generar_build_info.py                  # marca el build
    python tools/generar_build_info.py --version 2026.10.05.08.37.00
    python tools/generar_build_info.py --restaurar      # deja desarrollo
    python tools/generar_build_info.py --verificar      # solo informa
"""

from __future__ import print_function

import argparse
import datetime
import io
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ARCHIVO_BUILD_INFO = os.path.join(RAIZ, "libs", "build_info.py")
ARCHIVO_VERSION = os.path.join(RAIZ, "version.txt")

# Defaults de desarrollo. Deben coincidir con lo que hay versionado, y el
# test de contrato lo verifica: si alguien edita a mano uno y no el otro, el
# updater queda leyendo una version de la build anterior.
APP_ID_DESARROLLO = "development"
VERSION_DESARROLLO = "0.0.0.0.0.0"
APP_ID_PRODUCTIVO = "asiento"

VERSION_RE = re.compile(r"^\d{4}\.\d{2}\.\d{2}\.\d{2}\.\d{2}\.\d{2}$")

RE_APP_ID = re.compile(r'^APP_ID\s*=\s*"[^"]*"', re.M)
RE_BUILD_VERSION = re.compile(r'^BUILD_VERSION\s*=\s*"[^"]*"', re.M)


def version_utc_actual():
    """Timestamp UTC con el formato del manifiesto.

    UTC y no hora local: el manifiesto se escribe con `published_at` en UTC y
    comparar una version en hora local contra una en UTC hace que un build
    hecho a las 20:00 de Argentina se published "antes" que uno de ayer.
    """
    return datetime.datetime.utcnow().strftime("%Y.%m.%d.%H.%M.%S")


def _leer(ruta):
    with io.open(ruta, "r", encoding="utf-8") as fh:
        return fh.read()


def _escribir(ruta, texto):
    # UTF-8 sin BOM a proposito: PyInstaller lo lee con eval() de un archivo
    # de texto y un BOM al principio rompe el parseo.
    with io.open(ruta, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(texto)


def _reemplazar_valores(texto, app_id, version):
    """Cambia SOLO las dos lineas de identidad, sobre el archivo que hay.

    No se reescribe el archivo entero, y esa es la parte importante:
    `libs/build_info.py` tiene `manifest_url_for`, `es_build_productivo` y
    `changelog_url_for`. Un release que regenerara el archivo desde una
    plantilla se llevaria esas funciones y la app compilada quedaria sin
    poder consultar actualizaciones, con el build entero pasando los tests
    porque los tests corren contra el archivo versionado y no contra el
    generado.
    """
    texto, n_app = RE_APP_ID.subn('APP_ID = "{}"'.format(app_id), texto, count=1)
    texto, n_version = RE_BUILD_VERSION.subn(
        'BUILD_VERSION = "{}"'.format(version), texto, count=1)

    if n_app != 1 or n_version != 1:
        raise ValueError(
            "libs/build_info.py no tiene APP_ID / BUILD_VERSION con el formato "
            "esperado (encontre {} y {}). No se toca el archivo."
            .format(n_app, n_version))
    return texto


def _verificar(ruta, app_id, version):
    """Relee el archivo y comprueba que quedo lo que tiene que quedar.

    Sin esto, un release terminating mal el generador seguiria adelante,
    compilaria y publicaria, y el problema apareceria en la PC del cliente
    como 'no me avisa de las actualizaciones'.
    """
    texto = _leer(ruta)
    app = re.search(r'^APP_ID\s*=\s*"([^"]*)"', texto, re.M)
    ver = re.search(r'^BUILD_VERSION\s*=\s*"([^"]*)"', texto, re.M)
    if not app or app.group(1) != app_id:
        raise ValueError("{}: APP_ID quedo como {!r}, se esperaba {!r}".format(
            ruta, app.group(1) if app else None, app_id))
    if not ver or ver.group(1) != version:
        raise ValueError("{}: BUILD_VERSION quedo como {!r}, se esperaba {!r}".format(
            ruta, ver.group(1) if ver else None, version))


def escribir_build_info(app_id, version):
    texto = _reemplazar_valores(_leer(ARCHIVO_BUILD_INFO), app_id, version)
    _escribir(ARCHIVO_BUILD_INFO, texto)
    _verificar(ARCHIVO_BUILD_INFO, app_id, version)
    return ARCHIVO_BUILD_INFO


def restaurar_build_info():
    return escribir_build_info(APP_ID_DESARROLLO, VERSION_DESARROLLO)


def _filevers_de(version):
    """Los 4 enteros que Windows necesita en FixedFileInfo.

    El manifiesto tiene 6 componentes (anio.mes.dia.hora.min.seg) pero el
    bloque `ffi` de VSVersionInfo es de 4 DWORD fijos. Se toman anio, mes,
    dia y hora: es el orden en que Windows los muestra, asi que el archivo
    explorador queda ordenado de mas nuevo a mas viejo.
    """
    partes = version.split(".")
    return tuple(int(p) for p in partes[:4])


def escribir_version_txt(version):
    """Pone el timestamp en el archivo que lee PyInstaller."""
    if not VERSION_RE.match(version):
        raise ValueError("Version con formato invalido: {!r}".format(version))
    original = _leer(ARCHIVO_VERSION)
    anio, mes, dia, hora = _filevers_de(version)
    fv = "({}, {}, {}, {})".format(anio, mes, dia, hora)

    texto = original
    texto = re.sub(r"filevers=\([^)]*\)", "filevers=" + fv, texto, count=1)
    texto = re.sub(r"prodvers=\([^)]*\)", "prodvers=" + fv, texto, count=1)
    texto = re.sub(
        r"(u'ProductVersion',\s*u?')[^']*(')",
        lambda m: m.group(1) + version + m.group(2), texto, count=1)
    texto = re.sub(
        r"(u'FileVersion',\s*u?')[^']*(')",
        lambda m: m.group(1) + version + m.group(2), texto, count=1)

    _escribir(ARCHIVO_VERSION, texto)
    return ARCHIVO_VERSION


def restaurar_version_txt():
    """Deja la version de desarrollo en version.txt (0.9.0)."""
    original = _leer(ARCHIVO_VERSION)
    texto = original
    texto = re.sub(r"filevers=\([^)]*\)", "filevers=(0, 9, 0, 0)", texto, count=1)
    texto = re.sub(r"prodvers=\([^)]*\)", "prodvers=(4, 1, 2, 1)", texto, count=1)
    texto = re.sub(
        r"(u'ProductVersion',\s*u?')[^']*(')",
        lambda m: m.group(1) + "0.9.0" + m.group(2), texto, count=1)
    texto = re.sub(
        r"(u'FileVersion',\s*u?')[^']*(')",
        lambda m: m.group(1) + "0.9.0" + m.group(2), texto, count=1)
    _escribir(ARCHIVO_VERSION, texto)
    return ARCHIVO_VERSION


def verificar():
    """Informa que version de build tiene el arbol ahora mismo."""
    texto = _leer(ARCHIVO_BUILD_INFO)
    app_id = re.search(r'APP_ID\s*=\s*"([^"]+)"', texto)
    version = re.search(r'BUILD_VERSION\s*=\s*"([^"]+)"', texto)
    app_id = app_id.group(1) if app_id else "?"
    version = version.group(1) if version else "?"

    estado = "PRODUCTIVO" if app_id == APP_ID_PRODUCTIVO else "desarrollo"
    print("app_id      : {}".format(app_id))
    print("build       : {}".format(version))
    print("estado      : {}".format(estado))
    if app_id == APP_ID_DESARROLLO:
        print("")
        print("En desarrollo el actualizador queda deshabilitado a proposito:")
        print("si no, correr la app desde el repo avisaria de las versiones de")
        print("produccion y abriria el instalador sobre una base de pruebas.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--version", help="timestamp a escribir; por defecto, el de ahora")
    ap.add_argument("--app-id", default=APP_ID_PRODUCTIVO)
    ap.add_argument("--restaurar", action="store_true",
                    help="deja los archivos en su estado de desarrollo")
    ap.add_argument("--verificar", action="store_true",
                    help="solo informa el estado actual")
    args = ap.parse_args(argv)

    if args.verificar:
        return verificar()

    if args.restaurar:
        restaurar_build_info()
        restaurar_version_txt()
        print("Archivos restaurados al estado de desarrollo.")
        return 0

    version = args.version or version_utc_actual()
    if not VERSION_RE.match(version):
        print("Version invalida: {!r}. Se espera yyyy.MM.dd.HH.mm.ss"
              .format(version), file=sys.stderr)
        return 2

    escribir_build_info(args.app_id, version)
    escribir_version_txt(version)
    print("Build marcado: app_id={} version={}".format(args.app_id, version))
    return 0


if __name__ == "__main__":
    sys.exit(main())
