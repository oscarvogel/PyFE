# coding=utf-8
from controladores.ControladorBase import ControladorBase
from controladores.FE import FEv1
from libs import Ventanas
from vistas.ConsultaCAE import ConsultaCAEView


class ConsultaCAEController(ControladorBase):

    def __init__(self):
        super(ConsultaCAEController, self).__init__()
        self.view = ConsultaCAEView()
        self.conectarWidgets()

    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(self.view.cerrarformulario)
        self.view.btnConsultar.clicked.connect(self.ConsultaCAE)

    def ConsultaCAE(self):
        fe = FEv1()
        # tipocbte = [k for (k, v) in self.view.cboTipoComp.valores.iteritems() if v == self.view.cboTipoComp.text()][0]
        tipocbte = self.view.cboTipoComp.text()
        fe.ConsultarCAE(tipocbte=tipocbte,
                        puntoventa=self.view.layoutFactura.lineEditPtoVta.text(),
                        numero=self.view.layoutFactura.lineEditNumero.text())
        if fe:
            self.view.textCAE.setText(fe.CAE)
            self.view.textTotal.setText(str(fe.ImpTotal))
            self.view.textNeto.setText(str(fe.ImpNeto))
            self.view.textIVA.setText(str(fe.ImpIVA))
            self.view.textDGR.setText(str(fe.ImpTrib))
            self.view.textTipoDoc.setText(str(fe.factura["tipo_doc"]))
            self.view.textDocCli.setText(str(fe.factura["nro_doc"]))
            self.view.textFecha.setText(fe.FechaCbte)
            self.view.gridIVA.setRowCount(0)
            for iva in fe.factura['iva']:
                item = [
                    iva['iva_id'], iva['base_imp'], iva['importe']
                ]
                self.view.gridIVA.AgregaItem(items=item)
        else:
            Ventanas.showAlert("Sistema", "Comprobante consultado no valido")
