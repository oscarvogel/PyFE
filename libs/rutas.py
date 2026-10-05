# coding=utf-8
"""Donde se escribe: la carpeta de instalacion no siempre se puede escribir.

Por que existe esto
-------------------
La app se instala en `C:\\Program Files\\Asiento` (ver `installer/PyFE.iss`).
En Windows, un proceso normal NO puede crear archivos ahi: solo un proceso
elevado puede. Y la app no corre elevada: el acceso directo del instalador la
abre tal cual.

El instalador pide admin (`PrivilegesRequired=admin`) para poder escribir los
archivos, pero eso no dice nada de como corre la app despues. Por eso se podia
instalar bien y despues no poder guardar nada.

A esto se suma un detalle que hace que el fallo sea reciente y no de siempre: la
virtualizacion de archivos de UAC (que redirige en silencio las escrituras a
`%LOCALAPPDATA%\\VirtualStore`) solo existe para procesos de 32 bits. En un
ejecutable de 64 bits esta desactivada, y la escritura falla de verdad, con
`PermissionError`.

El crash que se vio en una instalacion nueva
--------------------------------------------
`main.py` deja el directorio de trabajo apuntando a la carpeta de la app, y
`Utiles.GrabarIni` resuelve `sistema.ini` con `os.getcwd()`. Con la carpeta de
instalacion en solo lectura, el asistente de primer arranque completaba y al
guardar tiraba:

    PermissionError: [Errno 13] Permission denied:
    'C:\\Program Files\\Asiento\\sistema.ini'

ademas de que la base (`sistema.db`), que tambien es relativa al directorio de
trabajo, no se podria crear despues.

La regla
--------
La carpeta de instalacion guarda lo que se puede LEER (el ejecutable,
`imagenes/`, `plantillas/`, `conf/`, `data/`, `temas/`). Lo que se ESCRIBE
(la configuracion, la base, los logs) va a una carpeta del usuario. No es una
decision estetica: con el ejecutable en solo lectura, escribir ahi es
imposible.

Como se decide
--------------
`carpeta_datos()` devuelve, en este orden:

1. `PYFE_CARPETA_DATOS` si esta definida. Los tests y las instalaciones
   portables la usan para fijar la carpeta a mano.
2. El directorio de trabajo actual, **si se puede escribir**. Esto mantiene
   exactamente el comportamiento de siempre en desarrollo, en los tests
   (que corren con `monkeypatch.chdir(tmp_path)`), en las instalaciones
   portables y en las herramientas de `tools/`, que dependian de que el
   `sistema.ini` se leyera del cwd.
3. `%LOCALAPPDATA%\\Asiento`, creada si falta. Es la carpeta de datos del
   usuario: se elige por la misma razon que ya usa `libs/changelog.py` para el
   estado de las novedades.

Que se escriba un archivo de prueba para decidir si una carpeta es escribible
no es paranoia: `os.access(carpeta, os.W_OK)` da `True` para carpetas en las
que despues no se puede crear nada (por ejemplo cuando hay un archivos de
solo lectura, o cuando el permiso viene de una ACL que `os.access` no mira).
"""

import os
import sys
import tempfile

from libs.Constantes import NOMBRE_PRODUCTO

# Variable de entorno para fijar la carpeta a mano (tests, portables, soporte).
ENV_CARPETA_DATOS = "PYFE_CARPETA_DATOS"

NOMBRE_INI = "sistema.ini"

_cache_carpetas = {}
_cache_escribible = {}


def limpiar_cache():
    """Olvida las carpetas ya resueltas y las sondas ya hechas.

    Lo usan los tests. Sin esto, resolver una vez en un `tmp_path` Pinado a un
    test contaminaria al siguiente.
    """
    _cache_carpetas.clear()
    _cache_escribible.clear()


def carpeta_instalacion():
    """La carpeta donde esta el programa. Solo lectura: nunca se escribe aca."""
    if getattr(sys, "frozen", False):
        ejecutable = os.path.dirname(os.path.abspath(sys.executable))
        if ejecutable:
            return ejecutable
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _sonda(carpeta):
    """Intenta crear y borrar un archivo en la carpeta. No deja nada.

    Devuelve True si se pudo. Ojo con el `bool()` de abajo: si esto devolviera
    None, `puede_escribir` contestaria False en todas las carpetas.
    """
    descriptor, temporal = tempfile.mkstemp(prefix=".pyfe-sonda-", dir=carpeta)
    os.close(descriptor)
    try:
        os.unlink(temporal)
    except OSError:
        pass
    return True


def puede_escribir(carpeta, probar=None):
    """True si se puede crear un archivo en `carpeta`.

    Se cachea por carpeta: la sonda crea un archivo, y llamarla en cada lectura
    de configuracion seria crear y borrar archivos todo el tiempo.

    `probar` permite inyectar la sonda en los tests. El default es la sonda
    real, que es la que decide.
    """
    if not carpeta:
        return False
    clave = os.path.normcase(os.path.abspath(carpeta))
    if clave not in _cache_escribible:
        if probar is None:
            probar = _sonda
        try:
            _cache_escribible[clave] = bool(probar(clave))
        except OSError:
            # Sin permiso, la carpeta no existe, o hay algo en el medio.
            _cache_escribible[clave] = False
    return _cache_escribible[clave]


def asegurar_carpeta(carpeta):
    """Crea la carpeta si falta. Devuelve la ruta, o '' si no se pudo."""
    if not carpeta:
        return ""
    try:
        if not os.path.isdir(carpeta):
            os.makedirs(carpeta)
        return carpeta
    except OSError:
        return ""


def _carpeta_del_usuario():
    """La carpeta de datos del usuario, segun el sistema operativo."""
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        # Fuera de Windows no hay LOCALAPPDATA. Mismo criterio que
        # libs/changelog.py: la carpeta de datos del usuario.
        base = os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(base, NOMBRE_PRODUCTO)


def _cwd():
    try:
        return os.getcwd()
    except OSError:
        # Carpeta de trabajo borrada: no hay donde trabajar.
        return ""


def _resolver_carpeta_datos():
    forzado = os.environ.get(ENV_CARPETA_DATOS)
    if forzado:
        return asegurar_carpeta(os.path.abspath(forzado)) or os.path.abspath(forzado)

    # El directorio de trabajo manda mientras se pueda escribir: es lo que
    # hacen la desarrollo, los tests, las portables y tools/.
    actual = _cwd()
    if actual and puede_escribir(actual):
        return actual

    destino = asegurar_carpeta(_carpeta_del_usuario())
    if not destino:
        # Ultimo recurso. Si tampoco esta se puede crear, se sigue con el cwd
        # y el error va a aparecer en la escritura, que es donde se puede
        # explicar en castellano.
        return actual
    return destino


def carpeta_datos():
    """La carpeta escribible: configuracion, base y logs van aca.

    El resultado se cachea POR DIRECTORIO DE TRABAJO, no en un unico lugar.
    Razon: los tests cambian de carpeta con `monkeypatch.chdir(tmp_path)` y
    esperan que la configuracion se lea de ahi. Con una sola entrada en la
    cache, el primer test que resuelve la deja fijada para todos los que
    siguen, y los demas leen (o escriben) la configuracion de otro directorio
    sin enterarse.
    """
    clave = (os.environ.get(ENV_CARPETA_DATOS) or "", _cwd())
    if clave not in _cache_carpetas:
        _cache_carpetas[clave] = _resolver_carpeta_datos()
    return _cache_carpetas[clave]


def ruta_ini():
    """Ruta completa del `sistema.ini`."""
    return os.path.join(carpeta_datos(), NOMBRE_INI)


def ruta_base(nombre):
    """Ruta de un archivo de datos (la base) dentro de la carpeta de datos."""
    asegurar_carpeta(carpeta_datos())
    return os.path.join(carpeta_datos(), nombre)


# -- Datos que ya estaban en la carpeta de instalacion ----------------------
#
# Cuando la carpeta de la app no se puede escribir, la carpeta de datos arranca
# vacia. Si no se trae para alla lo que ya estaba, el cliente ve una app como
# recien instalada: le aparece el asistente y la base le aparece VACIA, cuando
# en realidad tiene todo. Eso es peor que el PermissionError original.
#
# Se copia una vez, el archivo original queda donde estaba (no se borra nada:
# el desinstalador ya se encarga de la carpeta de la app), y la copia es la que
# pasa a mandar.


ARCHIVOS_A_MIGRAR = (NOMBRE_INI,)


def _archivos_a_migrar(instalacion):
    """El sistema.ini y cualquier base SQLite que haya en la instalacion.

    La base no siempre se llama `sistema.db`: con `usa_nombre_db = S` se llama
    como el `basedatos` de la configuracion. Si la migracion solo mirara
    `sistema.db`, ese cliente se encontraria con la base vacia, que es
    justamente lo que esta migracion existe para evitar.
    """
    nombres = list(ARCHIVOS_A_MIGRAR)
    try:
        for nombre in sorted(os.listdir(instalacion)):
            if nombre.lower().endswith(".db") and nombre not in nombres:
                nombres.append(nombre)
    except OSError:
        pass
    return nombres


def migrar_desde_instalacion(instalacion=None, destino=None, registrar=None):
    """Trae a la carpeta de datos lo que ya estaba en la de instalacion.

    Solo si el archivo no esta en el destino: una migracion nunca pisa lo que
    el usuario ya configuro en la carpeta nueva.

    Devuelve un dict con lo que se copio, para poder avisar por pantalla y
    dejar registro de que paso.
    """
    if instalacion is None:
        instalacion = carpeta_instalacion()
    if destino is None:
        destino = carpeta_datos()

    if os.path.normcase(os.path.abspath(instalacion)) == \
            os.path.normcase(os.path.abspath(destino)):
        return {}

    copiados = {}
    for nombre in _archivos_a_migrar(instalacion):
        origen = os.path.join(instalacion, nombre)
        destino_final = os.path.join(destino, nombre)
        if not os.path.isfile(origen) or os.path.exists(destino_final):
            continue
        try:
            asegurar_carpeta(destino)
            with open(origen, "rb") as f:
                contenido = f.read()
            with open(destino_final, "wb") as f:
                f.write(contenido)
        except OSError as error:
            if registrar:
                registrar("No se pudo copiar {} desde la carpeta del programa: {}"
                          .format(nombre, error.strerror or type(error).__name__))
            continue
        copiados[nombre] = destino_final
        if registrar:
            registrar("Se copio {} de la carpeta del programa a {}".format(
                nombre, destino))
    return copiados
