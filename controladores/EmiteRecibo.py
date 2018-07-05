# coding=utf-8
from PyQt4 import QtGui
from PyQt4.QtCore import Qt

from controladores.ControladorBase import ControladorBase
from modelos import Tipocomprobantes
from modelos.Cabfact import Cabfact
from vistas.EmiteRecibo import EmiteReciboView


class EmiteReciboController(ControladorBase):

    def __init__(self):
        super(EmiteReciboController, self).__init__()
        self.view = EmiteReciboView()
        self.conectarWidgets()

    def conectarWidgets(self):
        self.view.btnCerra.clicked.connect(self.view.Cerrar)
        self.view.controles['cliente'].editingFinished.connect(self.CargaDeuda)
        self.view.btnAgrega.clicked.connect(self.AgregaPago)
        self.view.gridDeuda.keyPressed.connect(self.onKeyPressedGridDeuda)
        self.view.gridPagos.keyPressed.connect(self.onKeyPressedGridPagos)

    def CargaDeuda(self):
        self.view.gridDeuda.setRowCount(0)
        if not self.view.controles['cliente'].text():
            return
        cabfact = Cabfact().select().where(Cabfact.saldo != 0, Cabfact.cliente == self.view.controles['cliente'].text())

        for c in cabfact:
            item = [
                c.tipocomp.nombre, c.numero, c.fecha, c.saldo, 0
            ]
            self.view.gridDeuda.AgregaItem(items=item)

        item = [
            u'A Cuenta', u'', u'', 0, 0
        ]
        self.view.gridDeuda.AgregaItem(items=item)
        self.SumaDeuda()

    def AgregaPago(self):
        self.view.gridPagos.setRowCount(self.view.gridPagos.rowCount() + 1)

    def onKeyPressedGridDeuda(self, key):
        modifiers = QtGui.QApplication.keyboardModifiers()
        if modifiers == Qt.ControlModifier:
            if key in [Qt.Key_Enter, Qt.Key_Return]:
                fila = self.view.gridDeuda.currentRow()
                saldar = self.view.gridDeuda.ObtenerItem(fila=fila, col='Saldo')
                self.view.gridDeuda.ModificaItem(valor=saldar, fila=fila, col='a Saldar')
        self.SumaDeuda()

    def SumaDeuda(self):
        total = 0.
        salda = 0.
        for x in range(self.view.gridDeuda.rowCount()):
            total += float(self.view.gridDeuda.ObtenerItem(fila=x, col='Saldo'))
            salda += float(self.view.gridDeuda.ObtenerItem(fila=x, col='a Saldar'))

        self.view.controles['deuda'].setText(str(round(total, 3)))
        self.view.controles['saldo'].setText(str(round(total-salda, 3)))

    def onKeyPressedGridPagos(self, key):
        fila = self.view.gridPagos.currentRow()
        colact = self.view.gridPagos.currentColumn()
        print("Col act {}".format(colact))
        if key == Qt.Key_F2:
            if colact == 0:
                Tipocomprobantes.Busqueda()