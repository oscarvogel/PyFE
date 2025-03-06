# coding=utf-8
from gc import enable
from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QFormLayout

from libs import Ventanas
from libs.Botones import Boton
from libs.EntradaTexto import TextEdit
from libs.Etiquetas import Etiqueta, EtiquetaTitulo
from libs.Fechas import Fecha, RangoFechas
from libs.Grillas import Grilla
from libs.Spinner import Spinner
from libs.Utiles import inicializar_y_capturar_excepciones, imagen
from modelos import Localidades, Tipodoc, Tiporesp, Impuestos
from modelos.Clientes import Cliente, Valida
from vistas.ABM import ABM
from vistas.VistaBase import VistaBase


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

        self.btn_ficha = Boton(self.tabLista, texto="Ficha", imagen=imagen("document-copy.png"), tamanio=QSize(32,32),
                                tooltip='Ficha del cliente')
        self.btn_ficha.setObjectName("btn_ficha")
        self.horizontalLayout.addWidget(self.btnEmail)
        self.horizontalLayout.addWidget(self.btn_ficha)

class ListaFichaClienteView(VistaBase):

    def __init__(self, *args, **kwargs):
        VistaBase.__init__(self, *args, **kwargs)
        self.initUi()

    def initUi(self):
        self.setWindowTitle("Ficha de cliente")
        self.resize(750, 450)
        layoutPpal = QVBoxLayout(self)
        lblTitulo = EtiquetaTitulo(texto=self.windowTitle())
        layoutPpal.addWidget(lblTitulo)

        self.layout_fechas = RangoFechas()
        self.layout_fechas.desde_fecha.setFecha(fecha=-30)
        layoutPpal.addLayout(self.layout_fechas)

        self.grid_datos = Grilla(enabled=True)
        self.grid_datos.ArmaCabeceras(
            cabeceras=["Fecha", "Detalle", "Debe", "Haber", "Saldo", 'id']
        )
        layoutPpal.addWidget(self.grid_datos)

        layout_botones = QHBoxLayout()
        self.btn_cargar = Boton(texto="Cargar", imagen=imagen("if_product-sales-report_49607.png"))
        self.btn_agregar = Boton(texto="Agregar", imagen=imagen("new.png"))
        self.btn_editar = Boton(texto="Editar", imagen=imagen("edit.png"))
        self.btn_borrar = Boton(texto="Borrar", imagen=imagen("delete.png"))
        self.btn_impresion = Boton(texto="Imprimir", imagen=imagen("print.png"))
        self.btn_cerrar = Boton(texto="Cerrar", imagen=imagen("close.png"))
        layout_botones.addWidget(self.btn_cargar)
        layout_botones.addWidget(self.btn_agregar)
        layout_botones.addWidget(self.btn_editar)
        layout_botones.addWidget(self.btn_borrar)
        layout_botones.addWidget(self.btn_impresion)
        layout_botones.addWidget(self.btn_cerrar)
        layoutPpal.addLayout(layout_botones)
        
class FichaClienteView(VistaBase):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initUi()
        
    def initUi(self):
        self.setWindowTitle("Ficha de cliente")
        self.resize(500, 350)
        layoutPpal = QVBoxLayout(self)
        lblTitulo = EtiquetaTitulo(texto=self.windowTitle())
        layoutPpal.addWidget(lblTitulo)
        
        layoutDatos = QFormLayout()
        lblCliente = Etiqueta(texto="Cliente")
        self.txtCliente = Valida(enabled=False)
        layoutDatos.addRow(lblCliente, self.txtCliente)
        
        lblFecha = Etiqueta(texto="Fecha")
        self.fecha = Fecha()
        layoutDatos.addRow(lblFecha, self.fecha)
        
        lblDetalle = Etiqueta(texto="Detalle")
        self.txtDetalle = TextEdit()
        layoutDatos.addRow(lblDetalle, self.txtDetalle)
        
        lblDebe = Etiqueta(texto="Debe")
        self.txtDebe = Spinner(decimales=2)
        layoutDatos.addRow(lblDebe, self.txtDebe)
        
        lblHaber = Etiqueta(texto="Haber")
        self.txtHaber = Spinner(decimales=2)
        layoutDatos.addRow(lblHaber, self.txtHaber)
        
        layoutPpal.addLayout(layoutDatos)
        
        layout_botones = QHBoxLayout()
        self.btn_guardar = Boton(texto="Guardar", imagen=imagen("save.png"))
        self.btn_cerrar = Boton(texto="Cerrar", imagen=imagen("close.png"))
        layout_botones.addWidget(self.btn_guardar)
        layout_botones.addWidget(self.btn_cerrar)
        layoutPpal.addLayout(layout_botones)
        