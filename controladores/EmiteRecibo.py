# coding=utf-8
from datetime import datetime

from PyQt5.QtCore import Qt
from PyQt5.uic.properties import QtGui

from controladores.ControladorBase import ControladorBase
from modelos import Tipocomprobantes
from modelos.Cabfact import Cabfact
from modelos.Clientes import Cliente
from modelos.Tipocomprobantes import TipoComprobante
from vistas.EmiteRecibo import EmiteReciboView


class EmiteReciboController(ControladorBase):

    def __init__(self):
        super(EmiteReciboController, self).__init__()
        self.view = EmiteReciboView()
        self.conectarWidgets()
        self.EstablecerOrden()

    def conectarWidgets(self):
        self.view.btnCerra.clicked.connect(self.view.Cerrar)
        self.view.controles['cliente'].editingFinished.connect(self.CargaDeuda)
        self.view.btnAgrega.clicked.connect(self.AgregaPago)
        self.view.gridDeuda.keyPressed.connect(self.onKeyPressedGridDeuda)
        self.view.gridPagos.keyPressed.connect(self.onKeyPressedGridPagos)
        self.view.btnGraba.clicked.connect(self.onClickGraba)

    def CargaDeuda(self):
        self.view.gridDeuda.setRowCount(0)
        if not self.view.controles['cliente'].text():
            return
        cabfact = Cabfact().select().where(Cabfact.saldo != 0, Cabfact.cliente == self.view.controles['cliente'].text())

        for c in cabfact:
            if c.tipocomp.lado == 'H':
                saldo = c.saldo * -1
            else:
                saldo = c.saldo
            item = [
                c.tipocomp.nombre, c.numero, c.fecha, saldo, 0, c.idcabfact
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
        # modifiers = QtGui.QApplication.keyboardModifiers()
        # if modifiers == Qt.ControlModifier:
        #     if key in [Qt.Key_Enter, Qt.Key_Return]:
        #         fila = self.view.gridDeuda.currentRow()
        #         saldar = self.view.gridDeuda.ObtenerItem(fila=fila, col='Saldo')
        #         self.view.gridDeuda.ModificaItem(valor=saldar, fila=fila, col='a Saldar')
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
        if key == Qt.Key_F2:
            if colact == 0:
                ventana = Tipocomprobantes.Busqueda()
                ventana.CargaDatos()
                ventana.exec_()
                if ventana.lRetval:
                    self.view.gridPagos.ModificaItem(valor=ventana.ValorRetorno,
                                                     fila=fila, col=colact)

            self.view.gridPagos.setFocus()

        self.SumaPagos()

    def SumaPagos(self):
        total = 0.
        for x in range(self.view.gridPagos.rowCount()):
            total += float(self.view.gridPagos.ObtenerItem(fila=x, col='Importe'))

        self.view.controles['pagos'].setText(str(round(total, 3)))

    def EstablecerOrden(self):
        self.view.controles['cliente'].proximoWidget = self.view.gridDeuda

    def onClickGraba(self):
        self.SumaDeuda()
        self.SumaPagos()
        cliente = Cliente.get_by_id(int(self.view.controles['cliente'].text()))
        recibo = Cabfact()
        recibo.tipocomp = Tipocomprobantes.CODIGO_RECIBO
        recibo.cliente = cliente.idcliente
        recibo.fecha = datetime.today()
        recibo.numero = str(TipoComprobante().SiguienteNumero(Tipocomprobantes.CODIGO_RECIBO)).zfill(12)
        recibo.total = float(self.view.controles['pagos'].text())
        if float(self.view.controles['saldo'].text()) < 0:
            recibo.saldo = abs(float(self.view.controles['saldo'].text()))

        recibo.tipoiva = cliente.tiporesp.idtiporesp
        recibo.formapago = Tipocomprobantes.FORMA_PAGO['Cta Cte']
        recibo.nombre = cliente.nombre
        recibo.domicilio = cliente.domicilio
        recibo.save()

        for x in range(self.view.gridDeuda.rowCount()):
            id = self.view.gridDeuda.ObtenerItem(fila=x, col='id') or 0
            importe = float(self.view.gridDeuda.ObtenerItem(fila=x, col='a Saldar') or 0)
            cabecera = Cabfact.get_by_id(int(id))
            cabecera.saldo = float(cabecera.saldo) - abs(importe)
            cabecera.desde = "0000-00-00"
            cabecera.hasta = "0000-00-00"
            cabecera.venccae = "0000-00-00"
            cabecera.save()