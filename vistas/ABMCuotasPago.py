from libs.Spinner import Spinner
from libs.Utiles import inicializar_y_capturar_excepciones
from modelos.CuotasPago import CuotaPago
from modelos.Formaspago import ComboFormapago
from vistas.ABM import ABM


class ABMCuotasPagoView(ABM):

    model = CuotaPago()
    camposAMostrar = [CuotaPago.idcuota, CuotaPago.formapago,
                      CuotaPago.cuotas, CuotaPago.recargo]
    ordenBusqueda = CuotaPago.cuotas
    campoClave = CuotaPago.idcuota

    def __init__(self, *args, **kwargs):
        ABM.__init__(self, *args, **kwargs)

    @inicializar_y_capturar_excepciones
    def ArmaCarga(self, *args, **kwargs):
        self.layoutID = self.ArmaEntrada(CuotaPago.idcuota.column_name,
                                         texto='Codigo')
        self.ArmaEntrada(CuotaPago.formapago.column_name, texto='Forma pago',
                         boxlayout=self.layoutID,
                         control=ComboFormapago())
        lineaNum = self.ArmaEntrada(CuotaPago.cuotas.column_name,
                                    texto='Cuotas',
                                    control=Spinner(decimales=0))
        self.ArmaEntrada(CuotaPago.recargo.column_name, texto='Recargo %',
                         control=Spinner(decimales=2), boxlayout=lineaNum)
