# coding=utf-8
import decimal

from PyQt4.QtCore import Qt
from PyQt4.QtGui import QComboBox, QFont


class ComboSQL(QComboBox):

    lTodos = False
    cBaseDatos = ''
    cSentencia = ''
    campo1 = ''
    campo2 = ''
    campovalor = ''
    condicion = ''
    tabla = ''
    cOrden = None
    model = None

    def __init__(self, *args, **kwargs):
        QComboBox.__init__(self)
        font = QFont()
        font.setPointSizeF(12)
        self.setFont(font)
        self.CargaDatos()

    def CargaDatos(self):
        self.clear()
        if not self.model:
            return
        data = self.model.select().dicts()
        if self.cOrden:
            data = data.order_by(self.cOrden)

        for r in data:
            if isinstance(r[self.campovalor], (decimal.Decimal,)):
                valor = str(r[self.campovalor])
            else:
                valor = r[self.campovalor]
            if isinstance(r[self.campo1], (decimal.Decimal,)):
                campo1 = str(r[self.campo1])
            else:
                campo1 = r[self.campo1]
            self.addItem(campo1, valor)

    def GetDato(self):
        return self.currentData()

    def text(self):
        if self.currentData():
            return self.currentData()
        else:
            return self.currentText()

    def setText(self, p_str):
        index = self.findText(p_str)
        self.setCurrentIndex(index)

    def setIndex(self, p_str):
        self.setCurrentIndex(self.findText(p_str))

class Combo(QComboBox):

    proximoWidget = None
    data = None

    def __init__(self, parent=None, *args, **kwargs):
        QComboBox.__init__(self, parent)
        font = QFont()
        if 'tamanio' in kwargs:
            font.setPointSizeF(kwargs['tamanio'])
        else:
            font.setPointSizeF(12)

        if 'enabled' in kwargs:
            self.setEnabled(kwargs['enabled'])

        self.setFont(font)

    def CargaDatos(self, data=None):
        if data:
            for r in data:
                self.addItem(r)

    def CargaDatosValores(self, data=None):
        self.clear()
        if data:
            for k, v in data.items():
                self.addItem(v, k)

    def text(self):
        return self.currentText()
        # if self.currentData():
        #     return self.currentData()
        # else:
        #     return self.currentText()
        #return self.itemData(self.currentIndex(), Qt.DisplayRole)

    def setText(self, p_str):
        index = self.findText(p_str)
        self.setCurrentIndex(index)

    def setIndex(self, p_str):
        self.setCurrentIndex(self.findData(p_str))

class ComboSINO(Combo):

    def __init__(self, parent=None, *args, **kwargs):
        Combo.__init__(self, parent, *args, **kwargs)
        self.CargaDatosValores(data={'S':'SI','N':'NO'})

class FormaPago(Combo):

    def __init__(self, parent=None, *args, **kwargs):
        Combo.__init__(self, parent, *args, **kwargs)
        self.CargaDatosValores(data={'S':'Contado','N':'Cuenta corriente'})
