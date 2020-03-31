# coding=utf-8
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout

from libs.Botones import Boton, BotonCerrarFormulario
from libs.EntradaTexto import EntradaTexto
from libs.Etiquetas import EtiquetaTitulo, Etiqueta
from libs.Spinner import Periodo
from vistas.VistaBase import VistaBase


class ObtieneCAEAView(VistaBase):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.setupUi(self)

    def setupUi(self, Form):
        self.setWindowTitle("Obtiene CAEA")
        layoutPpal = QVBoxLayout(Form)
        lblTitulo = EtiquetaTitulo(texto=self.windowTitle())
        layoutPpal.addWidget(lblTitulo)

        layoutLinea1 = QHBoxLayout()
        self.layoutPeriodo = Periodo(texto="Periodo")
        layoutLinea1.addLayout(self.layoutPeriodo)
        lblOrden = Etiqueta(texto="Orden")
        self.textOrden = EntradaTexto()
        layoutLinea1.addWidget(lblOrden)
        layoutLinea1.addWidget(self.textOrden)
        layoutPpal.addLayout(layoutLinea1)

        layoutBotones = QHBoxLayout()
        self.btnObtener = Boton(texto="Obtener CAEA", imagen='imagenes/if_product-sales-report_49607.png')
        self.btnCerrar = BotonCerrarFormulario()
        layoutBotones.addWidget(self.btnObtener)
        layoutBotones.addWidget(self.btnCerrar)
        layoutPpal.addLayout(layoutBotones)