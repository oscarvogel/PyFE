# coding=utf-8
import datetime
import decimal

import xlsxwriter
from PyQt4 import QtCore
from PyQt4.QtGui import QTableWidget, QFont, QTableWidgetItem, QColor, QFileDialog

from libs.Utiles import EsVerdadero, AbrirArchivo


class Grilla(QTableWidget):

    #columnas a ocultar
    columnasOcultas = []

    #lista con las cabeceras de la grilla
    cabeceras = []

    #tabla desde la cual obtener los datos
    tabla = None

    #campos de la tabla
    campos = None

    #condiciones para filtrar los datos
    condiciones = None

    #cantidad de registros a mostrar
    limite = 100

    #columnas habilitadas
    columnasHabilitadas = []

    #campos tabla
    camposTabla = None

    #valores a cargar
    data = None

    #indica si esta en la grilla
    engrilla = False

    #indica si las columnas son seleccionables o no
    enabled = False

    #widget para las columnas
    widgetCol = {}

    #color para la columna
    backgroundColorCol = {}

    #tamaño de la fuente
    tamanio = 12

    #emit signal
    keyPressed = QtCore.pyqtSignal(int)

    def __init__(self, *args, **kwargs):

        QTableWidget.__init__(self, *args)
        if 'tamanio' in kwargs:
            self.tamanio = kwargs['tamanio']
        font = QFont()
        font.setPointSizeF(self.tamanio)
        self.setFont(font)
        self.setSortingEnabled(True)

    def ArmaCabeceras(self, cabeceras=None):

        if not cabeceras:
            cabeceras = self.cabeceras

        self.setColumnCount(len(cabeceras))

        for col in range(0, len(cabeceras)):
            self.setHorizontalHeaderItem(col, QTableWidgetItem(cabeceras[col]))

        self.resizeRowsToContents()
        self.resizeColumnsToContents()
        self.cabeceras = cabeceras
        self.OcultaColumnas()

    def AgregaItem(self, items=None,
                   backgroundColor=QColor(255,255,255), readonly=False):

        if items:
            col = 0
            cantFilas = self.rowCount() + 1
            self.setRowCount(cantFilas)
            for x in items:
                flags = QtCore.Qt.ItemIsSelectable
                if isinstance(x, (bool)):
                    item = QTableWidgetItem(x)
                    if x:
                        item.setCheckState(QtCore.Qt.Checked)
                    else:
                        item.setCheckState(QtCore.Qt.Unchecked)
                elif isinstance(x, (int, float, decimal.Decimal)):
                    item = QTableWidgetItem(str(x))
                elif isinstance(x, (datetime.date)):
                    fecha = x.strftime('%d/%m/%Y')
                    item = QTableWidgetItem(fecha)
                elif isinstance(x, (bytes)):
                    if EsVerdadero(x):
                        item = 'Si'
                    else:
                        item = 'No'
                    item = QTableWidgetItem(QTableWidgetItem(x))
                else:
                    item = QTableWidgetItem(QTableWidgetItem(x))

                if readonly:
                    flags = QtCore.Qt.ItemIsSelectable
                elif col in self.columnasHabilitadas:
                    if isinstance(x, (bool)):
                        flags |= QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled
                    else:
                        flags |= QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable
                else:
                    if self.enabled and not readonly:
                        flags |= QtCore.Qt.ItemIsEnabled

                item.setFlags(flags)
                if col in self.backgroundColorCol:
                    item.setBackground(self.backgroundColorCol[col])

                if backgroundColor and isinstance(backgroundColor, QColor):
                    item.setBackground(backgroundColor)

                self.setItem(cantFilas - 1, col, item)
                if col in self.widgetCol:
                   widgetColumna = self.widgetCol[col]
                   self.setCellWidget(cantFilas - 1, col, widgetColumna)

                col += 1
            self.resizeRowsToContents()
            self.resizeColumnsToContents()

    def OcultaColumnas(self):
        for x in self.columnasOcultas:
            self.hideColumn(x)

    def ModificaItem(self, valor, fila, col, backgroundColor=None):
        """

        :param fila: la fila que se quiere modificar
        :param valor: valor a modificar
        :type col: entero en caso de indicar un numero de columna y string si quiero el nombre
        """
        if isinstance(valor, (int, float, decimal.Decimal)):
            item = QTableWidgetItem(str(valor))
        else:
            item = QTableWidgetItem(valor)

        if not isinstance(col, int):
            numCol = self.cabeceras.index(col)
        else:
            numCol = col

        if numCol in self.columnasHabilitadas:
            item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable)
        else:
            # item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            item.setFlags(QtCore.Qt.ItemIsSelectable)

        if col in self.backgroundColorCol:
            item.setBackground(self.backgroundColorCol[col])

        self.setItem(fila, numCol, item)
        self.resizeColumnsToContents()
        #self.dataChanged()

    def ObtenerItem(self, fila, col):

        if isinstance(col, int):
            numCol = col
        else:
            numCol = self.cabeceras.index(col)

        try:
            item = self.item(fila, numCol).text()
        except:
            item = ''
        # model = self.model()
        # index = model.index(fila, numCol)
        #
        # print(model.data(index))
        #return model.data(index).replace(',','.') if model.data(index) else ''
        return item.replace(',','.') if item else 0

    def CargaDatos(self, avance=None):

        self.blockSignals(True)
        self.setRowCount(0)
        self.blockSignals(False)

    def focusInEvent(self, *args, **kwargs):
        self.engrilla = True

    def focusOutEvent(self, *args, **kwargs):
        self.engrilla = False

    def ExportaExcel(self, columnas=None):
        if not columnas:
            columnas = self.cabeceras

        cArchivo = QFileDialog.getSaveFileName(caption="Guardar archivo", directory="", filter="*.XLSX")
        if not cArchivo:
            return

        workbook = xlsxwriter.Workbook(cArchivo[0])
        worksheet = workbook.add_worksheet()

        fila = 0
        for row in range(self.rowCount()):
            col = 0
            for c in columnas:
                dato = self.ObtenerItem(fila=row, col=c)
                if dato.isdigit():
                    dato = int(dato)
                worksheet.write(fila, col, dato)
                col += 1
            fila += 1

        workbook.close()
        AbrirArchivo(cArchivo[0])

    def keyPressEvent(self, event):
        super(Grilla, self).keyPressEvent(event)
        self.keyPressed.emit(event.key())

