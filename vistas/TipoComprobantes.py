# coding=utf-8
from libs.Checkbox import CheckBox
from libs.Utiles import inicializar_y_capturar_excepciones
from modelos.Tipocomprobantes import TipoComprobante, ComboTipoIngreso
from vistas.ABM import ABM


class TipoComprobantesView(ABM):

    model = TipoComprobante()
    camposAMostrar = [TipoComprobante.codigo, TipoComprobante.nombre]
    ordenBusqueda = TipoComprobante.nombre
    campoClave = TipoComprobante.codigo
    autoincremental = False

    def __init__(self, *args, **kwargs):
        ABM.__init__(self, *args, **kwargs)

    @inicializar_y_capturar_excepciones
    def ArmaCarga(self, *args, **kwargs):
        self.layoutID = self.ArmaEntrada('codigo', texto='Codigo')
        self.ArmaEntrada('nombre', boxlayout=self.layoutID)
        self.linea1 = self.ArmaEntrada('abreviatura')
        self.ArmaEntrada('lado', texto="Tipo ingreso (D/H)", boxlayout=self.linea1, control=ComboTipoIngreso())
        chkExporta = CheckBox(texto="Exporta")
        self.linea1.addWidget(chkExporta)
        self.controles['exporta'] = chkExporta
        self.ArmaEntrada('letra', boxlayout=self.linea1)

    @inicializar_y_capturar_excepciones
    def btnAceptarClicked(self, *args, **kwargs):
        if self.tipo == 'M':
            tc = TipoComprobante.get_by_id(self.controles[TipoComprobante.codigo.column_name].text())
            # tc.codigo = self.controles['codigo'].text()
        else:
            tc = TipoComprobante()
            tc.codigo = self.controles['codigo'].text()
        tc.nombre = self.controles['nombre'].text()
        tc.exporta = self.controles['exporta'].text()
        tc.letra = self.controles['letra'].text()
        tc.lado = self.controles['lado'].text()
        tc.abreviatura = self.controles['abreviatura'].text()
        if self.tipo == 'A':
            tc.save(force_insert=True)
        else:
            print("Entra a grabar modificacion")
            tc.save()
        ABM.btnAceptarClicked(self)

