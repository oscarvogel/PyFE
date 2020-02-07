from controladores.ControladorBase import ControladorBase
from libs.Utiles import inicializar_y_capturar_excepciones
from modelos.Impuestos import Impuesto
from vistas.ABMImpuestos import ABMImpuestoView


class ABMImpuestoController(ControladorBase):

    def __init__(self):
        super().__init__()
        self.view = ABMImpuestoView()
        #self.view.exec_()
        self.conectarWidgets()

    def conectarWidgets(self):
        self.view.btnAceptar.clicked.connect(self.onClickBtnAceptar)

    @inicializar_y_capturar_excepciones
    def onClickBtnAceptar(self, *args, **kwargs):
        if self.view.tipo == 'M':
            impuesto = Impuesto.get_by_id(self.view.controles[Impuesto.idimpuesto.column_name].text())
        else:
            impuesto = Impuesto()

        impuesto.detalle = self.view.controles[Impuesto.detalle.column_name].text()[:30]
        impuesto.porcentaje = self.view.controles[Impuesto.porcentaje.column_name].value()
        impuesto.minimo = self.view.controles[Impuesto.minimo.column_name].value()
        impuesto.save()
        self.view.btnAceptarClicked()
