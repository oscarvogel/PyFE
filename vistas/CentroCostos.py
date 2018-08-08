# coding=utf-8
from libs.Utiles import inicializar_y_capturar_excepciones
from modelos.CentroCostos import CentroCosto
from vistas.ABM import ABM


class CentroCostosView(ABM):

    model = CentroCosto()
    camposAMostrar = [CentroCosto.idctrocosto, CentroCosto.nombre]
    ordenBusqueda = CentroCosto.nombre
    campoClave = CentroCosto.idctrocosto

    def __init__(self, *args, **kwargs):
        ABM.__init__(self, *args, **kwargs)

    @inicializar_y_capturar_excepciones
    def ArmaCarga(self, *args, **kwargs):
        self.layoutID = self.ArmaEntrada('idctrocosto', texto='Codigo')
        self.ArmaEntrada('nombre', boxlayout=self.layoutID)

    @inicializar_y_capturar_excepciones
    def btnAceptarClicked(self, *args, **kwargs):
        if self.tipo == 'M':
            centro = CentroCosto.get_by_id(self.controles[CentroCosto.idctrocosto.column_name].text())
            centro.idcliente = self.controles['idctrocosto'].text()
        else:
            centro = CentroCosto()
        centro.nombre = self.controles['nombre'].text()
        centro.save()
        ABM.btnAceptarClicked(self)