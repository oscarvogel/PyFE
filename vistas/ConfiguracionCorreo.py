# coding=utf-8
"""Pantalla de configuracion del correo saliente.

Por que existe
--------------
La app manda un reporte automatico de errores por correo, y sus datos viven en
Parametros del sistema. Pero "Parametros del sistema" es un ABM generico: una
grilla con las columnas id / parametro / valor. Para configurar el correo
habia que agregar cuatro filas a mano, escribiendo de memoria los nombres
exactos de los parametros (SERVER_SMTP, USUARIO_SMTP, CLAVE_SMTP, PUERTO_SMTP)
en una pantalla que no dice para que son.

Eso no es configuracion: es un examen. Y el que la tiene que hacer es el
administrador del sistema, en la maquina de un cliente.

Ademas hay un boton para probar la conexion, que es la unica forma de
confirmar de verdad que el host y el puerto estan bien antes de esperar a que
falle un reporte.
"""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox,
                             QFormLayout, QGroupBox, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QVBoxLayout)

from libs.Formulario import Formulario


class ConfiguracionCorreoView(Formulario):
    """Datos del servidor de correo saliente, con botón de prueba.

    Hereda de `Formulario` y no de `QDialog` a proposito: es la unica pantalla
    que se saltaba la base comun, y por eso no TOMABA el piso de tamano que
    pone `Formulario.showEvent`. Quedaba en 460 px de ancho, con los campos
    de SMTP apretados de a tres por fila.
    """

    def __init__(self, parent=None, controlador=None):
        Formulario.__init__(self, parent=None)
        self.controlador = controlador
        self.setWindowTitle("Correo de reportes de errores")
        self.setObjectName("dialogoCorreo")

        vertical = QVBoxLayout(self)
        vertical.setSpacing(10)

        intro = QLabel(
            "Asiento avisa por correo cuando un cliente tiene un error que no "
            "puede seguir. Esta configuración es de la instalación, no del "
            "cliente: se completa una vez, en la máquina donde corre el "
            "programa.")
        intro.setObjectName("labelSubtitulo")
        intro.setWordWrap(True)
        vertical.addWidget(intro)

        # -- Servidor -------------------------------------------------------
        grupo = QGroupBox("Servidor de salida")
        formulario = QFormLayout(grupo)
        formulario.setLabelAlignment(Qt.AlignRight)

        self.txtServidor = QLineEdit()
        self.txtServidor.setPlaceholderText(
            "el que muestra el panel del hosting, por ejemplo smtp.mihost.com")
        formulario.addRow("Servidor SMTP", self.txtServidor)

        self.txtPuerto = QLineEdit()
        self.txtPuerto.setPlaceholderText("465 con SSL, 587 con STARTTLS, 25 sin cifrar")
        formulario.addRow("Puerto", self.txtPuerto)

        self.txtUsuario = QLineEdit()
        formulario.addRow("Usuario", self.txtUsuario)

        self.txtClave = QLineEdit()
        self.txtClave.setEchoMode(QLineEdit.Password)
        self.txtClave.setPlaceholderText("la de la casilla de correo")
        formulario.addRow("Contraseña", self.txtClave)

        self.chkVerClave = QCheckBox("Mostrar la contraseña")
        self.chkVerClave.toggled.connect(self._al_mirar_clave)
        formulario.addRow("", self.chkVerClave)

        self.txtDestino = QLineEdit()
        self.txtDestino.setPlaceholderText(
            "si se deja vacío, los reportes van a la casilla de arriba")
        formulario.addRow("Destino de los reportes", self.txtDestino)
        vertical.addWidget(grupo)

        # -- Estado ---------------------------------------------------------
        self.lblEstado = QLabel("")
        self.lblEstado.setObjectName("labelSubtitulo")
        self.lblEstado.setWordWrap(True)
        vertical.addWidget(self.lblEstado)

        # -- Botones --------------------------------------------------------
        horizontal = QHBoxLayout()
        self.btnProbar = QPushButton("Probar conexión")
        self.btnProbar.setObjectName("botonSecundario")
        self.btnProbar.clicked.connect(self._probar)
        horizontal.addWidget(self.btnProbar)
        horizontal.addStretch(1)

        self.botones = QDialogButtonBox(QDialogButtonBox.Save |
                                        QDialogButtonBox.Cancel)
        self.botones.button(QDialogButtonBox.Save).setText("Guardar")
        self.botones.button(QDialogButtonBox.Cancel).setText("Cancelar")
        self.botones.accepted.connect(self._guardar)
        self.botones.rejected.connect(self.reject)
        horizontal.addWidget(self.botones)
        vertical.addLayout(horizontal)

    # -- Cargar y guardar ---------------------------------------------------

    def cargar(self, valores):
        self.txtServidor.setText(valores.get("servidor", ""))
        self.txtPuerto.setText(str(valores.get("puerto", "") or ""))
        self.txtUsuario.setText(valores.get("usuario", ""))
        self.txtClave.setText(valores.get("clave", ""))
        self.txtDestino.setText(valores.get("destino", ""))

    def valores(self):
        return {
            "servidor": self.txtServidor.text().strip(),
            "puerto": self.txtPuerto.text().strip(),
            "usuario": self.txtUsuario.text().strip(),
            "clave": self.txtClave.text(),
            "destino": self.txtDestino.text().strip(),
        }

    # -- Acciones -----------------------------------------------------------

    def _al_mirar_clave(self, marcado):
        modo = QLineEdit.Normal if marcado else QLineEdit.Password
        self.txtClave.setEchoMode(modo)

    def _guardar(self):
        if self.controlador is not None:
            self.controlador.guardar(self.valores())
        self.accept()

    def _probar(self):
        if self.controlador is not None:
            self.controlador.probar(self.valores(), self.lblEstado)
        else:
            self.lblEstado.setText("No hay controlador conectado.")
