# coding=utf-8
from libs.Etiquetas import Etiqueta
from libs.Utiles import inicializar_y_capturar_excepciones
from modelos import Tiporesp, Localidades
from modelos.Proveedores import Proveedor
from vistas.ABM import ABM


class ProveedoresView(ABM):

    LanzarExcepciones = True
    model = Proveedor()
    camposAMostrar = [Proveedor.idproveedor, Proveedor.nombre, Proveedor.cuit]
    ordenBusqueda = Proveedor.nombre
    campoClave = Proveedor.idproveedor

    def __init__(self, *args, **kwargs):
        ABM.__init__(self, *args, **kwargs)

    @inicializar_y_capturar_excepciones
    def ArmaCarga(self, *args, **kwargs):
        self.layoutID = self.ArmaEntrada('idproveedor', texto='Codigo')
        self.ArmaEntrada('nombre', boxlayout=self.layoutID)
        self.layoutDom = self.ArmaEntrada('domicilio')
        self.ArmaEntrada('telefono', boxlayout=self.layoutDom)
        self.layoutDoc = self.ArmaEntrada('cuit')
        self.ArmaEntrada('tiporesp', control=Tiporesp.Valida(), boxlayout=self.layoutDoc)
        self.lblNombreTiporesp = Etiqueta()
        self.layoutDoc.addWidget(self.lblNombreTiporesp)
        self.controles['tiporesp'].widgetNombre = self.lblNombreTiporesp
        self.ArmaEntrada('idlocalidad', boxlayout=self.layoutDoc, control=Localidades.Valida(), texto='Localidad')
        self.lblNombreLoc = Etiqueta()
        self.layoutDoc.addWidget(self.lblNombreLoc)
        self.controles['idlocalidad'].widgetNombre = self.lblNombreLoc
        self.campoFoco = self.controles['nombre']

    @inicializar_y_capturar_excepciones
    def btnAceptarClicked(self, *args, **kwargs):
        if self.tipo == 'M':
            proveedor = Proveedor.get_by_id(self.controles[Proveedor.idproveedor.column_name].text())
            proveedor.idproveedor = self.controles['idproveedor'].text()
        else:
            proveedor = Proveedor()

        proveedor.cuit = self.controles['cuit'].text()
        proveedor.nombre = self.controles['nombre'].text()
        proveedor.idlocalidad = self.controles['idlocalidad'].text()
        proveedor.tiporesp = self.controles['tiporesp'].text()
        proveedor.domicilio = self.controles['domicilio'].text()
        proveedor.telefono = self.controles['telefono'].text()

        proveedor.save()
        ABM.btnAceptarClicked(self)
