# coding=utf-8
"""Prueba 3: generar el PDF de una factura, con los mismos calls que la app.

Por que importa
---------------
Autorizar el comprobante es la mitad del trabajo. Despues hay que armar el PDF,
que es el documento que se le entrega al cliente. Si esa parte falla, el
comprobante quedo autorizado en ARCA y el usuario no tiene nada que mostrar:
es el peor resultado posible, porque no se puede deshacer.

Que se prueba y que no
----------------------
Se prueban los llamados a la libreria (pyafipws.pyfepdf sobre fpdf) que hace
controladores/Facturas.py::ImprimeFactura. No se prueba el pegamento de
ImprimeFactura, que necesita la vista entera: lo que se responde aca es si esta
maquina puede fabricar un PDF de factura, que es lo que estaba en duda.
"""
from __future__ import print_function

import os
import sys
import traceback

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTORNO = os.path.join(RAIZ, "_prueba_facturacion")

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


def seccion(titulo):
    print("")
    print("=== {} ===".format(titulo))


seccion("1. ENTORNO DE PDF")
import fpdf  # noqa: E402
print("fpdf           : {} ({})".format(fpdf.__version__, fpdf.__file__))
from pyafipws import pyfepdf  # noqa: E402
print("pyfepdf        : importado")

plantillas = os.path.join(os.getcwd(), "plantillas")
if not os.path.isdir(plantillas):
    print("FALTAN las plantillas en {}".format(plantillas))
    print("Volvé a correr: python tools/armar_prueba_facturacion.py")
    sys.exit(1)
print("plantillas     : ok ({} archivos)".format(len(os.listdir(plantillas))))

seccion("2. ARMAR LA FACTURA EN MEMORIA")
pyfpdf = pyfepdf.FEPDF()
pyfpdf.CUIT = 20233472035

# Esta es la que crea el diccionario interno. Sin ella, AgregarIva y
# AgregarDetalleItem revientan con KeyError.
pyfpdf.CrearFactura(
    concepto=1,
    tipo_doc=96,
    nro_doc="11111111",
    tipo_cbte=6,
    punto_vta=1,
    cbte_nro=6,
    imp_total=9900.00,
    imp_neto=8181.82,
    imp_iva=1718.18,
    fecha_cbte="20261003",
    cae="86400944641465",
    fch_venc_cae="20261013",
    nombre_cliente="CONSUMIDOR FINAL",
    domicilio_cliente="S/NOMBRE",
)
print("CrearFactura   : ok")

for campo, valor in [
        ("empresa", "PRUEBA FACTURACION"),
        ("nombre", "PRUEBA FACTURACION"),
        ("domicilio", "Datos de prueba"),
        ("localidad", "Puerto Rico"),
        ("provincia", "Misiones"),
        ("cuit", "20-23347203-5"),
        ("iibb", "Sin actividad"),
        ("fecha", "03/10/2026"),
        ("comprobante", "Factura B"),
        ("letra", "B"),
        ("numero", "6"),
        ("neto", "8181.82"),
        ("iva", "1718.18"),
        ("total", "9900.00"),
        ("cae", "86400944641465"),
        ("vence_cae", "13/10/2026"),
        ("resultado", "A"),
        ("cliente_nombre", "CONSUMIDOR FINAL"),
        ("cliente_domicilio", "S/NOMBRE"),
        ("cliente_documento", "11111111")]:
    pyfpdf.AgregarDato(campo, valor)

# El pie de credito y el CUIT con guiones, que se agregaron en la etapa de marca.
from libs.Constantes import CREDITO_SOFTWARE  # noqa: E402
from libs.Utiles import formato_cuit  # noqa: E402
pyfpdf.AgregarDato("creditoSoftware", CREDITO_SOFTWARE)
pyfpdf.AgregarDato("CUIT", formato_cuit("20233472035"))

pyfpdf.AgregarIva(5, 8181.82, 1718.18)
pyfpdf.AgregarDetalleItem(0, "", 1, "PRUEBA DE PRODUCTO", 1, 7,
                          8181.82, 0, 5, 1718.18, 8181.82,
                          "", "", "", "", "")
print("datos          : ok (cabecera, alicuota de IVA, un item)")

seccion("3. FORMATO Y PLANTILLA")
formato = os.path.join(plantillas, "factura_qr.csv")
if not os.path.isfile(formato):
    print("FALTA el formato {}".format(formato))
    sys.exit(1)
try:
    print("CargarFormato  : {}".format(pyfpdf.CargarFormato(formato)))
    print("CrearPlantilla : {}".format(pyfpdf.CrearPlantilla("A4", "portrait")))
except Exception:
    print("FALLO:")
    traceback.print_exc(file=sys.stdout)
    sys.exit(1)

# La traduccion de los codigos de alineacion que hace la app real.
from libs import fpdf_compat  # noqa: E402
print("align antiguos  : {} elementos".format(
    sum(1 for e in pyfpdf.template.elements if e.get("align") in ("D", "I"))))
print("normalizados    : {} (align) y {} (fuentes)".format(*fpdf_compat.normalizar_plantilla(pyfpdf)))
print("align restantes : {} elementos con D/I".format(
    sum(1 for e in pyfpdf.template.elements if e.get("align") in ("D", "I"))))

seccion("4. GENERAR EL PDF")
try:
    procesado = pyfpdf.ProcesarPlantilla(1, 24, "izq")
    print("ProcesarPlantilla: {}".format(procesado))
    if not procesado:
        print("  Excepcion: {}".format(
            getattr(pyfpdf, "Excepcion", "").strip()))
        print("  Traceback: {}".format(
            getattr(pyfpdf, "Traceback", "").strip()[-1500:]))
    salida = os.path.join(os.getcwd(), "factura_prueba.pdf")
    pyfpdf.GenerarPDF(salida)
    print("GenerarPDF     : ok")
except Exception:
    print("FALLO al generar el PDF:")
    traceback.print_exc(file=sys.stdout)
    sys.exit(1)

if not os.path.isfile(salida):
    print("GenerarPDF dijo que si, pero el archivo no esta en {}".format(salida))
    sys.exit(1)

tam = os.path.getsize(salida)
with open(salida, "rb") as f:
    cabecera = f.read(5)
print("")
print("PDF GENERADO : {}".format(salida))
print("tamaño       : {} bytes".format(tam))
print("encabezado   : {}".format(cabecera))
if cabecera != b"%PDF-":
    print("ATENCION: no parece un PDF valido.")
    sys.exit(1)
if tam < 2000:
    print("ATENCION: es sospechosamente chico, puede estar casi vacio.")
print("")
print("La generacion de PDF funciona en esta maquina.")
