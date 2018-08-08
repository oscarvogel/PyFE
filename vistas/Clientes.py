# coding=utf-8
from PyQt4.QtCore import QSize

from libs.Botones import Boton
from libs.Etiquetas import Etiqueta
from libs.Utiles import inicializar_y_capturar_excepciones
from modelos import Localidades, Tipodoc, Tiporesp, Impuestos
from modelos.Clientes import Cliente
from vistas.ABM import ABM


class ClientesView(ABM):

    model = Cliente()
    camposAMostrar = [Cliente.idcliente, Cliente.nombre]
    ordenBusqueda = Cliente.nombre
    campoClave = Cliente.idcliente

    def __init__(self, *args, **kwargs):
        ABM.__init__(self, *args, **kwargs)

    @inicializar_y_capturar_excepciones
    def ArmaCarga(self, *args, **kwargs):
        self.layoutID = self.ArmaEntrada('idcliente', texto='Codigo')
        self.ArmaEntrada('nombre', boxlayout=self.layoutID)
        self.layoutDomi = self.ArmaEntrada('domicilio')
        self.ArmaEntrada('telefono', boxlayout=self.layoutDomi)
        self.layoutLocalidad = self.ArmaEntrada(nombre='localidad', control=Localidades.Valida())
        self.lblNombreLocalidad = Etiqueta()
        self.layoutLocalidad.addWidget(self.lblNombreLocalidad)
        self.controles['localidad'].widgetNombre = self.lblNombreLocalidad
        self.layoutDocumento = self.ArmaEntrada(nombre='tipodocu', control=Tipodoc.Valida())
        self.lblNombreTipodoc = Etiqueta()
        self.layoutDocumento.addWidget(self.lblNombreTipodoc)
        self.controles['tipodocu'].widgetNombre = self.lblNombreTipodoc
        self.ArmaEntrada(nombre='dni', boxlayout=self.layoutDocumento)
        self.ArmaEntrada(nombre='cuit', boxlayout=self.layoutDocumento)
        self.ArmaEntrada(nombre='tiporesp', boxlayout=self.layoutDocumento, control=Tiporesp.Valida())
        self.lblNombreTiporesp = Etiqueta()
        self.layoutDocumento.addWidget(self.lblNombreTiporesp)
        self.controles['tiporesp'].widgetNombre = self.lblNombreTiporesp
        self.layoutImpuesto = self.ArmaEntrada(nombre='percepcion', control=Impuestos.Valida())
        self.lblNombreImpuesto = Etiqueta()
        self.layoutImpuesto.addWidget(self.lblNombreImpuesto)
        self.controles['percepcion'].widgetNombre = self.lblNombreImpuesto
        self.campoFoco = self.controles['nombre']

    @inicializar_y_capturar_excepciones
    def btnAceptarClicked(self, *args, **kwargs):
        if self.tipo == 'M':
            cliente = Cliente.get_by_id(self.controles[Cliente.idcliente.column_name].text())
            cliente.idcliente = self.controles['idcliente'].text()
        else:
            cliente = Cliente()
        cliente.nombre = self.controles['nombre'].text()
        cliente.telefono = self.controles['telefono'].text()
        cliente.localidad = self.controles['localidad'].text()
        cliente.domicilio = self.controles['domicilio'].text()
        cliente.tipodocu = self.controles['tipodocu'].text()
        cliente.dni = self.controles['dni'].text() if self.controles['dni'].text() else '0'
        cliente.cuit = self.controles['cuit'].text() if self.controles['cuit'].text() else '0'
        cliente.tiporesp = self.controles['tiporesp'].text()
        cliente.formapago = '1'
        cliente.percepcion = self.controles['percepcion'].text()
        #if self.tipo == 'M': #actualizacion
        cliente.save()
        ABM.btnAceptarClicked(self)

    def BotonesAdicionales(self):
        self.btnEmail = Boton(self.tabLista, imagen="imagenes/email.png", tamanio=QSize(32,32),
                                tooltip='Agrega email del cliente')
        self.btnEmail.setObjectName("btnEmail")
        self.horizontalLayout.addWidget(self.btnEmail)

