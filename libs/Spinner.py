import datetime

from PyQt4 import QtCore
from PyQt4.QtGui import QHBoxLayout, QDoubleSpinBox, QFont

from libs.Etiquetas import Etiqueta
from libs.Utiles import InicioMes, FinMes


class Spinner(QDoubleSpinBox):

    proximoWidget = None
    tamanio = 12

    def __init__(self, parent=None, *args, **kwargs):
        QDoubleSpinBox.__init__(self, parent)

        font = QFont()
        if 'tamanio' in kwargs:
            self.tamanio = kwargs['tamanio']
        font.setPointSizeF(self.tamanio)
        self.setFont(font)
        self.setMaximum(9999999999)

        if 'decimales' in kwargs:
            self.setDecimals(kwargs['decimales'])
        else:
            self.setDecimals(4)
        if 'enabled' in kwargs:
            self.setEnabled(kwargs['enabled'])

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Enter or \
                        event.key() == QtCore.Qt.Key_Return or\
                        event.key() == QtCore.Qt.Key_Tab:
            if self.proximoWidget:
                self.proximoWidget.setFocus()
            else:
                self.focusNextChild()
        else:
            QDoubleSpinBox.keyPressEvent(self, event)

    def focusInEvent(self, *args, **kwargs):
        self.selectAll()
        QDoubleSpinBox.focusInEvent(self, *args, **kwargs)

    def focusOutEvent(self, *args, **kwargs):
        self.setStyleSheet("background-color: Dodgerblue")
        QDoubleSpinBox.focusOutEvent(self, *args, **kwargs)


class Periodo(QHBoxLayout):

    cPeriodo = ''
    dInicio = None #date que indica el primer dia del mes
    dFin = None #date que indica el ultimo dia del mes
    textoEtiqueta = ''

    def __init__(self, parent=None, *args, **kwargs):

        QHBoxLayout.__init__(self)
        if 'texto' in kwargs:
            textoEtiqueta = kwargs['texto']
            self.labelPeriodo = Etiqueta(parent, texto=textoEtiqueta)
            self.labelPeriodo.setObjectName("labelPeriodo")
            self.addWidget(self.labelPeriodo)

        self.lineEditMes = Spinner(parent)
        self.lineEditMes.setDecimals(0)
        self.lineEditMes.setObjectName("lineEditMes")
        self.addWidget(self.lineEditMes)
        self.lineEditAnio = Spinner(parent)
        self.lineEditAnio.setDecimals(0)
        self.lineEditAnio.setObjectName("lineEditAnio")
        self.addWidget(self.lineEditAnio)

        self.lineEditMes.proximoWidget = self.lineEditAnio
        self.lineEditAnio.valueChanged.connect(self.ActualizaPeriodo)
        self.lineEditMes.valueChanged.connect(self.ActualizaPeriodo)
        self.lineEditAnio.setValue(datetime.date.today().year)
        self.lineEditMes.setValue(datetime.date.today().month)
        self.lineEditMes.setMinimum(1.)
        self.lineEditMes.setMaximum(12.)
        self.lineEditAnio.setMinimum(2000.)
        self.lineEditAnio.setMaximum(2050.)
        self.lineEditAnio.setValue(datetime.date.today().year)

    def ActualizaPeriodo(self):
        self.cPeriodo = self.lineEditAnio.text() + str(self.lineEditMes.text()).zfill(2)
        if self.lineEditMes.value() >= 1 and self.lineEditMes.value() <= 12:
            self.dInicio = InicioMes(datetime.date(int(self.lineEditAnio.value()),
                                               int(self.lineEditMes.value()), 1))
        self.dFin = FinMes(self.dInicio)