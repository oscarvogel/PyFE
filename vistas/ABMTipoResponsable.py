

from libs.Checkbox import CheckBox
from libs.Utiles import inicializar_y_capturar_excepciones
from modelos.Tiporesp import Tiporesp
from vistas.ABM import ABM


class ABMTipoResponsableView(ABM):

    model = Tiporesp()
    camposAMostrar = [Tiporesp.idtiporesp, Tiporesp.nombre]
    ordenBusqueda = Tiporesp.nombre
    campoClave = Tiporesp.idtiporesp
    autoincremental = False

    def __init__(self, *args, **kwargs):
        ABM.__init__(self, *args, **kwargs)

    @inicializar_y_capturar_excepciones
    def ArmaCarga(self, *args, **kwargs):
        self.layoutID = self.ArmaEntrada(Tiporesp.idtiporesp.name, texto='Codigo')
        self.ArmaEntrada(Tiporesp.nombre.name, boxlayout=self.layoutID)
        layoutDiscrimina = self.ArmaEntrada(Tiporesp.discrimina.name, control=CheckBox())
        self.ArmaEntrada(Tiporesp.tipoiva.name, boxlayout=layoutDiscrimina)
        self.ArmaEntrada(Tiporesp.obligacuit.name, boxlayout=layoutDiscrimina, control=CheckBox())
        layoutFactura = self.ArmaEntrada(Tiporesp.factura.name)
        self.ArmaEntrada(Tiporesp.notacredito.name, boxlayout=layoutFactura)
        self.ArmaEntrada(Tiporesp.notadebito.name, boxlayout=layoutFactura)
        self.ArmaEntrada(Tiporesp.tipoivaepson.name, boxlayout=layoutFactura)
        self.ArmaEntrada(Tiporesp.condicion_iva_receptor_id.name, boxlayout=layoutFactura)