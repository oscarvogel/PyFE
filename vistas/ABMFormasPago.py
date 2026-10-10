from libs.Checkbox import CheckBox
from libs.Spinner import Spinner
from libs.Utiles import inicializar_y_capturar_excepciones
from modelos.Formaspago import Formapago
from vistas.ABM import ABM


class ABMFormasPagoView(ABM):

    model = Formapago()
    camposAMostrar = [Formapago.idformapago, Formapago.detalle,
                      Formapago.descuento, Formapago.recargo,
                      Formapago.tarjeta]
    ordenBusqueda = Formapago.detalle
    campoClave = Formapago.idformapago

    def __init__(self, *args, **kwargs):
        ABM.__init__(self, *args, **kwargs)

    @inicializar_y_capturar_excepciones
    def ArmaCarga(self, *args, **kwargs):
        self.layoutID = self.ArmaEntrada(Formapago.idformapago.column_name,
                                         texto='Codigo')
        self.ArmaEntrada(Formapago.detalle.column_name,
                         boxlayout=self.layoutID)
        lineaNum = self.ArmaEntrada(Formapago.descuento.column_name,
                                    texto='Descuento %',
                                    control=Spinner(decimales=2))
        self.ArmaEntrada(Formapago.recargo.column_name, texto='Recargo %',
                         control=Spinner(decimales=2), boxlayout=lineaNum)
        lineaFlags = self.ArmaEntrada(Formapago.ctacte.column_name,
                                      texto='Cta cte', control=CheckBox())
        self.ArmaEntrada(Formapago.tarjeta.column_name, texto='Tarjeta',
                         control=CheckBox(), boxlayout=lineaFlags)
        self.ArmaEntrada(Formapago.mensual.column_name, texto='Mensual',
                         control=CheckBox(), boxlayout=lineaFlags)
