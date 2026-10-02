import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_el_dialogo_se_puede_construir(app):
    from vistas.DialogoPassword import DialogoPassword
    d = DialogoPassword()
    assert d.windowTitle() == "Base de datos"
    # el campo tiene que ser de los que tapan lo que se escribe
    assert d.txtPassword.echoMode() == d.txtPassword.Password
    d.close()


def test_el_dialogo_devuelve_el_valor_y_el_recordar(app):
    from vistas.DialogoPassword import DialogoPassword
    d = DialogoPassword()
    d.txtPassword.setText("clave-de-prueba")
    d.chkRecordar.setChecked(True)
    assert d.valores() == ("clave-de-prueba", True)

    d.chkRecordar.setChecked(False)
    assert d.valores() == ("clave-de-prueba", False)
    d.close()


def test_el_dialogo_acepta_el_mensaje_personalizado(app):
    from vistas.DialogoPassword import DialogoPassword
    d = DialogoPassword(titulo="Aviso", mensaje="mensaje propio")
    assert d.windowTitle() == "Aviso"
    d.close()


def test_recordar_esta_marcado_por_defecto(app):
    # por defecto se ofrece recordar, que es lo que pidio el usuario
    from vistas.DialogoPassword import DialogoPassword
    d = DialogoPassword()
    assert d.chkRecordar.isChecked() is True
    d.close()
