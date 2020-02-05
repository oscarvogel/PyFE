# coding=utf-8
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout

from libs.Botones import Boton, BotonCerrarFormulario
from libs.EntradaTexto import Factura, EntradaTexto
from libs.Etiquetas import EtiquetaTitulo, Etiqueta
from libs.Grillas import Grilla
from libs.Utiles import LeerIni
from modelos.Tipocomprobantes import ComboTipoComp
from vistas.VistaBase import VistaBase


class ConsultaCAEView(VistaBase):

    def __init__(self, *args, **kwargs):
        VistaBase.__init__(self, *args, **kwargs)
        self.initUi()

    def initUi(self):
        self.setWindowTitle("Consulta de CAE")
        layoutPpal = QVBoxLayout(self)
        lblTitulo = EtiquetaTitulo(texto=self.windowTitle())
        layoutPpal.addWidget(lblTitulo)

        layoutTipoComp = QHBoxLayout()
        lblTipoComp = Etiqueta(texto="Tipo de comprobante")
        self.cboTipoComp = ComboTipoComp(tiporesp=int(LeerIni(key='WSFEv1', clave='cat_iva')))
        layoutTipoComp.addWidget(lblTipoComp)
        layoutTipoComp.addWidget(self.cboTipoComp)
        self.layoutFactura = Factura(titulo=u"Nº de Comprobante")
        layoutTipoComp.addLayout(self.layoutFactura)
        layoutPpal.addLayout(layoutTipoComp)

        layoutCliente = QHBoxLayout()
        lblTipDoc = Etiqueta(texto="Tip Doc")
        self.textTipoDoc = EntradaTexto(enabled=False)
        layoutCliente.addWidget(lblTipDoc)
        layoutCliente.addWidget(self.textTipoDoc)
        lblCliente = Etiqueta(texto="Doc Cliente")
        self.textDocCli = EntradaTexto(enabled=False)
        layoutCliente.addWidget(lblCliente)
        layoutCliente.addWidget(self.textDocCli)
        lblFechComp = Etiqueta(texto="Fecha")
        self.textFecha = EntradaTexto(enabled=False)
        layoutCliente.addWidget(lblFechComp)
        layoutCliente.addWidget(self.textFecha)
        layoutPpal.addLayout(layoutCliente)

        layoutCAE = QHBoxLayout()
        lblCAE = Etiqueta(texto="CAE")
        self.textCAE = EntradaTexto()
        layoutCAE.addWidget(lblCAE)
        layoutCAE.addWidget(self.textCAE)
        lblImpTotal = Etiqueta(texto="Imp. Total")
        self.textTotal = EntradaTexto()
        lblNeto = Etiqueta(texto="Neto")
        self.textNeto = EntradaTexto()
        layoutCAE.addWidget(lblNeto)
        layoutCAE.addWidget(self.textNeto)
        layoutCAE.addWidget(lblImpTotal)
        layoutCAE.addWidget(self.textTotal)
        layoutPpal.addLayout(layoutCAE)

        layoutImp = QHBoxLayout()
        lblIVA = Etiqueta(texto='IVA')
        self.textIVA = EntradaTexto()
        layoutImp.addWidget(lblIVA)
        layoutImp.addWidget(self.textIVA)
        lblDGR = Etiqueta(texto='DGR')
        self.textDGR = EntradaTexto()
        layoutImp.addWidget(lblDGR)
        layoutImp.addWidget(self.textDGR)
        layoutPpal.addLayout(layoutImp)

        self.gridIVA = Grilla()
        self.gridIVA.enabled = True
        cabeceras = [
            'ID IVA', 'Base Imp', 'Importe'
        ]
        self.gridIVA.ArmaCabeceras(cabeceras)
        layoutPpal.addWidget(self.gridIVA)

        layoutBotones = QHBoxLayout()
        self.btnConsultar = Boton(texto="Consultar CAE", imagen="imagenes/buscar.png")
        self.btnCerrar = BotonCerrarFormulario()
        layoutBotones.addWidget(self.btnConsultar)
        layoutBotones.addWidget(self.btnCerrar)
        layoutPpal.addLayout(layoutBotones)