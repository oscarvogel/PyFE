# coding=utf-8
"""Identidad del build, para el actualizador automatico de vogel-releases.

Por que este archivo existe
---------------------------
La app instalada necesita saber dos cosas para ofrecer actualizaciones: que
producto es y que version tiene. Eso no se puede leer del nombre del
ejecutable ni de `version.txt`:

- `version.txt` lo lee PyInstaller con `eval()` y solo existe en el build de
  produccion (ver vistas/Main.py::_version). En desarrollo no esta.
- El nombre del .exe es siempre `main.exe`.

Asi que la version viaja en el propio codigo. Aca el archivo versionado tiene
valores INERTES a proposito: si un build de desarrollo los usara, la app
intentaria actualizar contra el manifiesto publico creyendo que es una
instalacion vieja de produccion.

Que lo cambia
-------------
`release.ps1` llama a `tools/generar_build_info.py` antes de compilar, y ese
script SOLO reemplaza las dos lineas de abajo (nunca reescribe el archivo
entero: este modulo tiene funciones que si desaparecieran dejarian la app
sin poder actualizar). Despues del build los devuelve a los valores de
desarrollo.

El resto del archivo se edita a mano, como cualquier otro.
"""

# Valores de desarrollo. Un build de produccion los pisa; ver arriba.
APP_ID = "development"
BUILD_VERSION = "0.0.0.0.0.0"

# Un solo canal: `latest`. Los canales `candidate` (pilotos) son de fgpy y
# femag, que tienen un proceso de promocion con aprobacion. Asiento no lo
# necesita y agregarlo seria un canal mas que alguien tiene que mantener.
_MANIFESTOS = {
    "asiento": (
        "https://raw.githubusercontent.com/oscarvogel/vogel-releases/"
        "main/apps/asiento/latest.json"
    ),
}

_APP_IDS_PRODUCTIVOS = frozenset(_MANIFESTOS)


def manifest_url_for(app_id):
    """Devuelve el manifiesto registrado para ``app_id``.

    Se resuelve por tabla y no por formato de URL a proposito: si alguien
    agrega una app al lado sin registrarla aca, falla al arrancar el
    updater en vez de ir a buscar un manifiesto que no existe.
    """
    try:
        return _MANIFESTOS[app_id]
    except KeyError as exc:
        raise ValueError(
            "app_id de actualizacion desconocido: {!r}".format(app_id)) from exc


def es_build_productivo():
    """True solo en builds con app_id publicado.

    Es la guarda que evita todo el updater en desarrollo: sin ella, correr
    la app desde el repo avisaria de actualizaciones de la version de
    produccion y abriria el instalador de sobre una base de pruebas.
    """
    return APP_ID in _APP_IDS_PRODUCTIVOS


def changelog_url_for(app_id):
    """Historial de novedades del producto."""
    if app_id not in _MANIFESTOS:
        raise ValueError("app_id de changelog desconocido: {!r}".format(app_id))
    return (
        "https://raw.githubusercontent.com/oscarvogel/vogel-releases/"
        "main/apps/{}/changelog.json".format(app_id)
    )
