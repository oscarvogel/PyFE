"""La pantalla de correo: que guarde lo que dice y que explique los fallos.

Por que esta probada
--------------------
Probar la conexión es lo único que confirma de verdad que el host y el puerto
están bien. Y el error que devuelve smtplib es crudo: "[Errno 11001] getaddrinfo
failed" no le dice nada a quien lo lee, cuando lo que pasó es que el nombre del
servidor está mal. Ese es justamente el caso de Ferozo, que no publica el host
por DNS.
"""
import os
import socket
import sys

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def app():
    from PyQt5.QtWidgets import QApplication
    a = QApplication.instance() or QApplication(sys.argv)
    from libs.tema import aplicar_tema
    aplicar_tema(a)
    return a


# -- Traduccion de los errores -----------------------------------------------

def test_un_host_inexistente_se_explica_en_castellano():
    """El caso mas comun: el nombre esta mal, y smtplib no lo dice."""
    from controladores.ConfiguracionCorreo import _motivo

    error = socket.gaierror(-2, "Name or service not known")
    texto = _motivo(error)
    assert "no existe" in texto
    assert "panel" in texto, "tiene que decir de donde se saca el host"
    assert "gaierror" not in texto.lower().split("(")[0].strip(), \
        "el texto tiene que explicar, no repetir el nombre de la clase"


def test_el_error_de_socket_envuelto_tambien_se_traduce():
    """smtplib envuelve el error: "[Errno 11001] getaddrinfo failed" no dice
    'gaierror' en ninguna parte, asi que hay que mirar el nombre de la clase."""
    from controladores.ConfiguracionCorreo import _motivo

    class SMTPHostLookupError(Exception):
        pass

    texto = _motivo(SMTPHostLookupError("[Errno 11001] getaddrinfo failed"))
    assert "no existe" in texto


def test_un_puerto_cerrado_se_explica():
    from controladores.ConfiguracionCorreo import _motivo

    class ConnectionRefusedError(Exception):
        pass

    texto = _motivo(ConnectionRefusedError("Connection refused"))
    assert "puerto" in texto.lower()


def test_un_error_desconocido_pasa_por_largo():
    """Si no se conoce el motivo, se muestra el texto crudo, no se inventa."""
    from controladores.ConfiguracionCorreo import _motivo

    texto = _motivo(ValueError("algo raro paso"))
    assert "algo raro paso" in texto


# -- La pantalla -------------------------------------------------------------

@pytest.fixture
def controlador(app, monkeypatch):
    monkeypatch.setattr(sys, "argv", [sys.argv[0]])

    guardados = {}

    import modelos.ParametrosSistema as modelo
    monkeypatch.setattr(modelo.ParamSist, "GuardarParametro",
                        staticmethod(lambda nombre, valor: guardados.update(
                            {nombre: valor})))

    import libs.Utiles as utiles
    monkeypatch.setattr(utiles, "_parametro_smtp",
                        lambda nombre, defecto="": defecto or "")

    from controladores.ConfiguracionCorreo import ConfiguracionCorreoController
    c = ConfiguracionCorreoController()
    c._guardados = guardados
    yield c
    c.view.close()


def test_los_campos_arrancan_con_los_valores_por_defecto(controlador):
    """El usuario y el puerto por defecto ya vienen cargados: se ahorra
    escribirlos y se evita el error tipografico."""
    assert controlador.view.txtUsuario.text() == "info@vogelconsultoria.com.ar"
    assert controlador.view.txtPuerto.text() == "465"
    assert controlador.view.txtServidor.text() == "", \
        "el servidor NO se inventa: no es un nombre que exista"


def test_guardar_escribe_los_cuatro_parametros(controlador):
    controlador.guardar({
        "servidor": "smtp.ejemplo.com", "puerto": "587",
        "usuario": "info@vogelconsultoria.com.ar", "clave": "la-clave",
        "destino": "errores@ejemplo.com"})

    guardados = controlador._guardados
    assert guardados["SERVER_SMTP"] == "smtp.ejemplo.com"
    assert guardados["PUERTO_SMTP"] == "587"
    assert guardados["USUARIO_SMTP"] == "info@vogelconsultoria.com.ar"
    assert guardados["CLAVE_SMTP"] == "la-clave"
    assert guardados["DESTINO_ERRORES"] == "errores@ejemplo.com"


def test_sin_servidor_no_intenta_conectar(controlador):
    """Conectar a un host vacio revienta con un error que no dice nada, y esto
    corre cuando alguien esta=configurando, no cuando algo se rompió."""
    from unittest.mock import patch

    with patch("smtplib.SMTP_SSL") as smtp:
        ok = controlador.probar({"servidor": "", "puerto": "465",
                                 "usuario": "u", "clave": "c"},
                                controlador.view.lblEstado)
    assert ok is False
    assert not smtp.called, "no se puede intentar conectar sin servidor"
    assert "panel del hosting" in controlador.view.lblEstado.text()


def test_un_puerto_no_numerico_no_intenta_conectar(controlador):
    from unittest.mock import patch

    with patch("smtplib.SMTP_SSL") as smtp:
        ok = controlador.probar({"servidor": "smtp.ejemplo.com", "puerto": "no",
                                 "usuario": "u", "clave": "c"},
                                controlador.view.lblEstado)
    assert ok is False
    assert not smtp.called
    assert "número" in controlador.view.lblEstado.text()


def test_un_host_inexistente_muestra_la_explicacion(controlador):
    """Este es el caso real: el host no resuelve."""
    import socket
    from unittest.mock import patch

    with patch("smtplib.SMTP_SSL",
               side_effect=socket.gaierror(-2, "Name or service not known")):
        ok = controlador.probar({"servidor": "0110632.ferozo.com",
                                 "puerto": "465", "usuario": "u", "clave": "c"},
                                controlador.view.lblEstado)

    assert ok is False
    texto = controlador.view.lblEstado.text()
    assert "0110632.ferozo.com:465" in texto, "tiene que decir a quien se intentó"
    assert "no existe" in texto
    assert "panel" in texto, "y decir de donde se saca el nombre"


def test_una_conexion_correcta_lo_dice_en_verde(controlador):
    from unittest.mock import MagicMock, patch

    smtp = MagicMock()
    with patch("smtplib.SMTP_SSL", return_value=smtp):
        ok = controlador.probar({"servidor": "smtp.ejemplo.com", "puerto": "465",
                                 "usuario": "info@ejemplo.com", "clave": "c"},
                                controlador.view.lblEstado)

    assert ok is True
    smtp.login.assert_called_once_with("info@ejemplo.com", "c")
    assert "Conexión correcta" in controlador.view.lblEstado.text()


def test_la_contrasena_no_se_muestra_sola(controlador):
    """Oculta por defecto, y hay que pedirla a proposito."""
    from PyQt5.QtWidgets import QLineEdit
    assert controlador.view.txtClave.echoMode() == QLineEdit.Password

    controlador.view.chkVerClave.setChecked(True)
    assert controlador.view.txtClave.echoMode() == QLineEdit.Normal
