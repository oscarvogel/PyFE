# coding=utf-8
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QPushButton

from libs.Utiles import LeerIni, openFileNameDialog, GuardarArchivo


class Boton(QPushButton):

    def __init__(self, *args, **kwargs):
        QPushButton.__init__(self, *args)

        texto = ''
        if 'texto' in kwargs:
            texto = kwargs['texto']

        self.setText(texto)

        if 'imagen' in kwargs:
            icono = QIcon(kwargs['imagen'])
            self.setIcon(icono)

            if 'tamanio' in kwargs:
                if kwargs['tamanio'] and isinstance(kwargs['tamanio'],QSize):
                    self.setIconSize(kwargs['tamanio'])
            else:
                self.setIconSize(QSize(32,32))

        if 'tooltip' in kwargs:
            self.setToolTip(kwargs['tooltip'])

        if 'autodefault' in kwargs:
            self.setAutoDefault(kwargs['autodefault'])
        else:
            self.setAutoDefault(True)
        self.setDefault(False)

        if 'enabled' in kwargs:
            self.setEnabled(kwargs['enabled'])

class BotonMain(Boton):

    def __init__(self, *args, **kwargs):
        Boton.__init__(self, *args, **kwargs)
        self.setMinimumHeight(100)
        self.setIconSize(QSize(48,48))

class BotonAceptar(Boton):

    def __init__(self, *args, **kwargs):
        kwargs['texto'] = kwargs['textoBoton'] if 'textoBoton' in kwargs else '&Aceptar'
        kwargs['imagen'] = LeerIni("iniciosistema") + 'imagenes/aceptar.bmp'
        kwargs['tamanio'] = QSize(32,32)
        Boton.__init__(self, *args, **kwargs)

class BotonCerrarFormulario(Boton):

    def __init__(self, *args, **kwargs):
        kwargs['texto'] = kwargs['textoBoton'] if 'textoBoton' in kwargs else '&Cerrar'
        kwargs['imagen'] = LeerIni("iniciosistema") + 'imagenes/close.png'
        kwargs['tamanio'] = QSize(32,32)
        Boton.__init__(self, *args, **kwargs)
        self.setDefault(False)

class BotonArchivo(Boton):

    widgetArchivo = None
    files = None
    guardar = False
    directorio = ""
    nombre_archivo = ""

    def __init__(self, *args, **kwargs):
        kwargs['texto'] = kwargs['textoBoton'] if 'textoBoton' in kwargs else '...'
        if 'archivos' in kwargs:
            self.files = kwargs['archivos']

        super().__init__(*args, **kwargs)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if not self.guardar:
                self.archivo = openFileNameDialog(files=self.files)
            else:
                self.archivo = GuardarArchivo(caption="Guardar archivo", directory=self.directorio,
                                                             filter=self.files,
                                                             filename=self.nombre_archivo)
            if self.widgetArchivo and self.archivo:
                self.widgetArchivo.setText(self.archivo)