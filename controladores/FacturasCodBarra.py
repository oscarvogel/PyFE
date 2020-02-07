# coding=utf-8
from PyQt5.QtCore import Qt

from controladores.ControladorBase import ControladorBase
from libs import Ventanas
from vistas.FacturasCodBarra import FacturaCodBarraView


class FacturaCodBarraController(ControladorBase):

    cliente = None #modelo cliente
    tipo_cpte = 1 #tipo de comprobante a facturar
    netos = {
        0:0,
        10.5:0,
        21:0
    }
    concepto = '1' #concepto de factura electronica (productos, servicios o ambos)

    def __init__(self):
        super(FacturaCodBarraController, self).__init__()
        self.view = FacturaCodBarraView()
        self.conectarWidgets()
        self.EstablecerOrden()

    def conectarWidgets(self):
        self.view.textCodBarra.keyPressed.connect(self.ProcesaCodBarra)

    def ProcesaCodBarra(self, key):

        if key in [Qt.Key_Return, Qt.Key_Enter]:
            if str(self.view.textCodBarra.text()).startswith('+'):
                if self.ProcesaTotales():
                    pass
                else:
                    Ventanas.showAlert("Sistema", "El monto es menor al total de la compra")

    def ProcesaTotales(self):
        pass