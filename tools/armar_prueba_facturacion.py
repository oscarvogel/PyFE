# coding=utf-8
"""Arma un entorno de prueba para emitir facturas de HOMOLOGACION.

Para que sirve
--------------
Probar el camino fiscal completo contra AFIP sin tocar nada real:

  - una base SQLite propia, creada desde cero con los datos maestros
  - un sistema.ini propio, en homologacion (homo = S)
  - los certificados de homologacion que se le Passed por parametro

Por que un entorno aparte y no el sistema.ini del repo
------------------------------------------------------
El sistema.ini del repo esta en PRODUCCION (homo = N) con la razon social y el
CUIT de un cliente real. Emitir contra el, aunque sea de prueba, seria emitir
contra el servicio real de AFIP con datos reales. Este script no lee ni escribe
ese archivo.

Ademas el repo apunta a certificados/vogel_wsass.crt para homologacion, que
VENCIO en 2020: con esa configuracion la emision de prueba no puede funcionar
por mas que la maquina este bien.

Uso
---
    python tools/armar_prueba_facturacion.py
    python tools/armar_prueba_facturacion.py --limpiar
    python tools/armar_prueba_facturacion.py --cert certificados/homo.crt \\
                                            --key  certificados/homo.key
"""
from __future__ import print_function

import argparse
import os
import shutil
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

CARPETA = os.path.join(RAIZ, "_prueba_facturacion")
BASE_NOMBRE = "sistema.db"

# El CUIT con el que se registro el certificado de homologacion. Si el par
# cert/key es otro, hay que pasar --cuit junto con --cert y --key.
CUIT_POR_DEFECTO = "20233472035"


def _eliminar(que):
    if os.path.isdir(que):
        shutil.rmtree(que)
    elif os.path.isfile(que):
        os.remove(que)


def _copiar_arbol(origen, destino):
    if not os.path.isdir(origen):
        print("  ! no existe {}: se omite".format(origen))
        return
    if not os.path.isdir(destino):
        os.makedirs(destino)
    for nombre in os.listdir(origen):
        # data/ trae pablo.db, que es una base de pruebas ajena al producto.
        if nombre.lower().endswith(".db"):
            continue
        origen_item = os.path.join(origen, nombre)
        destino_item = os.path.join(destino, nombre)
        if os.path.isdir(origen_item):
            _copiar_arbol(origen_item, destino_item)
        else:
            shutil.copy2(origen_item, destino_item)


def leer_cuit_del_certificado(ruta_cert):
    """El CUIT con el que esta registrado el certificado.

    Si el certificado no lo dice, no se inventa: el emisor tiene que ser
    exactamente ese, y adivinarlo produce un rechazo de ARCA que no ayuda a
    diagnosticar nada.
    """
    from cryptography import x509

    with open(ruta_cert, "rb") as f:
        cert = x509.load_pem_x509_certificate(f.read())

    cn = cert.subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)
    # El CN suele venir como "CUIT 20233472035" o con los guiones puestos.
    for valor in [c.value for c in cn]:
        solo_digitos = "".join(ch for ch in valor if ch.isdigit())
        if len(solo_digitos) == 11:
            return solo_digitos

    for atributo in cert.subject:
        if "20" in str(atributo.value) or str(atributo.value).isdigit():
            solo_digitos = "".join(ch for ch in str(atributo.value) if ch.isdigit())
            if len(solo_digitos) == 11:
                return solo_digitos
    return ""


def formatear_cuit(cuit):
    if len(cuit) == 11 and cuit.isdigit():
        return "{}-{}-{}".format(cuit[:2], cuit[2:10], cuit[10:])
    return cuit


def escribir_ini(ruta, cuit_emisor, cert_homo, key_homo, pto_vta=1):
    cuit_factura = formatear_cuit(cuit_emisor)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(
            "; Entorno de PRUEBA en homologacion.\n"
            "; Generado por tools/armar_prueba_facturacion.py.\n"
            "; homologacion = S: las facturas que se emiten acá NO existen para\n"
            "; AFIP y no facturas a nadie. No confundir con el sistema.ini real.\n"
            "\n"
            "[param]\n"
            "iniciosistema = {raiz}/\n"
            "nombre_sistema = Asiento (prueba)\n"
            "basedatos = Basedatos\n"
            "usuario = \n"
            "host = localhost\n"
            "homo = S\n"
            "base = sqlite\n"
            "ultima_copia = 00000000\n"
            "email_contador = \n"
            "configurado = S\n"
            "\n"
            "[WSFEv1]\n"
            # 1 = Responsable Inscripto. El CUIT del certificado de
            # homologacion NO es monotributo: ARCA lo rechaza como comprobante
            # 82 (Tique), asi que la prueba se hace como RI, que es lo que el
            # certificado realmente habilita.
            "cat_iva = 1\n"
            "pto_vta = {pto}\n"
            "cuit = {cuit}\n"
            "url_prod = https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL\n"
            "url_homo = https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL\n"
            "cacert = conf/afip_ca_info.crt\n"
            "\n"
            "[WSAA]\n"
            "cert_homo = {cert}\n"
            "privatekey_homo = {key}\n"
            "cert_prod = \n"
            "privatekey_prod = \n"
            "url_prod = https://wsaa.afip.gov.ar/ws/services/LoginCms\n"
            "url_homo = https://wsaahomo.afip.gov.ar/ws/services/LoginCms\n"
            "\n"
            "[FACTURA]\n"
            "empresa = PRUEBA FACTURACION\n"
            "membrete1 = Datos de prueba\n"
            "membrete2 = No es una factura real\n"
            "cuit = {cuit_factura}\n"
            "iibb = \n"
            "iva = Responsable Monotributo\n"
            "inicio = 01-01-2020\n"
            "num_copias = 1\n"
            "venta = grilla\n"
            "\n"
            "[WSCDC]\n"
            "cuit = {cuit}\n"
            "url_prod = https://servicios1.afip.gov.ar/WSCDC/service.asmx?WSDL\n"
            "\n"
            "[RESPALDO]\n"
            "servidor =\n"
            "usuario =\n"
            "clave =\n".format(
                raiz=CARPETA.replace("\\", "/"),
                cuit=cuit_emisor,
                cuit_factura=cuit_factura,
                cert=cert_homo,
                key=key_homo,
                pto=pto_vta,
            )
        )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--limpiar", action="store_true",
                   help="borra el entorno de prueba y sale")
    p.add_argument("--cert", default="certificados/homo.crt",
                   help="certificado de homologacion, relativo a la raiz")
    p.add_argument("--key", default="certificados/homo.key",
                   help="clave privada de homologacion, relativo a la raiz")
    p.add_argument("--cuit", default="",
                   help="CUIT emisor; por defecto se lee del certificado")
    p.add_argument("--pto", type=int, default=1, help="punto de venta")
    args = p.parse_args()

    if args.limpiar:
        _eliminar(CARPETA)
        print("entorno de prueba borrado: {}".format(CARPETA))
        return 0

    cert_origen = os.path.join(RAIZ, args.cert.replace("/", os.sep))
    key_origen = os.path.join(RAIZ, args.key.replace("/", os.sep))

    for ruta, que in ((cert_origen, "certificado"), (key_origen, "clave privada")):
        if not os.path.isfile(ruta):
            print("ERROR: no existe el {} en {}".format(que, ruta))
            return 1

    cuit = args.cuit or leer_cuit_del_certificado(cert_origen)
    if not cuit:
        print("ERROR: no se pudo deducir el CUIT del certificado. Pasalo con --cuit.")
        return 1

    print("certificado : {}".format(args.cert))
    print("clave       : {}".format(args.key))
    print("CUIT emisor : {}  (leido del certificado)".format(formatear_cuit(cuit)))

    _eliminar(CARPETA)
    os.makedirs(CARPETA)

    print("")
    print("armando {}".format(CARPETA))
    _copiar_arbol(os.path.join(RAIZ, "data"), os.path.join(CARPETA, "data"))
    _copiar_arbol(os.path.join(RAIZ, "conf"), os.path.join(CARPETA, "conf"))
    # Las plantillas son el formato del PDF de la factura. Sin ellas
    # GenerarPDF() no encuentra el CSV con los campos y no arma el documento,
    # que es justamente el papel que se le entrega al cliente.
    _copiar_arbol(os.path.join(RAIZ, "plantillas"), os.path.join(CARPETA, "plantillas"))
    _copiar_arbol(os.path.join(RAIZ, "imagenes"), os.path.join(CARPETA, "imagenes"))

    cert_destino = "certificados/" + os.path.basename(cert_origen)
    key_destino = "certificados/" + os.path.basename(key_origen)
    _copiar_arbol(os.path.join(RAIZ, "certificados"),
                  os.path.join(CARPETA, "certificados"))
    for nombre in ("certificado_homologacion.crt", "clave_privada_homo.key",
                   "homo.crt", "homo.key"):
        origen = os.path.join(RAIZ, "certificados", nombre)
        if os.path.isfile(origen):
            shutil.copy2(origen, os.path.join(CARPETA, "certificados", nombre))

    escribir_ini(os.path.join(CARPETA, "sistema.ini"), cuit,
                 cert_destino, key_destino, args.pto)

    print("  sistema.ini     (homo = S, SQLite, CUIT {})".format(cuit))
    print("  data/           maestros para que la base nazca completa")
    print("  conf/           cacert de AFIP")
    print("  plantillas/     formato del PDF de la factura")
    print("  imagenes/       logo y recursos")
    print("  certificados/   par de homologacion")
    print("")
    print("La base {} se crea sola la primera vez que corre la app.".format(BASE_NOMBRE))
    return 0


if __name__ == "__main__":
    sys.exit(main())
