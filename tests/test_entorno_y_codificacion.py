"""Dos cosas que costaron horas y no se pueden volver a romper.

1. Un dialogo modal en plataforma offscreen Access Violation. No es un error de
   Python: se lleva el proceso entero y con el todo lo impreso hasta ese
   momento, asi que el script muere en silencio. Por eso hay que preguntar por
   la plataforma, no solo por la QApplication.

2. Los caracteres U+FFFD. Quedan cuando algo se decodifica con la codificacion
   equivocada: el original se pierde y en el lugar queda un signo de
   interrogacion que no es codigo. Aparece en comentarios y en un nombre de
   campo de plantilla, asi que no rompe nada, pero se propaga con cada copia.
"""
import os
import sys

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

CARPETAS_IGNORADAS = {".git", "build", "dist", "__pycache__", "_prueba_exec",
                      "_prueba_facturacion", "_sandbox_prueba", ".venv",
                      "pyafipws", "tests"}
EXTENSIONES = (".py", ".css", ".bat", ".iss", ".txt", ".csv")


# -- 1. Dialogos sin pantalla -------------------------------------------------

@pytest.fixture(scope="module")
def app():
    from PyQt5.QtWidgets import QApplication
    return QApplication.instance() or QApplication(sys.argv)


def test_offscreen_no_cuenta_como_interfaz(app):
    """Con la plataforma offscreen hay QApplication pero NO hay pantalla.

    Abrir un modal ahi es un Access Violation, no una excepcion: el proceso
    muere sin traceback. Por eso hay_interfaz() tiene que mirar la plataforma.
    """
    from libs import Ventanas
    assert app.platformName().lower() in ("offscreen", "minimal", "vnc")
    assert Ventanas.hay_interfaz() is False, \
        "si esto da True, un dialogo va a matar el proceso en los tests y scripts"


def test_en_offscreen_los_dialogos_no_abren_una_ventana(app, capsys):
    """Y por lo tanto no se intenta abrir ninguna."""
    from libs import Ventanas

    Ventanas.showAlert("Aviso", "mensaje de prueba")
    Ventanas.showError("Error", "fallo de prueba",
                       que_hacer="revisar", detalle="detalle tecnico")

    salida = capsys.readouterr().err
    assert "mensaje de prueba" in salida
    assert "fallo de prueba" in salida
    # El proceso sigue vivo: si hubiera reventado, no arrive aca.


def test_la_confirmacion_sin_pantalla_dice_que_no(app):
    """Sin ventana no se puede preguntar, y sin respuesta no se autoriza."""
    from libs import Ventanas
    assert Ventanas.showConfirmation("Emitir", "Emitir la factura?") is False


# -- 2. Caracteres corruptos -------------------------------------------------

def _fuentes_con_fffd():
    encontrados = []
    for carpeta, directorios, archivos in os.walk(RAIZ):
        directorios[:] = [d for d in directorios if d not in CARPETAS_IGNORADAS]
        for nombre in archivos:
            if not nombre.endswith(EXTENSIONES):
                continue
            ruta = os.path.join(carpeta, nombre)
            try:
                with open(ruta, "r", encoding="utf-8") as f:
                    contenido = f.read()
            except (UnicodeDecodeError, IOError):
                continue
            for numero, linea in enumerate(contenido.splitlines(), 1):
                if "\ufffd" in linea:
                    relativo = os.path.relpath(ruta, RAIZ)
                    repeticiones = linea.count("\ufffd")
                    encontrados.append("{}:{} ({} en total)".format(
                        relativo, numero, Replacement))
    return encontrados


def test_no_hay_caracteres_de_reemplazo_en_el_codigo():
    """Un U+FFFD es un caracter perdido: no se puede recuperar, se previene."""
    malos = _fuentes_con_fffd()
    assert not malos, (
        "caracteres U+FFFD (de una codificacion mal leida). Se pierden para "
        "siempre, hay que corregir el original a mano:\n  " + "\n  ".join(malos))


def test_las_plantillas_no_tienen_nombres_de_campo_corruptos():
    """Un campo con el nombre roto no lo encuentra nadie que lo busca."""
    carpeta = os.path.join(RAIZ, "plantillas")
    for nombre in os.listdir(carpeta):
        if not nombre.endswith(".csv"):
            continue
        ruta = os.path.join(carpeta, nombre)
        with open(ruta, "r", encoding="utf-8", errors="replace") as f:
            contenido = f.read()
        assert "\ufffd" not in contenido, "{} tiene un campo roto".format(nombre)
