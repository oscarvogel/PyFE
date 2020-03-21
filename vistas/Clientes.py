# coding=utf-8
from PyQt5.QtCore import QSize

from libs import Ventanas
from libs.Botones import Boton
from libs.Etiquetas import Etiqueta
from libs.Utiles import inicializar_y_capturar_excepciones, imagen
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
        self.layoutDocumento = self.ArmaEntrada(nombre='tipodocu', control=Tipodoc.ComboTipoDoc(),
                                                texto="Tipo de docuemnto")
        self.lblNombreTipodoc = Etiqueta()
        self.layoutDocumento.addWidget(self.lblNombreTipodoc)
        self.controles['tipodocu'].widgetNombre = self.lblNombreTipodoc
        self.ArmaEntrada(nombre='dni', boxlayout=self.layoutDocumento)
        self.ArmaEntrada(nombre='cuit', boxlayout=self.layoutDocumento)
        self.layoutImpuesto = self.ArmaEntrada(nombre='percepcion', control=Impuestos.ComboImpuesto(),
                                               texto="Tipo de impuesto")
        self.lblNombreImpuesto = Etiqueta()
        self.layoutImpuesto.addWidget(self.lblNombreImpuesto)
        self.controles['percepcion'].widgetNombre = self.lblNombreImpuesto
        self.campoFoco = self.controles['nombre']

        self.ArmaEntrada(nombre='tiporesp', boxlayout=self.layoutImpuesto, control=Tiporesp.Combo(),
                         texto="Responsabilidad frente al iva")
        self.lblNombreTiporesp = Etiqueta()
        self.layoutDocumento.addWidget(self.lblNombreTiporesp)
        self.controles['tiporesp'].widgetNombre = self.lblNombreTiporesp

    @inicializar_y_capturar_excepciones
    def btnAceptarClicked(self, *args, **kwargs):
        if self.tipo == 'M':
            cliente = Cliente.get_by_id(self.controles[Cliente.idcliente.column_name].text())
            cliente.idcliente = self.controles['idcliente'].text()
        else:
            if self.controles['dni'].text() != '0':
                doc = Cliente.select().where(
                    Cliente.dni == self.controles['dni'].text()
                )
            else:
                doc = Cliente.select().where(
                    Cliente.cuit == self.controles['cuit'].text() or '0'
                )
            if doc.count() > 0:
                Ventanas.showAlert("Sistema", "Cliente con el numero documento de documento cargado, ya dado de alta")
                return
            cliente = Cliente()
        cliente.nombre = self.controles['nombre'].text()
        cliente.telefono = self.controles['telefono'].text()
        cliente.localidad = self.controles['localidad'].text() or 1
        cliente.domicilio = self.controles['domicilio'].text()
        cliente.tipodocu = self.controles['tipodocu'].text() or 0
        cliente.dni = self.controles['dni'].text() if self.controles['dni'].text() else '0'
        cliente.cuit = self.controles['cuit'].text() if str(self.controles['cuit'].text()).replace('-', '') else '0'
        cliente.tiporesp = self.controles['tiporesp'].text() or 3
        cliente.formapago = '1'
        cliente.percepcion = self.controles['percepcion'].text() or 1
        #if self.tipo == 'M': #actualizacion
        cliente.save()
        ABM.btnAceptarClicked(self)

    def BotonesAdicionales(self):
        self.btnEmail = Boton(self.tabLista, texto="Email Cliente", imagen=imagen("email.png"), tamanio=QSize(32,32),
                                tooltip='Agrega email del cliente')
        self.btnEmail.setObjectName("btnEmail")
        self.horizontalLayout.addWidget(self.btnEmail)

