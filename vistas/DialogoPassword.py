# coding=utf-8
"""Dialogo para pedir el password de la base cuando no se puede leer del
sistema.ini.

Se usa solo en el arranque, y solo para instalaciones MySQL. En sqlite el
password no se usa para conectar, asi que nunca aparece.

El checkbox de 'recordar' es la decision: si esta marcado, el secreto se
guarda con DPAPI (atado al usuario de Windows) y no hay que volver a
tipoarlo. Si no, queda solo en memoria y se vuelve a pedir en el proximo
arranque.

No extiende Formulario a proposito: Formulario importa los modelos, que
tocan la base de datos, y este dialogo tiene que existir ANTES de que se
arme la conexion.
"""

from PyQt5.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QGridLayout,
                             QLabel, QLineEdit, QVBoxLayout)


class DialogoPassword(QDialog):
    """Pide el password de la base y devuelve (texto, recordar)."""

    def __init__(self, parent=None, titulo="Base de datos", mensaje=None):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.setModal(True)

        self.valor = ""
        self.recordar = False

        self.lblTitulo = QLabel(titulo)
        font = self.lblTitulo.font()
        font.setBold(True)
        font.setPointSize(font.pointSize() + 2)
        self.lblTitulo.setFont(font)

        self.lblMensaje = QLabel(
            mensaje or "Ingrese el password de la base de datos.")
        self.lblMensaje.setWordWrap(True)

        self.txtPassword = QLineEdit()
        self.txtPassword.setEchoMode(QLineEdit.Password)
        self.txtPassword.setPlaceholderText("password")

        self.chkRecordar = QCheckBox("Recordar en esta computadora")
        self.chkRecordar.setChecked(True)
        self.chkRecordar.setToolTip(
            "Se guarda protegido por Windows, asociado a este usuario de Windows.\n"
            "Si lo deseleccion, se le va a pedir en cada arranque.")

        self.botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.botones.button(QDialogButtonBox.Ok).setText("Aceptar")
        self.botones.button(QDialogButtonBox.Cancel).setText("Cancelar")
        self.botones.accepted.connect(self.accept)
        self.botones.rejected.connect(self.reject)

        grilla = QGridLayout()
        grilla.addWidget(self.txtPassword, 0, 0)
        grilla.addWidget(self.chkRecordar, 1, 0)

        vertical = QVBoxLayout()
        vertical.addWidget(self.lblTitulo)
        vertical.addWidget(self.lblMensaje)
        vertical.addLayout(grilla)
        vertical.addWidget(self.botones)
        self.setLayout(vertical)

        self.txtPassword.setFocus()

    def valores(self):
        return self.txtPassword.text(), self.chkRecordar.isChecked()
