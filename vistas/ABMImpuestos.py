from libs.Spinner import Spinner
from libs.Utiles import inicializar_y_capturar_excepciones
from modelos.Impuestos import Impuesto
from vistas.ABM import ABM


class ABMImpuestoView(ABM):

    model = Impuesto()
    camposAMostrar = [Impuesto.idimpuesto, Impuesto.detalle, Impuesto.porcentaje, Impuesto.minimo]
    ordenBusqueda = Impuesto.detalle
    campoClave = Impuesto.idimpuesto

    def __init__(self, *args, **kwargs):
        ABM.__init__(self, *args, **kwargs)

    @inicializar_y_capturar_excepciones
    def ArmaCarga(self, *args, **kwargs):
        self.layoutID = self.ArmaEntrada(Impuesto.idimpuesto.column_name, texto='Codigo')
        self.ArmaEntrada(Impuesto.detalle.column_name, boxlayout=self.layoutID)
        layoutLinea1 = self.ArmaEntrada(Impuesto.minimo.column_name, control=Spinner())
        self.ArmaEntrada(Impuesto.porcentaje.column_name, control=Spinner(), boxlayout=layoutLinea1)