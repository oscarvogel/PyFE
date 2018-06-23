# coding=utf-8
from controladores.ControladorBase import ControladorBase
from controladores.Facturas import FacturaController
from modelos.Cabfact import Cabfact
from vistas.ReImprimeFactura import ReImprimeFacturaView


class ReImprimeFacturaController(ControladorBase):

    def __init__(self):
        super(ReImprimeFacturaController, self).__init__()
        self.view = ReImprimeFacturaView()
        self.conectarWidgets()

    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(self.view.Cerrar)
        self.view.controles['cliente'].editingFinished.connect(self.CargaFacturasCliente)
        self.view.btnImprimir.clicked.connect(self.ImprimirFactura)

    def CargaFacturasCliente(self):
        self.view.gridDatos.setRowCount(0)
        cab = Cabfact().select().where(Cabfact.fecha >= self.view.controles['fecha'].date().toPyDate(),
                                       Cabfact.cliente == self.view.controles['cliente'].text())
        for c in cab:
            item = [
                c.fecha, c.numero, c.total, c.idcabfact
            ]
            self.view.gridDatos.AgregaItem(items=item)

    def ImprimirFactura(self):
        if self.view.gridDatos.currentRow() != -1:
            FacturaController().ImprimeFactura(self.view.gridDatos.ObtenerItem(
                fila=self.view.gridDatos.currentRow(), col='idcabecera'))