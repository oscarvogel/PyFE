# coding=utf-8
from libs.Utiles import inicializar_y_capturar_excepciones
from modelos.Grupos import Grupo
from vistas.ABM import ABM


class ABMGruposView(ABM):

    model = Grupo()
    camposAMostrar = [Grupo.idgrupo, Grupo.nombre]
    ordenBusqueda = Grupo.nombre
    campoClave = Grupo.idgrupo

    def __init__(self, *args, **kwargs):
        ABM.__init__(self, *args, **kwargs)

    @inicializar_y_capturar_excepciones
    def ArmaCarga(self, *args, **kwargs):
        self.layoutID = self.ArmaEntrada(Grupo.idgrupo.column_name, texto='Codigo')
        self.ArmaEntrada(Grupo.nombre.column_name, boxlayout=self.layoutID)

    @inicializar_y_capturar_excepciones
    def btnAceptarClicked(self, *args, **kwargs):
        if self.tipo == 'M':
            grupo = Grupo.get_by_id(self.controles[Grupo.idgrupo.column_name].text())
        else:
            grupo = Grupo()
        grupo.nombre = self.controles[Grupo.nombre.column_name].text()
        grupo.save()
        ABM.btnAceptarClicked(self)

