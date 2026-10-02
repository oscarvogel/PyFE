# coding=utf-8
"""Deteccion y escritura de la configuracion de una instalacion nueva.

Va separado de la ventana del asistente a proposito: la logica queda
libre de Qt y se puede probar sin levantar la interfaz.

Detalle importante del orden
----------------------------
El asistente tiene que correr ANTES de importar controladores.Main, que
arranca la cadena de imports que arma la conexion a la base. Por eso
main.py difiere ese import. Este modulo no importa nada de Qt justamente
para poder subirse en medio de esa secuencia.
"""

import os
import sys

from libs.Utiles import GrabarIni, LeerIni

# Claves de la seccion [param]
CLAVES_PARAM = "base", "basedatos", "usuario", "host", "homo", "nombre_sistema"

# Secciones que el asistente escribe
SECCION_FISCAL = "FACTURA"
SECCION_FACTURACION = "WSFEv1"
SECCION_CERT = "WSAA"


def ruta_config():
    """Misma resolucion que usa LeerIni, para no adivinar el archivo."""
    import argparse

    analizador = argparse.ArgumentParser(add_help=False)
    analizador.add_argument("-i", "--inicio", default=os.getcwd())
    analizador.add_argument("-a", "--archivo", default="sistema.ini")
    args, _ = analizador.parse_known_args()
    carpeta = args.inicio or os.getcwd()
    return os.path.join(carpeta, args.archivo)


def es_primer_arranque():
    """True si la instalacion todavia no fue configurada.

    Tres senales, por si alguna falla:
      - no existe el archivo de configuracion (instalador que no lo copio)
      - no esta el tipo de base (no se eligió sqlite ni mysql)
      - no esta la empresa (no se completaron los datos fiscales)
    """
    if not os.path.exists(ruta_config()):
        return True
    if not LeerIni(clave="base"):
        return True
    if not LeerIni(clave="empresa", key=SECCION_FISCAL):
        return True
    return False


def _es_mysql(base):
    return str(base or "").strip().lower() == "mysql"


def guardar_config_inicial(datos, escribir=None):
    """Escribe la configuracion inicial.

    'datos' es el dict que devuelve el asistente. Se puede inyectar una
    funcion de escritura para probar sin tocar el sistema.ini real.

    Devuelve un dict con lo que quedo guardado, para poder avisarle al
    usuario que se guardo y como.
    """
    if escribir is None:
        escribir = lambda clave, key, valor: GrabarIni(  # noqa: E731
            clave=clave, key=key, valor=valor)

    base = datos.get("base", "sqlite")

    escribir("base", "param", base)
    escribir("nombre_sistema", "param", datos.get("nombre_sistema", "PyFE"))
    # Homologacion por defecto: instalar en produccion por error es peor
    # que tener que cambiarlo a mano despues.
    escribir("homo", "param", datos.get("homo", "S"))

    if _es_mysql(base):
        escribir("basedatos", "param", datos.get("basedatos", ""))
        escribir("host", "param", datos.get("host", ""))
        escribir("usuario", "param", datos.get("usuario", ""))
    else:
        # Con sqlite no hay servidor, asi que estos datos sobran.
        escribir("basedatos", "param", datos.get("basedatos", "pyfe"))
        escribir("host", "param", "localhost")
        escribir("usuario", "param", datos.get("usuario", ""))

    # Datos fiscales
    escribir("empresa", SECCION_FISCAL, datos.get("empresa", ""))
    escribir("membrete1", SECCION_FISCAL, datos.get("membrete1", ""))
    escribir("membrete2", SECCION_FISCAL, datos.get("membrete2", ""))
    escribir("cuit", SECCION_FISCAL, datos.get("cuit", ""))
    escribir("iibb", SECCION_FISCAL, datos.get("iibb", ""))
    escribir("inicio", SECCION_FISCAL, datos.get("inicio", "01/01/2000"))
    escribir("num_copias", SECCION_FISCAL, datos.get("num_copias", "1"))
    escribir("venta", SECCION_FISCAL, "grilla")

    # Facturacion
    escribir("cat_iva", SECCION_FACTURACION, datos.get("cat_iva", "6"))
    escribir("pto_vta", SECCION_FACTURACION, datos.get("pto_vta", "1"))
    escribir("url_prod", SECCION_FACTURACION,
             "https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL")
    escribir("url_homo", SECCION_FACTURACION,
             "https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL")
    escribir("cacert", SECCION_FACTURACION, "conf/afip_ca_info.crt")

    # Certificados
    escribir("cert_homo", SECCION_CERT,
             datos.get("cert_homo", "certificados/certificado_homologacion.crt"))
    escribir("cert_prod", SECCION_CERT,
             datos.get("cert_prod", "certificados/certificado_produccion.crt"))
    escribir("privatekey_homo", SECCION_CERT,
             datos.get("privatekey_homo", "certificados/clave_privada_homo.key"))
    escribir("privatekey_prod", SECCION_CERT,
             datos.get("privatekey_prod", "certificados/clave_privada_produccion.key"))
    escribir("url_prod", SECCION_CERT, "https://wsaa.afip.gov.ar/ws/services/LoginCms")
    escribir("url_homo", SECCION_CERT,
             "https://wsaahomo.afip.gov.ar/ws/services/LoginCms")

    if datos.get("password"):
        from libs.secretos import persistir_password_base
        modo = persistir_password_base(datos["password"])
    else:
        modo = None

    return {"base": base, "modo_secreto": modo}
