# coding=utf-8
import decimal

from controladores.ControladorBase import ControladorBase
from modelos.Cabfact import Cabfact
from vistas.ConsultaCtaCte import ConsultaCtaCteView


class ConsultaCtaCteController(ControladorBase):

    def __init__(self):
        super(ConsultaCtaCteController, self).__init__()
        self.view = ConsultaCtaCteView()
        self.conectarWidgets()

    def CuentaCorriente(self):
        if not self.view.lineEditCliente.text():
            return
        modelo = Cabfact()
        modelo = modelo.select().where(Cabfact.cliente == self.view.lineEditCliente.text(),
                                       Cabfact.fecha.between(self.view.desdeFecha.date().toPyDate(),
                                                             self.view.hastaFecha.date().toPyDate()))
        data = []
        saldo = decimal.Decimal.from_float(0.)
        for m in modelo:
            if m.tipocomp.lado == 'H':
                debe = decimal.Decimal.from_float(0)
                haber = m.total
            else:
                haber = decimal.Decimal.from_float(0)
                debe = m.total
            if m.formapago.ctacte:
                saldo += debe - haber
            item = [m.formapago.detalle.strip(), m.tipocomp.nombre.strip(), m.numero, m.fecha, debe, haber, saldo]
            data.append(item)

        self.view.MostrarDeuda(data=data)

    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(self.view.cerrarformulario)
        self.view.btnMostrar.clicked.connect(self.CuentaCorriente)