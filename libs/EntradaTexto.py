# coding=utf-8
import datetime

from PyQt4 import QtCore
from PyQt4.QtGui import QLineEdit, QFont, QHBoxLayout, QTextEdit

from libs import Ventanas
from libs.Etiquetas import Etiqueta
from libs.Utiles import validar_cuit


class EntradaTexto(QLineEdit):

    ventana = None
    # para cuando se presiona ENTER cual es el widget que obtiene el foco
    proximoWidget = None

    # guarda la ultima tecla presionada
    lastKey = None

    largo = 0

    #para campos numericos que debo rellenar con ceros adelante
    relleno = 0

    def __init__(self, parent=None, *args, **kwargs):

        QLineEdit.__init__(self, *args)
        self.ventana = parent
        font = QFont()
        if 'tamanio' in kwargs:
            font.setPointSizeF(kwargs['tamanio'])
        else:
            font.setPointSizeF(12)
        self.setFont(font)

        if 'tooltip' in kwargs:
            self.setToolTip(kwargs['tooltip'])
        if 'placeholderText' in kwargs:
            self.setPlaceholderText(kwargs['placeholderText'])

        if 'alineacion' in kwargs:
            if kwargs['alineacion'].upper() == 'DERECHA':
                self.setAlignment(QtCore.Qt.AlignRight)
            elif kwargs['alineacion'].upper() == 'IZQUIERDA':
                self.setAlignment(QtCore.Qt.AlignLeft)

        if 'enabled' in kwargs:
            self.setEnabled(kwargs['enabled'])

        if 'inputmask' in kwargs:
            self.setInputMask(kwargs['inputmask'])

    def keyPressEvent(self, event):
        self.lastKey = event.key()
        if event.key() == QtCore.Qt.Key_Enter or \
                        event.key() == QtCore.Qt.Key_Return or\
                        event.key() == QtCore.Qt.Key_Tab:
            if self.proximoWidget:
                self.proximoWidget.setFocus()
        QLineEdit.keyPressEvent(self, event)

    def focusOutEvent(self, QFocusEvent):
        if self.relleno > 0:
            self.setText(self.text().zfill(self.relleno))

        if self.text():
            self.setStyleSheet("background-color: Dodgerblue")
        else:
            self.setStyleSheet("background-color: white")
        QLineEdit.focusOutEvent(self, QFocusEvent)

    def focusInEvent(self, QFocusEvent):
        self.selectAll()
        QLineEdit.focusInEvent(self, QFocusEvent)

    def setLargo(self, largo=0):
        if largo > 0:
            self.largo = largo
            self.setMaxLength(self.largo)

    def value(self):
        return float(self.text()) if self.text() else 0.

class Factura(QHBoxLayout):

    numero = ''
    titulo = ''
    tamanio = 12
    enabled = True

    def __init__(self, parent=None, *args, **kwargs):
        QHBoxLayout.__init__(self)
        if 'titulo' in kwargs:
            self.titulo = kwargs['titulo']
        if 'tamanio' in kwargs:
            self.tamanio = kwargs['tamanio']
        if 'enabled' in kwargs:
            self.enabled = kwargs['enabled']

        self.setupUi(parent)

    def setupUi(self, layout):

        if self.titulo:
            self.labelTitulo = Etiqueta(layout, texto=self.titulo, tamanio=self.tamanio)
            self.labelTitulo.setObjectName("labelTitulo")
            self.addWidget(self.labelTitulo)

        self.lineEditPtoVta = EntradaTexto(layout, placeholderText="Pto Vta", tamanio=self.tamanio)
        self.lineEditPtoVta.setObjectName("lineEditPtoVta")
        self.lineEditPtoVta.setEnabled(self.enabled)
        self.addWidget(self.lineEditPtoVta)

        self.lineEditNumero = EntradaTexto(layout, placeholderText="Numero", tamanio=self.tamanio)
        self.lineEditNumero.setObjectName("lineEditNumero")
        self.lineEditNumero.setEnabled(self.enabled)
        self.addWidget(self.lineEditNumero)

        self.lineEditPtoVta.proximoWidget = self.lineEditNumero
        self.lineEditNumero.largo = 8
        self.lineEditPtoVta.largo = 4
        self.lineEditPtoVta.setMaximumWidth(40)
        self.lineEditNumero.setMaximumWidth(70)

        self.lineEditPtoVta.editingFinished.connect(self.AssignNumero)
        self.lineEditNumero.editingFinished.connect(self.AssignNumero)

    def AssignNumero(self):
        if self.lineEditNumero.text():
            self.lineEditNumero.setText(str(self.lineEditNumero.text()).zfill(8))
        if self.lineEditPtoVta.text():
            self.lineEditPtoVta.setText(str(self.lineEditPtoVta.text()).zfill(4))

        self.numero = str(self.lineEditPtoVta.text()).zfill(4) + \
                      str(self.lineEditNumero.text()).zfill(8)


class TextEdit(QTextEdit):
    tamanio = 12

    def __init__(self, *args, **kwargs):
        QTextEdit.__init__(self, *args)
        if 'tamanio' in kwargs:
            self.tamanio = kwargs['tamanio']

        font = QFont()
        font.setPointSizeF(self.tamanio)
        self.setFont(font)


class CUIT(EntradaTexto):

    def __init__(self, *args, **kwargs):
        EntradaTexto.__init__(self, *args, **kwargs)
        self.setInputMask("99-99999999-9")

    def focusOutEvent(self, QFocusEvent):
        EntradaTexto().focusOutEvent(QFocusEvent)
        if not validar_cuit(self.text()):
            Ventanas.showAlert("Sistema", "ERROR: CUIT/CUIL no valido. Verfique!!!")

class EntradaFecha(EntradaTexto):

    def __init__(self, *args, **kwargs):
        EntradaTexto.__init__(self, *args, **kwargs)
        self.setInputMask("99/99/9999")

    def setFecha(self, fecha=datetime.datetime.today(), format=None):
        if format:
            if format == "Ymd":
                fecha = datetime.date(year=int(fecha[:4]),
                                      month=int(fecha[4:6]),
                                      day=int(fecha[-2:]))
        if isinstance(fecha, int):
            if fecha > 0:
                self.setDate(datetime.date.today() + datetime.timedelta(days=fecha))
            else:
                self.setDate(datetime.date.today() - datetime.timedelta(days=abs(fecha)))
        else:
            self.setDate(fecha)

    def getFechaSql(self):
        fecha = str(self.text())
        fecha = datetime.datetime.strptime(fecha, "%d/%m/%Y").date().strftime('%Y%m%d')
        return fecha

    def setDate(self, QDate):
        fecha = QDate.strftime("%d/%m/%Y")
        self.setText(fecha)