# coding=utf-8
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout

from libs.Botones import BotonArchivo, BotonCerrarFormulario, Boton
from libs.Utiles import imagen
from vistas.VistaBase import VistaBase


class GeneraCertificadoView(VistaBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

    def setupUi(self, Form):
        self.setWindowTitle("Genera certificado digital")
        self.verticalLayoutDatos = QVBoxLayout(Form)

        self.ArmaEntrada(nombre='cuit')
        self.ArmaEntrada(nombre='empresa')
        self.ArmaEntrada(nombre='nombre')
        layoutArchivo = self.ArmaEntrada(nombre='archivo')
        self.btnArchivo = BotonArchivo(archivos="CSR (*.csr)")
        self.btnArchivo.directorio = "certificados"
        self.btnArchivo.nombre_archivo = "certificado"
        self.btnArchivo.guardar = True
        self.btnArchivo.widgetArchivo = self.controles['archivo']
        layoutArchivo.addWidget(self.btnArchivo)

        layoutBotones = QHBoxLayout()
        self.btnGenera = Boton(texto="Genera", imagen=imagen("Accept.png"))
        self.btnCerrar = BotonCerrarFormulario()
        layoutBotones.addWidget(self.btnGenera)
        layoutBotones.addWidget(self.btnCerrar)
        self.verticalLayoutDatos.addLayout(layoutBotones)
