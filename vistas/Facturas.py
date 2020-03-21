# coding=utf-8
from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QVBoxLayout, QGridLayout, QHBoxLayout

from libs.Botones import Boton, BotonCerrarFormulario
from libs.Checkbox import CheckBox
from libs.ComboBox import FormaPago
from libs.EntradaTexto import EntradaTexto, Factura, TextEdit
from libs.Etiquetas import EtiquetaTitulo, Etiqueta
from libs.Fechas import Fecha
from libs.Formulario import Formulario
from libs.Grillas import Grilla
from libs.GroupBox import Agrupacion
from libs.Paginas import Pagina, TabPagina
from libs.Utiles import imagen, LeerIni
from modelos import Clientes, Tiporesp, Tipocomprobantes
from modelos.Clientes import Cliente


class FacturaView(Formulario):

    def __init__(self):
        Formulario.__init__(self)
        self.setupUi(self)

    def setupUi(self, Form):
        self.layoutPpal = QVBoxLayout(Form)
        self.setWindowTitle("Emision de comprobante electronico")
        self.resize(850, 650)
        self.lblTitulo = EtiquetaTitulo(texto=self.windowTitle())
        self.layoutPpal.addWidget(self.lblTitulo)
        self.layoutCliente = QGridLayout()
        self.agrupaCliente = Agrupacion(titulo="Cliente:")
        self.lblCodigoCliente = Etiqueta(texto="Codigo Cliente")
        self.lblNombreCliente = Etiqueta()
        self.validaCliente = Clientes.Valida()
        self.validaCliente.widgetNombre = self.lblNombreCliente
        self.layoutCliente.addWidget(self.lblCodigoCliente, 0, 0)
        self.layoutCliente.addWidget(self.validaCliente, 0, 1)
        self.layoutCliente.addWidget(self.lblNombreCliente, 0, 2, 1, 4)

        layoutIVA = QHBoxLayout()
        self.lblDomicilio = Etiqueta(texto="Domicilio")
        self.lineEditDomicilio = EntradaTexto(placeholderText="Domicilio cliente")
        self.layoutCliente.addWidget(self.lblDomicilio, 1, 0)
        self.layoutCliente.addWidget(self.lineEditDomicilio, 1, 1, 1, 1)

        self.lblDocumento = Etiqueta(texto=u"Nº Doc")
        self.lineEditDocumento = EntradaTexto(placeholderText="CUIT/CUIL/DNI")
        self.layoutCliente.addWidget(self.lblDocumento, 1, 2)
        self.layoutCliente.addWidget(self.lineEditDocumento, 1, 3)
        self.agrupaCliente.setLayout(self.layoutCliente)

        self.lblTipoIVA = Etiqueta(texto='IVA:')
        self.cboTipoIVA = Tiporesp.Combo()
        self.layoutCliente.addWidget(self.lblTipoIVA, 1, 4)
        self.layoutCliente.addWidget(self.cboTipoIVA, 1, 5)

        self.layoutPpal.addWidget(self.agrupaCliente)

        self.layoutComprobante = QHBoxLayout()
        self.lblComprobante = Etiqueta(texto="Comprobante", tamanio=10)
        self.cboComprobante = Tipocomprobantes.ComboTipoComp(tiporesp=int(LeerIni(clave='cat_iva', key='WSFEv1')),
                                                             tamanio=10)
        self.layoutComprobante.addWidget(self.lblComprobante)
        self.layoutComprobante.addWidget(self.cboComprobante)
        self.layoutFactura = Factura(titulo=u"Nº", tamanio=10, enabled=False)
        self.layoutComprobante.addLayout(self.layoutFactura)
        self.lblFecha = Etiqueta(texto="Fecha", tamanio=10)
        self.layoutPpal.addWidget(self.lblFecha)
        self.layoutCpbteRelacionado = Factura(titulo='Cpbte Rel', tamanio=10, enabled=False)
        self.layoutComprobante.addLayout(self.layoutCpbteRelacionado)
        self.lineEditFecha = Fecha(tamanio=10)
        self.lineEditFecha.setFecha()
        self.layoutComprobante.addWidget(self.lblFecha)
        self.layoutComprobante.addWidget(self.lineEditFecha)
        self.layoutPpal.addLayout(self.layoutComprobante)

        self.layoutConceptoPeriodo = QHBoxLayout()

        self.agrupaConceptos = Agrupacion(titulo="Conceptos a incluir")
        self.layoutConceptos = QGridLayout()
        self.checkBoxProductos = CheckBox(texto="Productos")
        self.checkBoxServicios = CheckBox(texto="Servicios")
        self.layoutConceptos.addWidget(self.checkBoxProductos, 0, 0)
        self.layoutConceptos.addWidget(self.checkBoxServicios, 0, 1)
        self.lblFormaPago = Etiqueta(texto="Forma de pago")
        self.cboFormaPago = FormaPago()
        self.layoutConceptos.addWidget(self.lblFormaPago, 1, 0)
        self.layoutConceptos.addWidget(self.cboFormaPago, 1, 1)
        self.agrupaConceptos.setLayout(self.layoutConceptos)
        self.layoutConceptoPeriodo.addWidget(self.agrupaConceptos)

        self.agrupaPeriodo = Agrupacion(titulo="Periodo Facturado")
        self.layoutPeriodo = QGridLayout()
        self.lblDesde = Etiqueta(texto="Desde", tamanio=10)
        self.lblHasta = Etiqueta(texto="Hasta", tamanio=10)
        self.fechaDesde = Fecha()
        self.fechaDesde.setFecha()
        self.fechaDesde.setEnabled(False)
        self.fechaHasta = Fecha()
        self.fechaHasta.setFecha()
        self.fechaHasta.setEnabled(False)
        self.lblVencimiento = Etiqueta(texto="Vto. para el pago")
        self.vencPago = Fecha()
        self.vencPago.setFecha()
        self.layoutPeriodo.addWidget(self.lblDesde, 0, 0)
        self.layoutPeriodo.addWidget(self.fechaDesde, 0, 1)
        self.layoutPeriodo.addWidget(self.lblHasta, 0, 2)
        self.layoutPeriodo.addWidget(self.fechaHasta, 0, 3)
        self.agrupaPeriodo.setLayout(self.layoutPeriodo)
        self.layoutPeriodo.addWidget(self.lblVencimiento, 1, 1, 1, 2)
        self.layoutPeriodo.addWidget(self.vencPago, 1, 3)
        self.layoutConceptoPeriodo.addWidget(self.agrupaPeriodo)

        self.layoutPpal.addLayout(self.layoutConceptoPeriodo)

        self.paginaDatos = Pagina()
        self.tabArticulo = TabPagina()
        self.tabAlicuotaIVA = TabPagina()
        self.tabOtrosTributos = TabPagina()
        self.tabObs = TabPagina()
        self.tabArticuloUI()
        self.tabAlicuotaIVAUI()
        self.tabOtrosTributosUI()
        self.tabObsUI()
        self.paginaDatos.addTab(self.tabArticulo, "Articulo")
        self.paginaDatos.addTab(self.tabAlicuotaIVA, "Alicuotas IVA")
        self.paginaDatos.addTab(self.tabOtrosTributos, "Otros Tributos")
        self.paginaDatos.addTab(self.tabObs, "Observaciones")
        self.layoutPpal.addWidget(self.paginaDatos)

        self.layoutTotales = QHBoxLayout()
        self.agrupaAfip = Agrupacion(titulo="Autorizacion AFIP")
        self.layoutAfip = QGridLayout()
        self.lblCAE = Etiqueta(texto="CAE")
        self.lineditCAE = EntradaTexto(placeholderText="CAE", enabled=False)
        self.lblVencCAE = Etiqueta(texto="Venc. CAE")
        self.fechaVencCAE = Fecha(enabled=False)
        self.lblResultado = Etiqueta(texto="Resultado")
        self.lineEditResultado = EntradaTexto(placeholderText="Resultado", enabled=False)
        self.layoutAfip.addWidget(self.lblCAE, 0, 0)
        self.layoutAfip.addWidget(self.lineditCAE, 0, 1)
        self.layoutAfip.addWidget(self.lblVencCAE, 1, 0)
        self.layoutAfip.addWidget(self.fechaVencCAE, 1, 1)
        self.layoutAfip.addWidget(self.lblResultado, 2, 0)
        self.layoutAfip.addWidget(self.lineEditResultado, 2, 1)
        self.agrupaAfip.setLayout(self.layoutAfip)
        self.layoutTotales.addWidget(self.agrupaAfip)

        lblSubTotal = Etiqueta(texto="Sub Total: ", tamanio=10)
        self.textSubTotal = EntradaTexto(tamanio=10, enabled=False)

        self.lblTributos = Etiqueta(texto="Otros Tributos", tamanio=10)
        self.lineEditTributos = EntradaTexto(tamanio=10, enabled=False)
        self.lblTotalIVA = Etiqueta(texto="IVA", tamanio=10)
        self.lineEditTotalIVA = EntradaTexto(tamanio=10, enabled=False)
        self.lblTotalFactura = Etiqueta(texto='Total', tamanio=10)
        self.lineEditTotal = EntradaTexto(tamanio=10, enabled=False)
        self.gridLayoutTotales = QGridLayout()
        self.gridLayoutTotales.addWidget(lblSubTotal, 0, 0)
        self.gridLayoutTotales.addWidget(self.textSubTotal, 0, 1)
        self.gridLayoutTotales.addWidget(self.lblTributos, 0, 2)
        self.gridLayoutTotales.addWidget(self.lineEditTributos, 0, 3)
        self.gridLayoutTotales.addWidget(self.lblTotalIVA, 1, 0)
        self.gridLayoutTotales.addWidget(self.lineEditTotalIVA, 1, 1, 1, 3)
        self.gridLayoutTotales.addWidget(self.lblTotalFactura, 2, 0)
        self.gridLayoutTotales.addWidget(self.lineEditTotal, 2, 1, 1, 3)

        self.layoutTotales.addLayout(self.gridLayoutTotales)
        self.layoutPpal.addLayout(self.layoutTotales)

        self.layoutBotones = QHBoxLayout()
        self.btnGrabarFactura = Boton(texto="Emitir", imagen=imagen('save.png'), autodefault=False)
        self.btnCerrarFormulario = BotonCerrarFormulario(autodefault=False)
        self.layoutBotones.addWidget(self.btnGrabarFactura)
        self.layoutBotones.addWidget(self.btnCerrarFormulario)
        self.layoutPpal.addLayout(self.layoutBotones)

    def tabArticuloUI(self):
        layoutppal = QVBoxLayout()
        self.gridFactura = Grilla(tamanio=10)
        cabeceras = [
            'Cant.','Codigo','Detalle','Unitario','IVA','SubTotal'
        ]
        self.gridFactura.ArmaCabeceras(cabeceras=cabeceras)
        self.gridFactura.enabled = True
        if int(LeerIni(clave='cat_iva', key='WSFEv1')) != 6:
            self.gridFactura.columnasHabilitadas = [
                0, 1, 2, 3, 4
            ]
        else:
            self.gridFactura.columnasHabilitadas = [
                0, 1, 2, 3
            ]

        item = [
            1, 1, '', 0, 21, 0
        ]
        self.gridFactura.AgregaItem(items=item)

        layoutppal.addWidget(self.gridFactura)
        layoutBotones = QHBoxLayout()
        self.botonAgregaArt = Boton(texto="Agrega", imagen=imagen("new.png"),
                                    tamanio=QSize(16,16), autodefault=False)
        self.botonBorrarArt = Boton(texto="Borrar", imagen=imagen("delete.png"),
                                    tamanio=QSize(16,16), autodefault=False)
        layoutBotones.addWidget(self.botonAgregaArt)
        layoutBotones.addWidget(self.botonBorrarArt)
        layoutppal.addLayout(layoutBotones)
        self.tabArticulo.setLayout(layoutppal)

    def tabAlicuotaIVAUI(self):
        layoutppal = QVBoxLayout()
        self.gridAlicuotasIVA = Grilla(tamanio=10)
        cabeceras = [
            'IVA', 'Alicuota', 'Base Imponible', 'Importe'
        ]
        self.gridAlicuotasIVA.ArmaCabeceras(cabeceras=cabeceras)
        layoutppal.addWidget(self.gridAlicuotasIVA)
        layoutBotones = QHBoxLayout()
        self.botonAgregaIVA = Boton(texto="Agrega", imagen=imagen("nuevo.png"),
                                    tamanio=QSize(16,16), autodefault=False)
        self.botonBorrarIVA = Boton(texto="Borrar", imagen=imagen("delete.png"),
                                    tamanio=QSize(16,16), autodefault=False)
        layoutBotones.addWidget(self.botonAgregaIVA)
        layoutBotones.addWidget(self.botonBorrarIVA)
        layoutppal.addLayout(layoutBotones)
        self.tabAlicuotaIVA.setLayout(layoutppal)

    def tabOtrosTributosUI(self):
        layoutppal = QVBoxLayout()
        self.gridAlicuotasTributos = Grilla(tamanio=10)
        cabeceras = [
            'Alicuota', 'Base Imponible', 'Importe'
        ]
        self.gridAlicuotasTributos.ArmaCabeceras(cabeceras=cabeceras)
        layoutppal.addWidget(self.gridAlicuotasTributos)
        layoutBotones = QHBoxLayout()
        self.botonAgregaTributos = Boton(texto="Agrega", imagen=imagen("nuevo.png"),
                                         tamanio=QSize(16,16), autodefault=False)
        self.botonBorrarTributos = Boton(texto="Borrar", imagen=imagen("delete.png"),
                                         tamanio=QSize(16,16), autodefault=False)
        layoutBotones.addWidget(self.botonAgregaTributos)
        layoutBotones.addWidget(self.botonBorrarTributos)
        layoutppal.addLayout(layoutBotones)
        self.tabOtrosTributos.setLayout(layoutppal)

    def tabObsUI(self):
        layoutppal = QVBoxLayout()
        self.editObs = TextEdit()
        layoutppal.addWidget(self.editObs)
        self.tabObs.setLayout(layoutppal)