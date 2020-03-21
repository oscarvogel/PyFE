from libs.Utiles import inicializar_y_capturar_excepciones
from modelos.Tipodoc import Tipodoc
from vistas.ABM import ABM


class ABMTipoDocumentoView(ABM):

    model = Tipodoc()
    camposAMostrar = [Tipodoc.codigo, Tipodoc.nombre]
    ordenBusqueda = Tipodoc.nombre
    campoClave = Tipodoc.codigo
    autoincremental = False

    def __init__(self, *args, **kwargs):
        ABM.__init__(self, *args, **kwargs)

    @inicializar_y_capturar_excepciones
    def ArmaCarga(self, *args, **kwargs):
        self.layoutID = self.ArmaEntrada(Tipodoc.codigo.name, texto='Codigo')
        self.ArmaEntrada(Tipodoc.nombre.name, boxlayout=self.layoutID)
