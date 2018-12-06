# coding=utf-8
from libs.Utiles import inicializar_y_capturar_excepciones
from modelos.Localidades import Localidad
from vistas.ABM import ABM


class LocalidadesView(ABM):

    model = Localidad()
    camposAMostrar = [Localidad.idlocalidad, Localidad.nombre, Localidad.provincia, Localidad.nacion]
    ordenBusqueda = Localidad.nombre
    campoClave = Localidad.idlocalidad

    def __init__(self, *args, **kwargs):
        ABM.__init__(self, *args, **kwargs)

    @inicializar_y_capturar_excepciones
    def ArmaCarga(self, *args, **kwargs):
        self.layoutID = self.ArmaEntrada('idlocalidad', texto='Codigo')
        self.ArmaEntrada('nombre', boxlayout=self.layoutID)
        self.layoutProv = self.ArmaEntrada('provincia')
        self.ArmaEntrada('nacion', boxlayout=self.layoutProv)

    @inicializar_y_capturar_excepciones
    def btnAceptarClicked(self, *args, **kwargs):
        if self.tipo == 'M':
            localidad = Localidad.get_by_id(self.controles[Localidad.idlocalidad.column_name].text())
            localidad.idlocalidad = self.controles['idlocalidad'].text()
        else:
            localidad = Localidad()
        localidad.nombre = self.controles['nombre'].text()
        localidad.provincia = self.controles['provincia'].text()
        localidad.nacion = self.controles['nacion'].text()
        localidad.save()
        ABM.btnAceptarClicked(self)