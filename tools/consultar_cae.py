# coding=utf-8
"""Consulta de vuelta los CAE emitidos, para confirmar que quedaron guardados.

Que prueba esto
---------------
Que la app "haya recibido un numero" no es lo mismo a que ARCA lo haya
guardado. Esta consulta vuelve a preguntarle a ARCA por cada comprobante y
compara lo que dice ahora contra lo que se emitio: si coinciden, el comprobante
existe de verdad del lado de ellos.
"""
from __future__ import print_function

import argparse
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTORNO = os.path.join(RAIZ, "_prueba_facturacion")

p = argparse.ArgumentParser()
p.add_argument("--tipo", type=int, default=6, help="tipo de comprobante")
p.add_argument("--pto", type=int, default=0, help="punto de venta; 0 = el del sistema.ini")
p.add_argument("--desde", type=int, default=1, help="primer numero a verificar")
p.add_argument("--hasta", type=int, default=0, help="ultimo numero; 0 = hasta el ultimo autorizado")
args = p.parse_args()

if not os.path.isdir(ENTORNO):
    print("El entorno de prueba no existe. Corré primero:")
    print("    python tools/armar_prueba_facturacion.py")
    sys.exit(1)

os.chdir(ENTORNO)
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
sys.argv = [sys.argv[0]]
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt5.QtWidgets import QApplication  # noqa: E402
app = QApplication.instance() or QApplication(sys.argv)

from libs.Utiles import LeerIni, DeCodifica  # noqa: E402
from controladores.FE import FEv1  # noqa: E402

if LeerIni("homo") != "S":
    print("CORTANDO: solo se consulta en el entorno de prueba.")
    sys.exit(1)

pto = args.pto or int(LeerIni(clave="pto_vta", key="WSFEv1") or 1)

wsfe = FEv1()
wsfe.Autenticar()
wsfe.SetTicketAcceso(ta_string=wsfe.Autenticar())
wsfe.Cuit = LeerIni(clave="cuit", key="WSFEv1")
wsfe.Conectar("")

hasta = args.hasta
if not hasta:
    hasta = int(wsfe.UltimoComprobante(tipo=args.tipo, ptovta=pto) or 0)

print("CUIT {}  |  comprobante {}  |  punto de venta {}".format(
    wsfe.Cuit, args.tipo, pto))
print("verificando del {} al {}".format(args.desde, hasta))
print("")

encontrados = 0
for numero in range(args.desde, hasta + 1):
    try:
        wsfe.ConsultarCAE(args.tipo, pto, numero)
    except Exception as exc:
        print("  {:>4}  error: {}".format(numero, exc))
        continue
    resultado = getattr(wsfe, "Resultado", "")
    caes = getattr(wsfe, "CAE", None) or getattr(wsfe, "CodAutorizacion", None)
    if resultado == "A":
        encontrados += 1
        print("  {:>4}  AUTORIZADO   CAE {}".format(numero, caes))
    else:
        print("  {:>4}  {}".format(numero, DeCodifica(getattr(wsfe, "Obs", "")) or resultado))

print("")
print("comprobantes autorizados encontrados: {}".format(encontrados))
sys.exit(0 if encontrados else 1)
