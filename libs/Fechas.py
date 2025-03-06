# coding=utf-8
import datetime

from PyQt5 import QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QDateEdit, QHBoxLayout
from PyQt5.uic.properties import QtGui

from libs.Etiquetas import Etiqueta


class Fecha(QDateEdit):

    proximoWidget = None
    tamanio = 12

    def __init__(self, *args, **kwargs):
        QDateEdit.__init__(self, *args)
        self.setCalendarPopup(True)
        #self.cw = QNCalendarWidget(n=1, columns=1)
        #self.setCalendarWidget(self.cw)

        self.setDisplayFormat('dd/MM/yyyy')
        if 'enabled' in kwargs:
            self.setEnabled(kwargs['enabled'])
        if 'tamanio' in kwargs:
            self.tamanio = kwargs['tamanio']
        font = QFont()
        font.setPointSizeF(self.tamanio)
        self.setFont(font)
        if 'fecha' in kwargs:
            self.setFecha(kwargs['fecha'])
        else:
            self.setFecha()

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

    def keyPressEvent(self, QKeyEvent, *args, **kwargs):
        teclaEnter = [Qt.Key_Enter, Qt.Key_Return, Qt.Key_Tab]
        if QKeyEvent.key() in teclaEnter:
            if self.proximoWidget:
                self.proximoWidget.setFocus()
        QDateEdit.keyPressEvent(self, QKeyEvent, *args, **kwargs)

    def getFechaSql(self):
        # fecha = str(self.text())
        # fecha = datetime.datetime.strptime(fecha, "%d/%m/%Y").date().strftime('%Y%m%d')
        fecha = self.toPyDate().strftime("%Y%m%d")
        return fecha

    def toPyDate(self):
        return self.date().toPyDate()

    def valor(self):
        return self.date().toPyDate()

    def text(self):
        return self.valor()

class RangoFechas(QHBoxLayout):

    etiqueta_desde = "Desde fecha"
    etiqueta_hasta = "Hasta fecha"

    def __init__(self):
        super().__init__()
        self.setupUi()

    def setupUi(self):
        lblDesdeFecha = Etiqueta(texto=self.etiqueta_desde)
        self.desde_fecha = Fecha(fecha=0)
        lblHastaFecha = Etiqueta(texto=self.etiqueta_hasta)
        self.hasta_fecha = Fecha(fecha=0)
        self.addWidget(lblDesdeFecha)
        self.addWidget(self.desde_fecha)
        self.addWidget(lblHastaFecha)
        self.addWidget(self.hasta_fecha)
        self.desde_fecha.proximoWidget = self.hasta_fecha
