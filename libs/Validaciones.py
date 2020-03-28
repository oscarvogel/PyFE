# coding=utf-8
from PyQt5 import QtCore
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QLineEdit, QHBoxLayout

from libs.EntradaTexto import EntradaTexto
from libs.Etiquetas import Etiqueta, EtiquetaRoja
from vistas.Busqueda import UiBusqueda


class Validaciones(EntradaTexto):

    #modelo sobre la que se consulta
    modelo = ''

    #orden para la busqueda si se presiona F2
    cOrden = ''

    #campos que se van a mostrar
    campos = ''

    #campos de la tabla, permite hacer uniones de campos
    camposTabla = None

    #el campo que va a retornar la busqueda
    campoRetorno = None

    #el campo del nombre
    campoNombre = None

    #largo se utiliza para la cantidad de ingreso y para el zfill y rellanar con ceros
    largo = 0

    #este es el widget que va a contener la descripcion del nombre
    widgetNombre = None

    #en caso de que necesitems hacer una condicion para mostrar los datos se utiliza esta propiedad
    condiciones = ''

    #indica si el valor obtenido es valido o no
    valido = False

    #cursor que guarda los valores obtenidos por el outfocus
    cursor = None

    def __init__(self, parent=None, *args, **kwargs):
        EntradaTexto.__init__(self, parent, *args, **kwargs)
        font = QFont()
        font.setPointSizeF(12)
        self.setFont(font)
        if self.largo != 0:
            self.setMaxLength(self.largo)
        self.setMaximumWidth(50)

    def keyPressEvent(self, event):
        self.lastKey = event.key()
        if event.key() == QtCore.Qt.Key_F2:
            ventana = UiBusqueda()
            ventana.modelo = self.modelo
            ventana.cOrden = self.cOrden
            ventana.campos = self.campos
            ventana.campoBusqueda = self.cOrden
            ventana.camposTabla = self.camposTabla
            ventana.campoRetorno = self.campoRetorno
            ventana.condiciones = self.condiciones
            ventana.CargaDatos()
            ventana.exec_()
            if ventana.lRetval:
                self.setText(ventana.ValorRetorno)
                self.valido = True
                QLineEdit.keyPressEvent(self, event)
        elif event.key() == QtCore.Qt.Key_Enter or \
                        event.key() == QtCore.Qt.Key_Return or\
                        event.key() == QtCore.Qt.Key_Tab:
            self.valida()
            if self.proximoWidget:
                self.proximoWidget.setFocus()
        QLineEdit.keyPressEvent(self, event)

    def focusOutEvent(self, QFocusEvent):
        if self.lastKey != QtCore.Qt.Key_F2:
            self.valida()
        QLineEdit.focusOutEvent(self, QFocusEvent)

    def valida(self):
        if not self.text():
            return
        if self.largo != 0:
            self.setText(str(self.text()).zfill(self.largo))
        #data = SQL().BuscaUno(self.tabla, self.campoRetorno, self.text())
        data = self.modelo.select().where(self.campoRetorno == self.text()).dicts()
        if data:
            self.valido = True
            self.setStyleSheet("background-color: Dodgerblue")
            self.cursor = data
            if self.widgetNombre:
                for d in data:
                    self.widgetNombre.setText(d[self.campoNombre.column_name].strip())
        else:
            self.valido = False
            self.setStyleSheet("background-color: yellow")
            #Ventanas.showAlert("Error", "Codigo no encontrado en el sistema")


class ValidaConNombre(QHBoxLayout):

    textoEtiqueta = 'Nombre'
    modelo = None
    campoNombre = None
    campoRetorno = None
    camposTabla = []
    largo = 0
    maxwidth = 50

    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent)

        if 'texto' in kwargs:
            self.textoEtiqueta = kwargs['texto']

        self.labelNombre = Etiqueta(parent, texto=self.textoEtiqueta)
        self.labelNombre.setObjectName("labelNombre")
        self.addWidget(self.labelNombre)

        self.lineEditCodigo = Validaciones(parent)
        self.lineEditCodigo.setObjectName("lineEditNombre")
        self.lineEditCodigo.modelo = self.modelo
        self.lineEditCodigo.campoNombre = self.campoNombre
        self.lineEditCodigo.campoRetorno = self.campoRetorno
        self.lineEditCodigo.cOrden = self.campoNombre
        self.lineEditCodigo.camposTabla = self.camposTabla
        self.lineEditCodigo.campos = self.lineEditCodigo.camposTabla
        self.lineEditCodigo.largo = self.largo
        self.lineEditCodigo.setMaximumWidth(self.maxwidth)
        self.addWidget(self.lineEditCodigo)

        self.labelDescripcion = EtiquetaRoja(parent, texto="")
        self.labelDescripcion.setObjectName("labelDescripcion")
        self.addWidget(self.labelDescripcion)
        self.lineEditCodigo.widgetNombre = self.labelDescripcion