from libs.Spinner import Spinner
from libs.Utiles import inicializar_y_capturar_excepciones
from modelos.CategoriasMonotributo import CategoriaMono
from vistas.ABM import ABM


class ABMCategoriaMonoView(ABM):

    model = CategoriaMono()
    camposAMostrar = [CategoriaMono.categoria, CategoriaMono.ing_brutos, CategoriaMono.imp_cosas_muebles,
                      CategoriaMono.imp_servicio, CategoriaMono.obra_social,
                      CategoriaMono.sipa]
    # camposAMostrar = [CategoriaMono.categoria, CategoriaMono.imp_cosas_muebles, CategoriaMono.sipa]

    ordenBusqueda = CategoriaMono.categoria
    campoClave = CategoriaMono.categoria
    autoincremental = False

    @inicializar_y_capturar_excepciones
    def ArmaCarga(self, *args, **kwargs):
        layoutID = self.ArmaEntrada(CategoriaMono.categoria)
        self.ArmaEntrada(CategoriaMono.ing_brutos, boxlayout=layoutID,
                         control=Spinner(decimales=2))
        self.ArmaEntrada(CategoriaMono.sup_afectada, boxlayout=layoutID,
                         control=Spinner(decimales=0))
        self.ArmaEntrada(CategoriaMono.energia_electrica, boxlayout=layoutID,
                         control=Spinner(decimales=0))
        self.ArmaEntrada(CategoriaMono.alquileres, boxlayout=layoutID,
                         control=Spinner(decimales=2))

        layoutValores = self.ArmaEntrada(CategoriaMono.sipa, control=Spinner(decimales=2))
        self.ArmaEntrada(CategoriaMono.imp_servicio, control=Spinner(decimales=2), boxlayout=layoutValores)
        self.ArmaEntrada(CategoriaMono.imp_cosas_muebles, control=Spinner(decimales=2), boxlayout=layoutValores)
        self.ArmaEntrada(CategoriaMono.obra_social, control=Spinner(decimales=2), boxlayout=layoutValores)
