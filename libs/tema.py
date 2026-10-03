# coding=utf-8
"""Aplicacion del tema de la aplicacion.

Como funciona
-------------
Antes el tema vivia en tres lugares y ninguno funcionaba:

1. `libs/ComboBox.py` tenia un `ComboTema` que ofrecia 7 archivos .css, pero
   ningun codigo leia esa seleccion: era un desplegable que no hacia nada.
2. `controladores/Main.py` llamaba a `EstableceTema()`, que estaba comentado.
3. `libs/Formulario.py` aplicaba un .css POR DIALOGO, leyendo el parametro
   `TEMA` de la base, dentro de un `except: pass`. Eso hace que el estilo se
   pierda en cuanto un dialogo no encuentra el archivo, y que cada ventana
   pueda verse distinta de las demas.

Ahora hay un solo tema (`temas/pyfe.css`) que se aplica una vez a la
QApplication. Todas las ventanas heredan el mismo estilo por definicion, y no
hace falta base de datos ni leer configuracion para que se vea bien.
"""

import os
import re

from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QStyleFactory

# Fuente de la app. Segoe UI esta en todas las instalaciones de Windows desde
# Vista; los nombres siguientes son el fallback para otros sistemas.
FAMILIAS_FUENTE = ["Segoe UI", "Noto Sans", "DejaVu Sans", "Helvetica"]
TAMANIO_BASE = 10

RUTA_TEMA = os.path.join("temas", "pyfe.css")


def _fuente_disponible(familias):
    """Primer nombre de fuente que exista en el sistema, o el primero."""
    from PyQt5.QtGui import QFontDatabase
    disponibles = set(QFontDatabase().families())
    for familia in familias:
        if familia in disponibles:
            return familia
    return familias[0]


def ruta_tema(nombre=RUTA_TEMA):
    """Ruta absoluta del .css del tema, o '' si no se encuentra."""
    try:
        from libs.recursos import ruta_recurso
        return ruta_recurso(nombre)
    except Exception:
        # Si el modulo de recursos no esta disponible (por ejemplo en un
        # arranque muy temprano), se resuelve a mano.
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidato = os.path.join(base, nombre)
        return candidato if os.path.exists(candidato) else ""


def resolver_urls(css):
    """Convierte `url(@algo.png)` del stylesheet en una ruta absoluta.

    Qt resuelve las url() de un stylesheet cargado con setStyleSheet() contra
    el directorio de trabajo, no contra la carpeta del archivo. En el
    ejecutable compilado el cwd es desde donde el usuario hizo doble clic, asi
    que las imagenes del tema no se encontrarian. Se pasan a absolutas antes de
    aplicar, que es lo unico que funciona en los dos casos.

    El prefijo @ es a proposito: marca "esto lo resuelve la app" y evita que
    una url relativa suelta quede passando por alto.
    """
    try:
        from libs.recursos import ruta_recurso
    except Exception:
        return css

    def _reemplazar(m):
        completa = ruta_recurso("temas/" + m.group(1).lstrip("/"))
        return "url({})".format(completa.replace("\\", "/")) if completa else m.group(0)

    return re.sub(r"url\(@([^)]+)\)", _reemplazar, css)


def aplicar_tema(app=None, nombre=RUTA_TEMA):
    """Aplica estilo base, fuente y stylesheet a la aplicacion.

    Devuelve un dict con lo que se pudo aplicar, para poder avisar en el log
    sin romper el arranque.
    """
    app = app or QApplication.instance()
    if app is None:
        raise RuntimeError("aplicar_tema necesita una QApplication")

    resultado = {"estilo": None, "fuente": None, "css": False, "ruta_css": ""}

    # 1) Estilo base Fusion. El de Windows deja los controles con relieve y
    #    degradados que el stylesheet no alcanza a tapar, y deja bordes
    #    distintos segun la version de Windows. Fusion es la base que los
    #    estilos personalizados controlan de verdad.
    for estilo in ("Fusion", "WindowsVista", "Windows"):
        if estilo in QStyleFactory.keys():
            app.setStyle(QStyleFactory.create(estilo))
            resultado["estilo"] = estilo
            break

    # 2) Fuente unica para toda la app. Los widgets que en su constructor
    #    fuerzan su propia QFont pisan esto; esos se corrigieron uno por uno.
    fuente = QFont(_fuente_disponible(FAMILIAS_FUENTE), TAMANIO_BASE)
    fuente.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(fuente)
    resultado["fuente"] = fuente.family()

    # 3) El stylesheet, global.
    ruta = ruta_tema(nombre)
    resultado["ruta_css"] = ruta
    if ruta:
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                app.setStyleSheet(resolver_urls(f.read()))
            resultado["css"] = True
        except (OSError, IOError, UnicodeDecodeError):
            # Sin stylesheet la app sigue funcionando: se ve con el estilo
            # base, que es lo de siempre. No se corta el arranque.
            pass

    return resultado


# Estados que puede tomar un control de entrada.
#   'ok'     -> el dato se valido (por ejemplo, el codigo existe)
#   'error'  -> el dato no sirve
#   'aviso'  -> ni una cosa ni la otra
# El color de cada uno lo decide el tema, no el codigo que llama.
ESTADOS = ("ok", "error", "aviso")


def marcar_estado(widget, estado):
    """Marca un control con un estado visual y refresca el estilo al instante.

    Cambiar una propiedad dinamica en Qt no actualiza el widget por si solo:
    hay que hacer unpolish/polish, o el color nuevo no se ve hasta que la
    ventana se vuelve a mostrar.
    """
    if widget is None:
        return
    if estado not in ESTADOS:
        estado = ""
    widget.setProperty("estado", estado)
    estilo = widget.style()
    if estilo is not None:
        estilo.unpolish(widget)
        estilo.polish(widget)
    widget.update()


def limpiar_estado(widget):
    # El nombre es marcar_estado: con "marca_" esto tiraba NameError en
    # cuanto un control se limpiaba, y eso rompia el "Nuevo" y el "Editar" de
    # los 12 ABM, que son los que la llaman.
    marcar_estado(widget, "")
