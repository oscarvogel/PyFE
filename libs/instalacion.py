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

from libs.Utiles import GrabarIni, LeerIni, formato_cuit, validar_cuit
from libs.build_info import nombre_build

# Claves de la seccion [param]
CLAVES_PARAM = "base", "basedatos", "usuario", "host", "homo", "nombre_sistema"

# Secciones que el asistente escribe
SECCION_FISCAL = "FACTURA"
SECCION_FACTURACION = "WSFEv1"
SECCION_CERT = "WSAA"


def ruta_config():
    """El sistema.ini que se lee y se escribe.

    La resolucion vive en libs/rutas.py y la comparte con LeerIni/GrabarIni.
    Antes estaba duplicada aca, y por eso este modulo podia mirar un archivo y
    GrabarIni otro.
    """
    import argparse

    from libs import rutas

    analizador = argparse.ArgumentParser(add_help=False)
    analizador.add_argument("-i", "--inicio", default=None)
    analizador.add_argument("-a", "--archivo", default=rutas.NOMBRE_INI)
    args, _ = analizador.parse_known_args()
    carpeta = args.inicio or rutas.carpeta_datos()
    return os.path.join(carpeta, args.archivo)


def _instalacion_ya_configurada():
    """True si la configuracion tiene datos reales, no los de la plantilla.

    Se usa para las instalaciones anteriores al marcador 'configurado':
    si ya tenian base y empresa cargadas no hay que volver a preguntarles
    nada, solo marcar la instalacion como configurada.
    """
    base = LeerIni(clave="base")
    empresa = LeerIni(clave="empresa", key=SECCION_FISCAL)

    if not base or not empresa:
        return False

    # La plantilla trae estos textos de ejemplo. Si siguen sin tocar, la
    # instalacion esta sin configurar.
    if empresa.strip().lower() in ("", "razon social", "nombre de la empresa"):
        return False
    if base.strip().lower() not in ("sqlite", "mysql"):
        return False
    return True


def es_primer_arranque():
    """True si la instalacion todavia no fue configurada.

    No se deduce solo de los valores: la plantilla trae 'base = sqlite' y
    'empresa = Razon Social' de ejemplo, asi que si uno se guiara por eso
    creeria que una instalacion nueva ya esta configurada.

    El mecanismo es un marcador explicito ([param] configurado = S) que
    escribe el asistente. Las instalaciones anteriores a este cambio no
    lo tienen, asi que seAcceptedan tal cual si ya tienen datos reales,
    para no volver a mostrarles el asistente.
    """
    if not os.path.exists(ruta_config()):
        return True

    if str(LeerIni(clave="configurado", key="param")).strip().upper() == "S":
        return False

    return not _instalacion_ya_configurada()


def marcar_instalacion_configurada():
    """Pone el marcador en una instalacion que ya venia funcionando.

    Se llama al arrancar: asi las instalaciones viejas quedan marcadas
    y el asistente no vuelve a aparecer nunca mas.
    """
    try:
        GrabarIni(clave="configurado", key="param", valor="S")
    except Exception:
        pass


def _es_mysql(base):
    return str(base or "").strip().lower() == "mysql"


# -- El CUIT emisor, en un solo lugar ----------------------------------------
#
# Por que existe
# --------------
# El CUIT vivia duplicado en dos claves: [FACTURA] cuit, que es la que ve y
# edita el usuario en Configuracion, y [WSFEv1] cuit, que es la que viaja a
# ARCA en Auth.Cuit (pyafipws/wsfev1.py). El asistente escribia la primera y
# NADIE escribia la segunda, asi que en una instalacion nueva quedaba
# '00000000000', que es lo que trae sistema.ini.example: el usuario completaba
# el asistente y despues no podia emitir. El diagnostico tampoco lo veia,
# porque 00000000000 no esta vacio.
#
# La regla: [FACTURA] cuit es la clave canonica (es la que el usuario
# controla) y todo lector pasa por cuit_emisor(). La clave vieja se completa
# una sola vez, y solo si no tiene nada real, para no romper instalaciones
# que hoy funcionan.


def _cuit_digitos(valor):
    """11 dígitos, o '' si el valor no tiene forma de CUIT."""
    digitos = "".join(c for c in str(valor or "") if c.isdigit())
    return digitos if len(digitos) == 11 else ""


def cuit_es_real(valor):
    """True si el valor parece un CUIT de verdad.

    11 dígitos, no todos ceros, y el dígito verificador cierra. El 'todos
    ceros' va aparte porque 00000000000 tiene dígito verificador válido y
    sin esta comprobación pasaría por un CUIT real: es justamente el valor
    con el que queda una instalación sin configurar.
    """
    digitos = _cuit_digitos(valor)
    if not digitos or digitos == "0" * 11:
        return False
    return validar_cuit(formato_cuit(digitos))


def cuit_emisor(leer=None):
    """El CUIT con el que se emite, sólo dígitos (lo que espera ARCA).

    Devuelve '' si no hay ningún CUIT utilizable, para que el chequeo de
    instalación lo reporte en vez de mandar ceros a ARCA.
    """
    if leer is None:
        leer = LeerIni

    de_empresa = leer(clave="cuit", key=SECCION_FISCAL)
    de_facturacion = leer(clave="cuit", key=SECCION_FACTURACION)

    if cuit_es_real(de_empresa):
        return _cuit_digitos(de_empresa)
    if cuit_es_real(de_facturacion):
        return _cuit_digitos(de_facturacion)
    return ""


def normalizar_cuit_emisor(grabar=None, leer=None):
    """Deja de acuerdo las dos claves del CUIT. Se corre una vez al arrancar.

    No pisa ningún dato: escribe sólo en la clave que está vacía o tiene un
    valor de relleno. Si las dos tienen un CUIT real y distinto, no toca
    ninguna y lo avisa, porque elegir una en ese caso es descartar la otra y
    no hay forma de saber cuál es la correcta sin preguntarle al usuario.

    Devuelve un dict con lo que hizo, para poder avisar y para testear:
    ``{'estado': 'ok'|'discrepan'|'falta'|'nada', 'cuit': str}``.
    """
    if grabar is None:
        grabar = lambda clave, key, valor: GrabarIni(  # noqa: E731
            clave=clave, key=key, valor=valor)
    if leer is None:
        leer = LeerIni

    de_empresa = leer(clave="cuit", key=SECCION_FISCAL)
    de_facturacion = leer(clave="cuit", key=SECCION_FACTURACION)

    real_empresa = cuit_es_real(de_empresa)
    real_facturacion = cuit_es_real(de_facturacion)

    if real_empresa and real_facturacion:
        if _cuit_digitos(de_empresa) == _cuit_digitos(de_facturacion):
            return {"estado": "nada", "cuit": _cuit_digitos(de_empresa)}
        # Dos CUIT reales y distintos: no se elige uno. Se avisa.
        return {"estado": "discrepan",
                "cuit": _cuit_digitos(de_empresa),
                "conflicto": "{} vs {}".format(
                    _cuit_digitos(de_empresa), _cuit_digitos(de_facturacion))}

    if real_empresa:
        if not _grabar_queda(grabar, "cuit", SECCION_FACTURACION,
                             _cuit_digitos(de_empresa)):
            return {"estado": "nada", "cuit": _cuit_digitos(de_empresa),
                    "sin_guardar": True}
        return {"estado": "ok", "cuit": _cuit_digitos(de_empresa),
                "completada": SECCION_FACTURACION}

    if real_facturacion:
        if not _grabar_queda(grabar, "cuit", SECCION_FISCAL,
                             formato_cuit(_cuit_digitos(de_facturacion))):
            return {"estado": "nada", "cuit": _cuit_digitos(de_facturacion),
                    "sin_guardar": True}
        return {"estado": "ok", "cuit": _cuit_digitos(de_facturacion),
                "completada": SECCION_FISCAL}

    return {"estado": "falta", "cuit": ""}


def _grabar_queda(grabar, clave, key, valor):
    """Escribe la clave y devuelve si se pudo.

    Esta correccion es un arreglo, no un requisito: si la escritura falla
    (una carpeta de solo lectura, un disco lleno) la app tiene que abrir igual
    y avisar. Antes el error subia y mataba el arranque entero.
    """
    try:
        grabar(clave, key, valor)
        return True
    except Exception as error:
        print("No se pudo guardar {} en [{}]: {}".format(
            clave, key, type(error).__name__))
        return False


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

    # Marcador de 'ya configurado'. Sin esto el asistente se volveria a
    # mostrar en cada arranque.
    escribir("configurado", "param", "S")

    escribir("base", "param", base)
    escribir("nombre_sistema", "param", datos.get("nombre_sistema", nombre_build()))
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
