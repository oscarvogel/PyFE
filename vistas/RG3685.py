# coding=utf-8
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout

from libs.BarraProgreso import Avance
from libs.Botones import Boton, BotonCerrarFormulario
from libs.Etiquetas import EtiquetaTitulo
from libs.Formulario import Formulario
from libs.Spinner import Periodo


class RG3685View(Formulario):

    def __init__(self, *args, **kwargs):
        Formulario.__init__(self, *args, **kwargs)
        self.setupUi(self)

    def setupUi(self, Form):
        self.setWindowTitle("RG 3685 Afip - Ventas")
        self.resize(650, 100)
        layoutPpal = QVBoxLayout(Form)
        lblTitulo = EtiquetaTitulo(texto=self.windowTitle())
        layoutPpal.addWidget(lblTitulo)

        self.periodo = Periodo(texto="Periodo a procesar")
        layoutPpal.addLayout(self.periodo)

        self.avance = Avance()
        layoutPpal.addWidget(self.avance)

        layoutBotones = QHBoxLayout()
        self.btnProcesar = Boton(texto="Procesar", imagen='imagenes/accept.png')
        self.btnCerrar = BotonCerrarFormulario()
        layoutBotones.addWidget(self.btnProcesar)
        layoutBotones.addWidget(self.btnCerrar)
        layoutPpal.addLayout(layoutBotones)
