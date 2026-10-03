# coding=utf-8
"""Almacenamiento de secretos de PyFE.

Por que este modulo existe
--------------------------
El esquema historico guardaba el password de la base dos veces en el
mismo archivo: el texto cifrado en 'password' y la clave Fernet en
'key'. Los dos juntos descifran el secreto al instante, asi que el
"cifrado" no protegia nada.

Este modulo agrega un backend real (DPAPI de Windows, que ata el
cifrado al usuario y a la maquina) sin romper las instalaciones que ya
tienen el esquema viejo.

Reglas de diseno, en orden de importancia
-----------------------------------------
1. Nunca fail-closed. Si un backend falla, el usuario igual tiene que
   poder arrancar la app. Los errores se reportan para que el que llama
   pueda pedir el dato, nunca para abortar el arranque.
2. Una sola llamada por secreto y cacheada. DPAPI no se puede llamar en
   cada lectura de config: son ~0.2 ms por llamada y se acumulan.
3. El valor guardado lleva prefijo de version ('dpapi:v1:' o
   'fernet:v1:'). Asi una instalacion puede migrar de a poco y siempre
   se sabe con que algoritmo hay que leer.

Portabilidad
------------
DPAPI solo existe en Windows. En otro sistema operativo el modulo no
importa las APIs de Windows y se usa solo el backend Fernet, que es el
mismo que usaba el proyecto antes. Nada mas se rompe.
"""

import base64
import ctypes
import sys
from ctypes import wintypes

PREFIXO_DPAPI = "dpapi:v1:"
PREFIXO_FERNET = "fernet:v1:"

# Entropia opcional: separa el cifrado de otros usos de DPAPI en la misma
# maquina. La tiene que conocer quien descifra.
ENTROPIA = b"PyFE/v1"

ES_WINDOWS = sys.platform == "win32"


class SecretoIlegible(Exception):
    """El valor guardado no se pudo leer con ningun backend."""


# --------------------------------------------------------------------------
# Backend DPAPI (solo Windows, via ctypes: no agrega dependencias)
# --------------------------------------------------------------------------
if ES_WINDOWS:  # pragma: no cover - depende de la plataforma

    class _DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD),
                    ("pbData", ctypes.POINTER(ctypes.c_byte))]

    class _CRYPTPROTECT_PROMPTSTRUCT(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD),
                    ("pszPrompt", wintypes.LPCWSTR),
                    ("ppszDataDescr", ctypes.POINTER(wintypes.LPWSTR)),
                    ("pOptionalPrompt", ctypes.c_void_p),
                    ("dwFlags", wintypes.DWORD)]

    _crypt32 = ctypes.WinDLL("Crypt32.dll", use_last_error=True)
    _kernel32 = ctypes.WinDLL("Kernel32.dll")

    _CryptProtectData = _crypt32.CryptProtectData
    _CryptProtectData.argtypes = [
        ctypes.POINTER(_DATA_BLOB), wintypes.LPCWSTR,
        ctypes.POINTER(_DATA_BLOB), ctypes.c_void_p,
        ctypes.POINTER(_CRYPTPROTECT_PROMPTSTRUCT), wintypes.DWORD,
        ctypes.POINTER(_DATA_BLOB)]
    _CryptProtectData.restype = wintypes.BOOL

    _CryptUnprotectData = _crypt32.CryptUnprotectData
    _CryptUnprotectData.argtypes = [
        ctypes.POINTER(_DATA_BLOB), ctypes.POINTER(wintypes.LPWSTR),
        ctypes.POINTER(_DATA_BLOB), ctypes.c_void_p,
        ctypes.POINTER(_CRYPTPROTECT_PROMPTSTRUCT), wintypes.DWORD,
        ctypes.POINTER(_DATA_BLOB)]
    _CryptUnprotectData.restype = wintypes.BOOL

    _LocalFree = _kernel32.LocalFree
    _LocalFree.argtypes = [ctypes.c_void_p]
    _LocalFree.restype = ctypes.c_void_p

    # Sin UI: si algo pide interaccion, es un error, nunca un dialogo.
    _UI_FORBIDDEN = 0x01

    def _blob(datos):
        buffer = ctypes.create_string_buffer(datos, len(datos))
        return _DATA_BLOB(len(datos),
                          ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte))), buffer

    def disponible_dpapi():
        return True

    def _dpapi_proteger(datos, descripcion="PyFE"):
        entrada, _ = _blob(datos)
        entropia, _ = _blob(ENTROPIA)
        salida = _DATA_BLOB()
        if not _CryptProtectData(ctypes.byref(entrada), descripcion,
                                  ctypes.byref(entropia), None, None,
                                  _UI_FORBIDDEN, ctypes.byref(salida)):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            return ctypes.string_at(salida.pbData, salida.cbData)
        finally:
            _LocalFree(salida.pbData)

    def _dpapi_desproteger(datos):
        entrada, _ = _blob(datos)
        # La entropia tiene que coincidir con la usada al cifrar.
        entropia, _ = _blob(ENTROPIA)
        salida = _DATA_BLOB()
        if not _CryptUnprotectData(ctypes.byref(entrada), None, ctypes.byref(entropia),
                                   None, None, _UI_FORBIDDEN, ctypes.byref(salida)):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            return ctypes.string_at(salida.pbData, salida.cbData)
        finally:
            _LocalFree(salida.pbData)

else:  # pragma: no cover - se ejecuta solo fuera de Windows

    def disponible_dpapi():
        return False

    def _dpapi_proteger(datos, descripcion="PyFE"):
        raise SecretoIlegible("DPAPI solo existe en Windows")

    def _dpapi_desproteger(datos):
        raise SecretoIlegible("DPAPI solo existe en Windows")


# --------------------------------------------------------------------------
# Backend Fernet (portatil, es el que ya usaba el proyecto)
# --------------------------------------------------------------------------
def _fernet_cifrar(texto, clave):
    from cryptography.fernet import Fernet
    return Fernet(clave).encrypt(texto if isinstance(texto, bytes) else texto.encode())


def _fernet_descifrar(datos, clave):
    from cryptography.fernet import Fernet
    if not isinstance(datos, bytes):
        datos = datos.encode()
    return Fernet(clave).decrypt(datos)


# --------------------------------------------------------------------------
# API publica
# --------------------------------------------------------------------------
def cifrar(texto, clave_fernet=None):
    """Devuelve el valor listo para guardar, con su prefijo de version.

    Usa DPAPI cuando esta disponible y hay una clave Fernet usable para
    dejar la migration a la vista; si DPAPI falla por cualquier motivo,
    cae a Fernet sin levantar excepcion.
    """
    if disponible_dpapi():
        try:
            bruto = _dpapi_proteger(texto.encode()
                                    if isinstance(texto, str) else texto)
            return PREFIXO_DPAPI + base64.b64encode(bruto).decode("ascii")
        except Exception:
            # Regla 1: se cae al otro backend, nunca se aborta.
            if clave_fernet is None:
                raise
    if clave_fernet is None:
        raise SecretoIlegible("no hay clave Fernet disponible para cifrar")
    bruto = _fernet_cifrar(texto, clave_fernet)
    return PREFIXO_FERNET + base64.b64encode(bruto).decode("ascii")


def descifrar(valor, clave_fernet=None):
    """Lee un valor guardado, detectando el backend por el prefijo.

    Si el valor no tiene prefijo se trata como el esquema historico y se
    descifra con la clave que se le pase (compatibilidad con lo que hay
    instalado hoy).
    """
    if valor is None:
        raise SecretoIlegible("no hay valor guardado")

    if isinstance(valor, bytes):
        valor = valor.decode("utf-8", "replace")
    valor = valor.strip()
    if not valor:
        raise SecretoIlegible("el valor guardado esta vacio")

    try:
        if valor.startswith(PREFIXO_DPAPI):
            bruto = base64.b64decode(valor[len(PREFIXO_DPAPI):], validate=True)
            return _dpapi_desproteger(bruto).decode("utf-8")

        if valor.startswith(PREFIXO_FERNET):
            if clave_fernet is None:
                raise SecretoIlegible("valor Fernet pero no se paso la clave")
            bruto = base64.b64decode(valor[len(PREFIXO_FERNET):], validate=True)
            return _fernet_descifrar(bruto, clave_fernet).decode("utf-8")

        # Esquema historico: el valor crudo con la clave de al lado.
        if clave_fernet is None:
            raise SecretoIlegible("valor sin prefijo y sin clave para descifrar")
        return _fernet_descifrar(valor, clave_fernet).decode("utf-8")

    except SecretoIlegible:
        raise
    except Exception as e:
        # Se informa el tipo de error real sin filtrar el secreto.
        raise SecretoIlegible(
            "no se pudo descifrar ({}: {})".format(type(e).__name__, e)) from e


def esta_legible(valor, clave_fernet=None):
    """True si el valor se puede leer. Para decidir si hay que pedirlo."""
    try:
        descifrar(valor, clave_fernet)
        return True
    except SecretoIlegible:
        return False


# --------------------------------------------------------------------------
# Resolucion y persistencia del password de la base
# --------------------------------------------------------------------------
# Estas dos son las que usa el resto de la app. Aceptan funciones de
# lectura/escritura inyectadas para poder testearlas sin tocar el
# sistema.ini real.


def resolver_password_base(leer=None):
    """Devuelve el password de la base, o None si hay que pedirlo.

    Orden de resolucion:
      1. lo que se tipeo en este arranque (cache de sesion)
      2. sistema.ini, detectando el backend por el prefijo del valor
      3. None

    El paso 2 acepta las tres formas a la vez, que es lo que hace que la
    migracion sea gradual y no rompa a nadie:
      'dpapi:v1:...'  -> DPAPI (Windows)
      'fernet:v1:...' -> Fernet con la clave 'key' del ini
      'gAAAA...'      -> esquema historico: Fernet con la 'key' del ini
    Si el valor no se puede leer, devuelve None en vez de romper, para que
    el que llama pueda pedirlo.
    """
    from libs.Utiles import LeerIni

    if leer is None:
        leer = LeerIni

    en_sesion = obtener_de_sesion("password_base")
    if en_sesion is not None:
        return en_sesion

    valor = leer(clave="password", key="param")
    if valor is None or not str(valor).strip():
        return None

    clave = leer(clave="key", key="param")
    try:
        return descifrar(valor, clave)
    except SecretoIlegible:
        return None


def persistir_password_base(texto, escribir=None, borrar=None):
    """Guarda el password migrandolo al backend mas seguro disponible.

    Con DPAPI (Windows) escribe 'dpapi:v1:...' y BORRA la clave Fernet
    vieja, que ya no sirve para nada y seria un secreto mas dando vueltas
    en el archivo. Si DPAPI no esta o falla, cae a 'fernet:v1:...' con su
    clave al lado, que es el esquema portable.

    Devuelve 'dpapi' o 'fernet' segun lo que quedo guardado.
    """
    if escribir is None or borrar is None:
        from libs.Utiles import GrabarIni

        if escribir is None:
            escribir = lambda clave, key, valor: GrabarIni(  # noqa: E731
                clave=clave, key=key, valor=valor)
        if borrar is None:
            borrar = lambda clave, key: GrabarIni(  # noqa: E731
                clave=clave, key=key, borrar=True)

    if disponible_dpapi():
        try:
            bruto = _dpapi_proteger(texto.encode()
                                    if isinstance(texto, str) else texto)
            escribir("password", "param",
                     PREFIXO_DPAPI + base64.b64encode(bruto).decode("ascii"))
            borrar("key", "param")
            return "dpapi"
        except Exception:
            # Regla 1: se cae a Fernet sin abortar.
            pass

    from cryptography.fernet import Fernet

    clave = Fernet.generate_key()
    bruto = _fernet_cifrar(texto, clave)
    escribir("password", "param",
             PREFIXO_FERNET + base64.b64encode(bruto).decode("ascii"))
    escribir("key", "param", clave.decode("ascii"))
    return "fernet"


# --------------------------------------------------------------------------
# Cache de la sesion
# --------------------------------------------------------------------------
# El password de la base se necesita una vez, para abrir la conexion. Cachearlo
# aca evita llamar a DPAPI por cada lectura de configuracion.
_cache = {}


def guardar_en_sesion(clave, valor):
    _cache[clave] = valor


def obtener_de_sesion(clave, por_defecto=None):
    return _cache.get(clave, por_defecto)


def limpiar_sesion():
    _cache.clear()
