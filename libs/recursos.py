# coding=utf-8
"""Resolucion de recursos (imagenes, plantillas, conf) de la aplicacion.

Por que existe esto
-------------------
Los recursos NO van empaquetados adentro del .exe: `compila.bat` copia
`imagenes/` y `conf/` sueltos al lado del ejecutable, porque el sistema.ini los
referencia con rutas relativas.

Antes, el unico modo de encontrar un icono era `imagen()`, que hacia:

    ubicacion_sistema() + join("imagenes", archivo)

y `ubicacion_sistema()` lee `iniciosistema` del sistema.ini. Eso se rompe de
dos maneras:

1. Si la instalacion se copia a otra carpeta (o a otra maquina), el
   `iniciosistema` guardado apunta a la ruta de la maquina original. En las
   instalaciones reales se ven valores tipo `C:\\Programacion\\PyFE/`, que es
   la maquina donde se desarrollo el sistema.
2. Con un ejecutable de una sola pieza, el cwd es desde donde el usuario hizo
   doble clic, no la carpeta de la app.

Ademas habia 22 llamadas que NO usaban el helper y ponian la ruta a mano
(`imagen='imagenes/save.png'`), que es justamente el caso que se rompe al
empaquetar.

Como funciona ahora
-------------------
Se arma una lista de carpetas base candidatas y se devuelve la PRIMERA donde
exista el archivo pedido. Es autocurativo: si el ini queda viejo, se ignora y
se usa la carpeta real del ejecutable. Como el resultado depende del archivo
concreto, se puede probar con un test sin levantar la app.
"""

from __future__ import print_function

import os
import sys

# Carpeta del repo: .../libs/ -> .../
_RAIZ_FUENTE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_cache_rutas = None


def _inicio_sistema():
    """El `iniciosistema` del ini, o cadena vacia si no se puede leer.

    Va ultimo en la lista de candidatas a proposito: es el unico que puede
    quedar desactualizado, asi que se consulta solo cuando nada mas sirvio.
    """
    try:
        from libs.Utiles import LeerIni
        return LeerIni("iniciosistema") or ""
    except Exception:
        # Circular a proposito: Utiles importa a recursos. Y si todavia no
        # hay sistema.ini, no hay inicio que leer.
        return ""


def rutas_base():
    """Carpetas donde puede estar un recurso, en orden de prioridad."""
    global _cache_rutas
    if _cache_rutas is not None:
        return _cache_rutas

    candidatas = []

    # 1) Congelado: la carpeta del .exe. Es donde compila.bat deja imagenes/
    #    y conf/ sueltos.
    if getattr(sys, "frozen", False):
        ejecutable = os.path.dirname(os.path.abspath(sys.executable))
        if ejecutable:
            candidatas.append(ejecutable)
        # PyInstaller one-file extrae los datos a _MEIPASS. No se usa para
        # imagenes/ (que van sueltos) pero sirve si alguien decide empaquetar.
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidatas.append(meipass)

    # 2) Desarrollo: la raiz del repo.
    candidatas.append(_RAIZ_FUENTE)

    # 3) El cwd, por si se corre desde otro lado.
    try:
        cwd = os.path.abspath(os.getcwd())
        if cwd:
            candidatas.append(cwd)
    except OSError:
        pass

    # 4) El ini, de ultimo.
    inicio = _inicio_sistema()
    if inicio:
        candidatas.append(os.path.abspath(inicio.rstrip("/\\")))

    # Sin repetidos, conservando el orden.
    vistas, _cache_rutas = set(), []
    for c in candidatas:
        norm = os.path.normcase(os.path.normpath(c))
        if norm not in vistas:
            vistas.add(norm)
            _cache_rutas.append(c)
    return _cache_rutas


def limpiar_cache():
    """Olvida las rutas cacheadas. Lo usan los tests."""
    global _cache_rutas
    _cache_rutas = None


def ruta_recurso(relativo, debe_existir=True):
    """Devuelve la ruta absoluta de un recurso, o '' si no se encuentra.

    Acepta 'new.png', 'imagenes/new.png' o 'conf/x.crt': si ya trae carpeta,
    no se le antepone 'imagenes'.
    """
    if not relativo:
        return ""

    relativo = str(relativo).replace("\\", "/").lstrip("/")

    # Si el llamador ya paso la carpeta, se respeta tal cual.
    prefijos = [""] if "/" in relativo else ["", "imagenes/"]

    for base in rutas_base():
        for prefijo in prefijos:
            candidato = os.path.join(base, prefijo + relativo)
            if os.path.exists(candidato):
                return os.path.abspath(candidato)
            # SomeQT con QFileDialog y barra de estado usan separador /.
            alternativo = os.path.join(base, prefijo + relativo).replace("\\", "/")
            if os.path.exists(alternativo):
                return alternativo

    if debe_existir:
        return ""
    return os.path.join(rutas_base()[0], relativo)


def imagen(archivo):
    """Ruta de un icono de imagenes/. Vacio si no existe.

    Reemplaza al uso directo de rutas relativas, que es lo que se rompia en el
    ejecutable compilado.

    Para los iconos de la interfaz conviene usar icono('nombre'), que busca en
    el set nuevo (imagenes/iconos/). Este meteda queda para los recursos que no
    son iconos de la interfaz: el logo de la app, los logos de PDF, etc.
    """
    if not archivo:
        return ""
    nombre = str(archivo).replace("\\", "/")
    limpio = nombre[len("imagenes/"):] if nombre.startswith("imagenes/") else nombre
    return ruta_recurso("imagenes/" + limpio)


def icono(nombre, alterno=None, claro=False, peligro=False):
    """Icono del set nuevo, con caida al icono viejo si todavia no se migro.

    El set nuevo vive en imagenes/iconos/ (SVG monoline, ver
    tools/generar_iconos.py). Los PNG viejos siguen en imagenes/ porque
    conviven los dos durante la migracion pantalla por pantalla.

        icono('nueva-venta')                          -> solo el nuevo
        icono('nueva-venta', 'if_bill_416404.png')    -> nuevo, y si falta el viejo
        icono('nuevo', claro=True)                    -> la variante en blanco
        icono('borrar', peligro=True)                 -> la variante en rojo

    `claro=True` busca en imagenes/iconos/blanco/ y `peligro=True` en
    imagenes/iconos/peligro/. Son para los botones con fondo de color: con el
    icono azul sobre fondo azul el dibujo desaparece, y en uno de borrar con el
    texto en rojo y el icono en azul el dibujo dice otra cosa. Qt no sabe
    recolorear un QIcon desde el stylesheet, asi que las variantes tienen que
    existir como archivo.

    Devuelve '' si no encuentra ninguno, que es lo que hace que un boton salga
    sin icono en vez de romper.
    """
    if not nombre:
        return alterno and imagen(alterno) or ""

    relativo = str(nombre).replace("\\", "/")
    if relativo.startswith("imagenes/"):
        relativo = relativo[len("imagenes/"):]

    # Si el llamador ya pasa una extension, se respeta el archivo tal cual.
    if os.path.splitext(relativo)[1]:
        return ruta_recurso("imagenes/" + relativo) or (imagen(alterno) if alterno else "")

    if claro:
        encontrado = ruta_recurso("imagenes/iconos/blanco/{}.svg".format(relativo))
        if encontrado:
            return encontrado
    if peligro:
        encontrado = ruta_recurso("imagenes/iconos/peligro/{}.svg".format(relativo))
        if encontrado:
            return encontrado

    encontrado = ruta_recurso("imagenes/iconos/{}.svg".format(relativo))
    if encontrado:
        return encontrado
    if alterno:
        return imagen(alterno)
    return ""


def iconos_faltantes(referencias):
    """De una lista de nombres de icono, devuelve los que no se encuentran.

    Lo usa el test de recursos para reportar en una sola vez todo lo que esta
    roto, en vez de fallar por el primero.
    """
    faltan = []
    for nombre in referencias:
        if not imagen(nombre):
            faltan.append(nombre)
    return faltan
