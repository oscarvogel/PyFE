# coding=utf-8
"""Prueba 1: autenticacion contra ARCA. NO emite nada.

Corre el DiagnosticoAfip desde el entorno de prueba, asi que lo unico que
puede pasar es autenticarse y pedir un comprobante de prueba (Dummy). Si esto
anda, el certificado y la clave sirven y la maquina tiene salida.

Esto va antes de emitir a proposito: si el certificado esta vencido o la clave
no corresponde, AFIP lo dice en esta etapa con un mensaje claro, y no hace
falta gastar un numero de comprobante para enterarse.
"""
from __future__ import print_function

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTORNO = os.path.join(RAIZ, "_prueba_facturacion")

if not os.path.isdir(ENTORNO):
    print("El entorno de prueba no existe. Corré primero:")
    print("    python tools/armar_prueba_facturacion.py")
    sys.exit(1)

# LeerIni arma la ruta del sistema.ini con os.getcwd(), asi que el proceso
# tiene que correr DENTRO del entorno de prueba para no leer el del repo
# (que esta en produccion con datos de un cliente real).
os.chdir(ENTORNO)
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
sys.argv = [sys.argv[0]]

from libs.Utiles import LeerIni  # noqa: E402
from libs.instalacion import cuit_emisor  # noqa: E402
from controladores.DiagnosticoAfip import DiagnosticoAfip  # noqa: E402

print("=== ENTORNO DE PRUEBA ===")
print("carpeta   : {}".format(ENTORNO))
print("sistema.ini: {}".format(os.path.abspath("sistema.ini")))
print("base      : sqlite  ({})".format(os.path.abspath("sistema.db")
                                       if os.path.exists("sistema.db")
                                       else "se crea al arrancar"))
print("modo      : {}".format("HOMOLOGACION" if LeerIni("homo") == "S"
                              else "PRODUCCION  <-- esto NO deberia pasar"))
print("CUIT      : {}".format(cuit_emisor()))
print("cert      : {}".format(LeerIni(clave="cert_homo", key="WSAA")))
print("clave     : {}".format(LeerIni(clave="privatekey_homo", key="WSAA")))
print("")

if LeerIni("homo") != "S":
    print("CORTANDO: el entorno de prueba tiene que estar en homologacion.")
    sys.exit(1)

print("=== DIAGNOSTICO CONTRA ARCA ===")
diagnostico = DiagnosticoAfip()
pasos = diagnostico.ejecutar(al_avanzar=lambda etapa: print("  ... {}".format(etapa)))
print("")

for paso in pasos:
    print("{} {}".format("OK   " if paso.ok else "ERROR", paso.nombre))
    for linea in str(paso.detalle).splitlines():
        print("        {}".format(linea))

print("")
print("Titulo   : {}".format(diagnostico.titulo(pasos)))
consejo = diagnostico.que_hacer(pasos)
if consejo:
    print("Que hacer: {}".format(consejo))
    sys.exit(1)

print("RESULTADO: la autenticacion funciono. Se puede emitir en homologacion.")
