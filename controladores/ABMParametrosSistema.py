# coding=utf-8
from controladores.ControladorBase import ControladorBase
from modelos.ParametrosSistema import ParamSist
from vistas.ABMParametrosSistema import ABMParamSistView


class ABMParamSistController(ControladorBase):

    def __init__(self):
        super().__init__()
        self.view = ABMParamSistView()
        #self.view.exec_()
        self.conectarWidgets()

    def conectarWidgets(self):
        self.view.btnAceptar.clicked.connect(self.onClickBtnAceptar)

    def onClickBtnAceptar(self):

        if self.view.tipo == 'M':
            param = ParamSist.get_by_id(self.view.controles[ParamSist.id.column_name].text())
        else:
            param = ParamSist()

        param.valor = self.view.controles[ParamSist.valor.column_name].text()
        param.parametro = self.view.controles[ParamSist.parametro.column_name].text()
        param.save()
        self.view.btnAceptarClicked()