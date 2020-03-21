from modelos.Tipodoc import Tipodoc
from vistas.ABM import ABM


class ABMTipoDocumentoView(ABM):

    model = Tipodoc()
    camposAMostrar = [Tipodoc.codigo, Tipodoc.nombre]
    ordenBusqueda = Tipodoc.nombre
    campoClave = Tipodoc.codigo

    def __init__(self, *args, **kwargs):
        ABM.__init__(self, *args, **kwargs)

