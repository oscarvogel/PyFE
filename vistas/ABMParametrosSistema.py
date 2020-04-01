# coding=utf-8
from libs.Utiles import inicializar_y_capturar_excepciones
from modelos.ParametrosSistema import ParamSist
from vistas.ABM import ABM


class ABMParamSistView(ABM):

    model = ParamSist()
    camposAMostrar = [ParamSist.id, ParamSist.parametro, ParamSist.valor]
    ordenBusqueda = ParamSist.parametro
    campoClave = ParamSist.id

    def __init__(self, *args, **kwargs):
        ABM.__init__(self, *args, **kwargs)

    @inicializar_y_capturar_excepciones
    def ArmaCarga(self, *args, **kwargs):
        codigo = self.ArmaEntrada(ParamSist.id.column_name)
        parametro = self.ArmaEntrada(ParamSist.parametro.column_name)
        valor = self.ArmaEntrada(ParamSist.valor.column_name)

    def PostAgrega(self):
        self.controles[ParamSist.parametro.column_name].setEnabled(True)

    def PostModifica(self):
        self.controles[ParamSist.parametro.column_name].setEnabled(False)