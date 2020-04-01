# coding=utf-8
import datetime
import decimal

from PyQt5 import QtCore
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QComboBox

from libs.Utiles import InicioMes


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
    proximoWidget = None
    valor_defecto = ''  # valor por defecto, para establecer el indice a ese valor

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

        indice_defecto = 0 #indice por defecto si se encuentra el valor
        indice = 0 #contador para saber el indice como va avanzando
        for r in data:
            if isinstance(r[self.campovalor], (decimal.Decimal, int, float)):
                valor = str(r[self.campovalor])
            else:
                valor = r[self.campovalor]
            if isinstance(r[self.campo1], (decimal.Decimal, int, float)):
                campo1 = str(r[self.campo1])
            else:
                campo1 = r[self.campo1]
            self.addItem(campo1, valor)
            if campo1.strip() == self.valor_defecto or valor.strip() == self.valor_defecto:
                indice_defecto = indice
            indice += 1

        self.setCurrentIndex(indice_defecto)
        self.PostCargaDatos()

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

    def keyPressEvent(self, event):
        self.lastKey = event.key()
        if event.key() == QtCore.Qt.Key_Enter or \
                        event.key() == QtCore.Qt.Key_Return or\
                        event.key() == QtCore.Qt.Key_Tab:
            if self.proximoWidget:
                self.proximoWidget.setFocus()
        QComboBox.keyPressEvent(self, event)

    #en caso de que se quiera agregar un dato extra luego de haber cargados todos los valores de la tabla
    #por ej para un valor en blanco
    def PostCargaDatos(self):
        pass

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
        # return self.currentText()
        if self.currentData():
            return self.currentData()
        else:
            return self.currentText()
        #return self.itemData(self.currentIndex(), Qt.DisplayRole)

    def setText(self, p_str):
        index = self.findText(p_str)
        self.setCurrentIndex(index)

    def setIndex(self, p_str):
        self.setCurrentIndex(self.findData(p_str))

    def GetDato(self):
        return self.currentText()

class ComboSINO(Combo):

    def __init__(self, parent=None, *args, **kwargs):
        Combo.__init__(self, parent, *args, **kwargs)
        self.CargaDatosValores(data={'S':'SI','N':'NO'})

class FormaPago(Combo):

    def __init__(self, parent=None, *args, **kwargs):
        Combo.__init__(self, parent, *args, **kwargs)
        self.CargaDatosValores(data={'S':'Contado','N':'Cuenta corriente'})

class ComboConstComp(Combo):

    def __init__(self, parent=None, *args, **kwargs):
        Combo.__init__(self, parent, *args, **kwargs)
        self.CargaDatos(data=[
            'Comprobantes con CAI',
            'Comprobantes Sin CAI',
            'Comprobantes con CAE',
            'Comprobantes con CAEA',
            'Controlador Fiscal CF',
        ])

    def valor(self):
        retorno = ''
        texto = str(self.text())
        if texto.endswith('CAI'):
            if texto.find('Sin') != -1:
                retorno = 'SIN'
            else:
                retorno = 'CAI'
        elif texto.endswith('CAE'):
            retorno = 'CAE'
        elif texto.endswith('CAEA'):
            retorno = 'CAEA'
        elif texto.endswith('CF'):
            retorno = 'CF'

        return retorno

class ComboConceptoFacturacion(Combo):

    def __init__(self, parent=None, *args, **kwargs):
        Combo.__init__(self, parent, *args, **kwargs)
        self.CargaDatosValores(data={'1':'Productos','2':'Servicios'})

class ComboTipoBaseDatos(Combo):

    def __init__(self, parent=None, *args, **kwargs):
        Combo.__init__(self, parent, *args, **kwargs)
        self.CargaDatos(data=[
            'sqlite','mysql','postgresql'
        ])

class ComboTipoRespIVA(Combo):

    def __init__(self, parent=None, *args, **kwargs):
        Combo.__init__(self, parent, *args, **kwargs)
        self.CargaDatosValores(data={
            '1': 'Responsable Inscripto',
            '4': 'Exento',
            '6': 'Monotributo'
        })

class ComboCopiasFE(Combo):

    def __init__(self, parent=None, *args, **kwargs):
        Combo.__init__(self, parent, *args, **kwargs)
        self.CargaDatos(data=[
            '1','2','3','4'
        ])

class ComboPeriodoMonotributo(Combo):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.CargaDatosValores(data={
            '1' : 'Enero/Junio',
            '2' : 'Julio/Diciembre'
        })

    def RangoFecha(self, anio=0):

        if isinstance(anio, float):
            anio = int(anio)

        if self.text() == '1':
            desde = datetime.date(anio -1, 7, 1)
            hasta = datetime.date(anio, 6, 30)
        else:
            desde = datetime.date(anio -1, 1, 1)
            hasta = datetime.date(anio -1, 12, 31)

        return desde, hasta

class ComboActividadMono(Combo):

    def __init__(self, parent=None, *args, **kwargs):
        Combo.__init__(self, parent, *args, **kwargs)
        self.CargaDatosValores(data={
            'S': 'Locaciones y/o Prestaciones de Servicio',
            'V': 'Venta de Cosas Muebles',
        })
