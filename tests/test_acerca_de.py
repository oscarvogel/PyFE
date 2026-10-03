"""La version que se muestra y el dialogo de Acerca de.

Por que estan probados
----------------------
La version se muestra en dos lugares (la barra de estado y Acerca de) y salia
vacia en los dos. No habia ningun error: `_version` buscaba una clave
`versionName` en version.txt que el archivo no tenia, devolvia "" y la pantalla
seguia andando. Estos tests lo cortan.

El dominio tambien importa: es el unico lugar de la app donde el usuario tiene
una forma de ubicar a quien lo desarrollo sin abrir la factura.
"""
import os
import sys

import pytest
from PyQt5.QtWidgets import QApplication

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def app():
    aplicacion = QApplication.instance() or QApplication(sys.argv)
    from libs.tema import aplicar_tema
    aplicar_tema(aplicacion)
    return aplicacion


# -- La version --------------------------------------------------------------

def test_el_version_txt_se_puede_parsear():
    """PyInstaller lee version.txt con eval().

    Agregarle una linea suelta (tipo "versionName=0.8.10") rompe la compilacion
    entera con "Failed to deserialize VSVersionInfo", y el error aparece en el
    .spec, lejos del archivo que lo provoco. Este test corta eso antes.
    """
    from PyInstaller.utils.win32.versioninfo import load_version_info_from_text_file

    ruta = os.path.join(RAIZ, "version.txt")
    assert os.path.isfile(ruta)
    # Si PyInstaller no esta instalado, el chequeo se hace con eval, que es lo
    # mismo que hace el.
    try:
        load_version_info_from_text_file(ruta)
    except ImportError:
        with open(ruta, "r", encoding="utf-8") as f:
            eval(f.read())


def test_el_version_txt_no_tiene_la_marca_vieja():
    """La Etapa 1 renombro el producto; el archivo de version quedo atras."""
    ruta = os.path.join(RAIZ, "version.txt")
    with open(ruta, "r", encoding="utf-8") as f:
        contenido = f.read()
    assert "Servin" not in contenido, "quedo el nombre del desarrollador anterior"
    assert "Asiento" in contenido


def test_la_app_consigue_leer_la_version(app):
    from vistas.Main import MainView

    version = MainView._version()
    assert version, "la version se devuelve vacia"
    assert version.startswith("v")
    assert any(c.isdigit() for c in version)


def test_la_version_cae_a_filevers_si_no_hay_productversion(tmp_path, monkeypatch):
    """Si alguien regenera version.txt con la herramienta de Microsoft, la
    version tiene que seguir saliendo en vez de desaparecer en silencio."""
    import libs.recursos as recursos
    from vistas.Main import MainView

    generado = tmp_path / "version.txt"
    generado.write_text(
        "VSVersionInfo(\n"
        "  ffi=FixedFileInfo(\n"
        "    filevers=(2, 4, 6, 0),\n"
        "  ),\n"
        ")\n", encoding="utf-8")
    monkeypatch.setattr(recursos, "rutas_base", lambda: [str(tmp_path)])

    assert MainView._version() == "v2.4.6"


# -- Acerca de ---------------------------------------------------------------

@pytest.fixture
def ventana_principal(app):
    """La pantalla principal.

    MainView arma su UI en initUi(), no en __init__: sin llamarla la vista
    existe pero esta vacia, y el test pasaria probando un widget que no esta.
    """
    from vistas.Main import MainView

    ventana = MainView()
    ventana.initUi()
    yield ventana
    ventana.close()


def test_el_acerca_de_muestra_el_dominio(ventana_principal):
    """El dominio es el unico contacto visible dentro de la app."""
    from PyQt5.QtWidgets import QLabel

    from libs.Constantes import SITIO_EMPRESA

    dlg = ventana_principal.construir_acerca_de()
    textos = " ".join(lbl.text() for lbl in dlg.findChildren(QLabel))
    assert SITIO_EMPRESA in textos
    assert "WhatsApp" in textos
    dlg.close()


def test_el_boton_del_acerca_de_esta_en_castellano(ventana_principal):
    """Con QDialogButtonBox el texto salia en el idioma del sistema: 'Close'."""
    from PyQt5.QtWidgets import QPushButton

    dlg = ventana_principal.construir_acerca_de()
    textos = [b.text() for b in dlg.findChildren(QPushButton)]
    assert "Cerrar" in textos, "no hay boton Cerrar, hay: {}".format(textos)
    assert "Close" not in textos
    dlg.close()


def test_el_pie_de_la_barra_lateral_tiene_el_boton(ventana_principal):
    from PyQt5.QtWidgets import QPushButton

    botones = [b for b in ventana_principal.findChildren(QPushButton)
               if b.objectName() == "botonAcercaDe"]
    assert len(botones) == 1, "el boton de Acerca de no esta en la pantalla"
    assert "Acerca" in botones[0].text()
