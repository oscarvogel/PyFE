# coding=utf-8
"""Controlador de la configuracion del correo de reportes."""
import smtplib

from libs import Constantes
from libs.Utiles import _parametro_smtp, inicializar_y_capturar_excepciones
from modelos.ParametrosSistema import ParamSist
from vistas.ConfiguracionCorreo import ConfiguracionCorreoView


# Los nombres que la app ya lee. Se usan tal cual, porque cualquier otro nombre
# no lo lee nadie y el reporte nunca sale.
PARAMETROS = {
    "servidor": "SERVER_SMTP",
    "usuario": "USUARIO_SMTP",
    "clave": "CLAVE_SMTP",
    "puerto": "PUERTO_SMTP",
    "destino": "DESTINO_ERRORES",
}


class ConfiguracionCorreoController(object):
    """Guarda los datos del correo y prueba si el servidor responde."""

    def __init__(self, parent=None):
        self.view = ConfiguracionCorreoView(parent, self)
        self.cargar()

    def cargar(self):
        """Muestra lo que hay configurado, o los valores por defecto."""
        self.view.cargar({
            "servidor": _parametro_smtp("SERVER_SMTP", Constantes.SERVER_SMTP),
            "puerto": _parametro_smtp("PUERTO_SMTP",
                                      Constantes.PUERTO_SMTP) or "",
            "usuario": _parametro_smtp("USUARIO_SMTP", Constantes.USUARIO_SMTP),
            "clave": _parametro_smtp("CLAVE_SMTP", Constantes.CLAVE_SMTP),
            "destino": _parametro_smtp("DESTINO_ERRORES", ""),
        })

    @inicializar_y_capturar_excepciones
    def guardar(self, valores):
        for clave, nombre in PARAMETROS.items():
            ParamSist.GuardarParametro(nombre, valores.get(clave, ""))
        return True

    @inicializar_y_capturar_excepciones
    def probar(self, valores, etiqueta):
        """Conecta al servidor y dice que pasó, sin mandar ningun correo.

        Conectar y autenticar es la mitad de la prueba: si eso anda, el
        problema no es de configuracion local, y avisarlo ahorra volver a
        pensar el tema.
        """
        servidor = (valores.get("servidor") or "").strip()
        usuario = (valores.get("usuario") or "").strip()
        clave = valores.get("clave") or ""
        puerto = (valores.get("puerto") or "").strip() or 465

        if not servidor:
            etiqueta.setText("Falta el servidor SMTP. Se lo tiene del panel "
                             "del hosting, en la sección de correo.")
            etiqueta.setStyleSheet("color: #C62F35;")
            return False

        try:
            puerto = int(puerto)
        except ValueError:
            etiqueta.setText("El puerto tiene que ser un número (465, 587 o 25).")
            etiqueta.setStyleSheet("color: #C62F35;")
            return False

        try:
            if puerto == 465:
                smtp = smtplib.SMTP_SSL(servidor, puerto, timeout=20)
            else:
                smtp = smtplib.SMTP(servidor, puerto, timeout=20)
                if puerto == 587:
                    smtp.starttls()
        except Exception as exc:
            etiqueta.setText(
                "No se pudo conectar con {}:{}.\n\n{}".format(
                    servidor, puerto, _motivo(exc)))
            etiqueta.setStyleSheet("color: #C62F35;")
            return False

        try:
            if usuario and clave:
                smtp.login(usuario, clave)
        except Exception as exc:
            etiqueta.setText(
                "Se conectó, pero no aceptó el usuario o la contraseña.\n\n{}"
                .format(_motivo(exc)))
            etiqueta.setStyleSheet("color: #C62F35;")
            return False
        finally:
            try:
                smtp.quit()
            except Exception:
                pass

        etiqueta.setText(
            "Conexión correcta con {}:{} y el servidor aceptó las "
            "credenciales.".format(servidor, puerto))
        etiqueta.setStyleSheet("color: #1B7A3D;")
        return True

    def exec_(self):
        self.view.show()
        return self.view.exec_()


def _motivo(exc):
    """El motivo de una excepcion de red, en palabras."""
    texto = str(exc).strip() or exc.__class__.__name__
    conocida = {
        "gaierror": "El nombre del servidor no existe. Reviselo: algunos "
                    "proveedores de correo no publican el host por DNS y lo "
                    "dan unicamente en el panel.",
        "timed out": "No respondió a tiempo. Puede ser un firewall o que el "
                     "puerto este bloqueado en esta red.",
        "connection refused": "El puerto está cerrado en ese servidor.",
        "authentication": "El servidor rechazó el usuario o la contraseña.",
    }
    for marca, explicacion in conocida.items():
        if marca in texto.lower():
            return "{} ({})".format(explicacion, texto)
    return texto
