# coding=utf-8
from PyQt5.QtWidgets import QVBoxLayout, QFormLayout, QHBoxLayout

from libs.Botones import Boton, BotonCerrarFormulario
from libs.ComboBox import ComboConstComp
from libs.EntradaTexto import EntradaTexto, CUIT, Factura
from libs.Etiquetas import EtiquetaTitulo, Etiqueta
from libs.Fechas import Fecha
from libs.Utiles import imagen, LeerIni
from modelos import Tipocomprobantes, Tipodoc
from vistas.VistaBase import VistaBase


class ConstatacionComprobanteView(VistaBase):

    def __init__(self, *args, **kwargs):
        VistaBase.__init__(self, *args, **kwargs)
        self.setupUi(self)

    def setupUi(self, Form):
        self.setWindowTitle("Constatacion de comprobantes")

        self.layoutPpal = QVBoxLayout(Form)
        self.lblTitulo = EtiquetaTitulo(texto=self.windowTitle())
        self.layoutPpal.addWidget(self.lblTitulo)
        self.formLayout = QFormLayout()

        self.lblComboTipo = Etiqueta(texto="Tipo de constatacion")
        self.cboComboTipo = ComboConstComp()
        self.formLayout.addRow(self.lblComboTipo, self.cboComboTipo)
        self.layoutPpal.addLayout(self.formLayout)

        self.lblCuit = Etiqueta(texto="CUIT")
        self.textCuit = CUIT(placeholderText="CUIT")
        self.formLayout.addRow(self.lblCuit, self.textCuit)

        self.lblCae = Etiqueta(texto="CAE/CAI")
        self.textCae = EntradaTexto(placeholderText="CAE/CAI")
        self.formLayout.addRow(self.lblCae, self.textCae)

        self.lblFechaEm = Etiqueta(texto="Fecha de emision")
        self.textFecha = Fecha()
        self.textFecha.setFecha()
        self.formLayout.addRow(self.lblFechaEm, self.textFecha)

        self.lblTipoComp = Etiqueta(texto="Tipo de comprobante")
        self.layoutTipoComp = QHBoxLayout()
        self.textTipoComp = Tipocomprobantes.Valida()
        self.lblNombreComp = Etiqueta()
        self.textTipoComp.widgetNombre = self.lblNombreComp
        self.layoutTipoComp.addWidget(self.textTipoComp)
        self.layoutTipoComp.addWidget(self.lblNombreComp)
        self.formLayout.addRow(self.lblTipoComp, self.layoutTipoComp)

        self.lblFactura = Etiqueta(texto=u"Nº Factura")
        self.textFactura = Factura(titulo="")
        self.formLayout.addRow(self.lblFactura, self.textFactura)

        self.lblImpTotal = Etiqueta(texto="Importe total")
        self.textImpTotal = EntradaTexto(placeholderText="Importe Total")
        self.formLayout.addRow(self.lblImpTotal, self.textImpTotal)

        self.lblTipoDocReceptor = Etiqueta(texto="Tipo Doc. Receptor")
        self.textTipoDocReceptor = Tipodoc.Valida()
        self.textTipoDocReceptor.setText('80')
        self.formLayout.addRow(self.lblTipoDocReceptor, self.textTipoDocReceptor)

        self.lblNroDoc = Etiqueta(texto="Nro Doc. Receptor")
        self.textNroDoc = EntradaTexto(placeholderText="Nro Doc. Receptor")
        self.textNroDoc.setText(LeerIni(clave='cuit', key='WSCDC'))
        self.formLayout.addRow(self.lblNroDoc, self.textNroDoc)

        self.lblResultado = Etiqueta()
        self.layoutPpal.addWidget(self.lblResultado)

        self.layoutBotones = QHBoxLayout()
        self.btnConsultar = Boton(texto="Consultar", imagen=imagen('if_SEO_usability_audit_search__969250.png'))
        self.btnImprimir = Boton(texto="Imprimir", imagen=imagen("print.png"))
        self.btnImprimir.setEnabled(False)
        self.btnCerrar = BotonCerrarFormulario()
        self.layoutBotones.addWidget(self.btnConsultar)
        self.layoutBotones.addWidget(self.btnImprimir)
        self.layoutBotones.addWidget(self.btnCerrar)
        self.layoutPpal.addLayout(self.layoutBotones)

        self.cboComboTipo.setFocus()
