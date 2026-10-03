# coding=utf-8
"""Arma una instalacion de prueba isolada para levantar la app de verdad.

Por que
-------
Para ver la interfaz en pantalla real hay que correr main.py. Pero main.py abre
la base que este en la carpeta de trabajo, y la de este repo esta en modo
produccion (homo = N) con los datos de facturacion reales. No se corre la app
contra esa base ni por un minuto.

Este script arma una carpeta aparte con:
  - un sistema.ini propio, en HOMOLOGACION y con base sqlite
  - una base nueva, vacia
  - enlaces de carpeta (junction) al codigo y a los recursos, que son de solo
    lectura: no se duplican 126 MB ni se corre el riesgo de que el codigo y el
    que se copia se desincronicen

Lo unico que se escribe de verdad dentro del sandbox es lo que la app crea:
sistema.ini, la base, los logs y los PDF/Excel que exporte.

Uso:
    python tools\armar_sandbox.py            # crea _sandbox_prueba
    python tools\armar_sandbox.py --limpiar  # borra el sandbox
"""

from __future__ import print_function

import argparse
import os
import shutil
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SANDBOX = os.path.join(RAIZ, "_sandbox_prueba")

# Carpetas del proyecto que se enlazan: son codigo y recursos de solo lectura.
# data/ es importante: MigracionBaseDatos carga de ahi los datos basicos
# (tipos de documento, formas de pago, impuestos, localidades) y sin esa carpeta
# la app levanta el schema y despues muere al sembrar.
ENLAZAR = [
    "libs", "vistas", "controladores", "modelos", "temas", "imagenes",
    "conf", "plantillas", "data", "pyafipws", "pyafipws.res", "certificados", "dll",
]

CONFIG_SANDBOX = u"""# Instalacion de prueba. Generada por tools/armar_sandbox.py.
# No tocar: esta en homologacion y con una base vacia, a proposito.
#
# Va completa a proposito: si faltara algo, la app abre el asistente de primer
# arranque y hay que llenarlo cada vez. Asi se abre directo a la pantalla
# principal y se puede probar la interfaz sin vueltas.

[param]
base = sqlite
homo = S
nombre_sistema = Asiento - Prueba local
iniciosistema = {carpeta}
ultima_copia = 20261002

[WSFEv1]
# Los nombres de estas claves son los que el codigo lee de verdad. Con otros
# nombres la pantalla se cae: por ejemplo [WSFEv1] cat_iva convertida con
# int() sin proteccion tumba Comprobantes, la consulta de CAE y la de CAEA.
# La lista completa sale de tools/listar_claves_ini.py
cuit = 30111111124
pto_vta = 1
cat_iva = 1
aliasfce = ASIENTO
cacert = conf/afip_ca_info.crt
url_prod = https://wsa.afip.gov.ar/ws/services/

[FACTURA]
empresa = Empresa de Prueba SRL
membrete1 = Direccion de prueba 123
membrete2 = Buenos Aires
cuit = 30-71234567-1
iibb = Exento
iva = Responsable Inscripto
inicio = 01/03/2015
num_copias = 2

[WSAA]
cert_homo = certificados/certificado_homologacion.crt
privatekey_homo = certificados/clave_privada_homologacion.key
cert_prod = certificados/certificado_produccion.crt
privatekey_prod = certificados/clave_privada_produccion.key
url_homo = https://wsa-homo.afip.gov.ar/ws/services/
url_prod = https://wsa.afip.gov.ar/ws/services/

[EMAIL]
smtpserver =
smtpport = 587
smtpusuario =
smtppassword =
"""


def crear_junction(destino, origen):
    """Enlace de carpeta en Windows. Se usa mklink a proposito: es lo unico
    que no copia 126 MB ni duplica el codigo."""
    cmd = ['cmd', '/c', 'mklink', '/J', destino, origen]
    proceso = subprocess.run(cmd, capture_output=True, text=True)
    return proceso.returncode == 0


def armar():
    if os.path.exists(SANDBOX):
        print("El sandbox ya existe. Borralo con --limpiar primero.")
        return 1

    os.makedirs(SANDBOX)
    print("sandbox:", SANDBOX)

    # Codigo: solo main.py se copia. El resto va por junction.
    shutil.copy2(os.path.join(RAIZ, "main.py"), os.path.join(SANDBOX, "main.py"))

    for carpeta in ENLAZAR:
        origen = os.path.join(RAIZ, carpeta)
        destino = os.path.join(SANDBOX, carpeta)
        if not os.path.isdir(origen):
            print("  (no existe, se salta)", carpeta)
            continue
        if crear_junction(destino, origen):
            print("  enlazada  ", carpeta)
        else:
            # Sin junctions (o sin permisos): se copia igual. Pesa mas, pero
            # el sandbox tiene que funcionar igual.
            print("  copiada   ", carpeta, "(junction no disponible)")
            shutil.copytree(origen, destino)

    with open(os.path.join(SANDBOX, "sistema.ini"), "w", encoding="utf-8") as f:
        f.write(CONFIG_SANDBOX.format(carpeta=SANDBOX.replace("\\", "/") + "/"))

    # Con una base vacia y migraciones aplicadas, para que la primera pantalla
    # sea la principal y no haya que esperar a que corra el migrador.
    import sqlite3
    base = os.path.join(SANDBOX, "sistema.db")
    conexion = sqlite3.connect(base)
    conexion.close()
    if not _migra(SANDBOX):
        print("  aviso: la migracion no pudo correr; la app la hara al arrancar")
    print("  base nueva y migrada:", os.path.relpath(base, RAIZ))

    # El asistente de primer arranque no debe aparecer: la instalacion esta
    # configurada y solo queremos ver la pantalla principal.
    print("")
    print("Listo. Para levantar la app:")
    print('  cd "{}"'.format(SANDBOX))
    print("  python main.py")
    return 0


def limpiar():
    if not os.path.exists(SANDBOX):
        print("No hay sandbox.")
        return 0
    # Los junctions hay que borrarlos como enlaces, o se borra el codigo real.
    for carpeta in ENLAZAR + ["plantillas", "certificados"]:
        destino = os.path.join(SANDBOX, carpeta)
        if os.path.islink(destino) or os.path.exists(destino) and not os.path.isfile(destino):
            if _es_junction(destino):
                print("  desenlazada", carpeta)
                os.rmdir(destino)
    shutil.rmtree(SANDBOX, ignore_errors=True)
    print("sandbox eliminado")
    return 0


def _es_junction(ruta):
    if not os.path.exists(ruta):
        return False
    try:
        # Un junction reports itself as a reparse point.
        import stat
        st = os.lstat(ruta)
        return bool(st.st_file_attributes & 0x400)  # FILE_ATTRIBUTE_REPARSE_POINT
    except (OSError, AttributeError):
        return False


def _migra(carpeta):
    """Crea las tablas y corre las migraciones, sin levantar la ventana.

    Se hace aca para que al abrir la app la base este lista y la primera
    pantalla sea la principal. Si falla, la app lo vuelve a hacer al arrancar
    igual, asi que no es critico.

    Hace falta una QApplication: parte del codigo de migracion toca widgets
    (por ejemplo para pedir un dato faltante) y sin ella PyQt se queja.
    """
    import subprocess
    import sys as _sys
    guion = (
        "import os, sys\n"
        "os.chdir({carpeta!r})\n"
        "sys.path.insert(0, {carpeta!r})\n"
        "os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')\n"
        "from PyQt5.QtWidgets import QApplication\n"
        "app = QApplication(sys.argv)\n"
        "from controladores.MigracionBaseDatos import MigracionBaseDatos\n"
        "MigracionBaseDatos().Migrar()\n"
    ).format(carpeta=carpeta)
    proceso = subprocess.run(
        [_sys.executable, "-c", guion],
        cwd=carpeta, capture_output=True)
    if proceso.returncode != 0:
        detalle = (proceso.stderr or b"").decode("utf-8", "replace").strip()
        if detalle:
            print("  detalle:", detalle.splitlines()[-1][:140])
    return proceso.returncode == 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--limpiar", action="store_true")
    args = p.parse_args()
    if args.limpiar:
        return limpiar()
    return armar()


if __name__ == "__main__":
    sys.exit(main())
