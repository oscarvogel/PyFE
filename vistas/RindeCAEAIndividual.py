# coding=utf-8
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout

from libs.Botones import Boton, BotonCerrarFormulario
from libs.EntradaTexto import Factura
from libs.Etiquetas import EtiquetaTitulo, Etiqueta
from libs.Utiles import LeerIni, imagen, icono, a_entero
from modelos.Tipocomprobantes import ComboTipoComp
from vistas.VistaBase import VistaBase


class RindeCAEAIndividualView(VistaBase):

    def __init__(self, *args, **kwargs):
        VistaBase.__init__(self, *args, **kwargs)
        self.initUi()

    def initUi(self):
        self.setWindowTitle("Rinde CAEA Individual")
        layoutPpal = QVBoxLayout(self)
        lblTitulo = EtiquetaTitulo(texto=self.windowTitle())
        layoutPpal.addWidget(lblTitulo)

        layoutTipoComp = QHBoxLayout()
        lblTipoComp = Etiqueta(texto="Tipo de comprobante")
        self.cboTipoComp = ComboTipoComp(tiporesp=a_entero(LeerIni(key='WSFEv1', clave='cat_iva'), 1))
        layoutTipoComp.addWidget(lblTipoComp)
        layoutTipoComp.addWidget(self.cboTipoComp)
        self.layoutFactura = Factura(titulo=u"Nº de Comprobante")
        layoutTipoComp.addLayout(self.layoutFactura)
        layoutPpal.addLayout(layoutTipoComp)

        layoutBotones = QHBoxLayout()
        self.btnConsultar = Boton(texto="Rinde CAEA", imagen=icono('check'))
        self.btnCerrar = BotonCerrarFormulario()
        layoutBotones.addWidget(self.btnConsultar)
        layoutBotones.addWidget(self.btnCerrar)
        layoutPpal.addLayout(layoutBotones)