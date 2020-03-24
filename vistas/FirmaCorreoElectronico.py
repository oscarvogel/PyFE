from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout

from libs.Botones import Boton, BotonCerrarFormulario
from libs.EntradaTexto import TextoEnriquecido
from libs.Utiles import imagen
from vistas.VistaBase import VistaBase


class FirmaCorreoElectronicoView(VistaBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

    def setupUi(self, Form):
        self.setWindowTitle("Firma de correo electronico")
        layoutPpal = QVBoxLayout(Form)

        self.editorFirma = TextoEnriquecido()
        layoutPpal.addWidget(self.editorFirma)

        layoutBotones = QHBoxLayout()
        self.btnCargar = Boton(texto="Cargar", imagen=imagen("load_html_file.png"))
        self.btnGrabar = Boton(texto="Grabar", imagen=imagen("save.png"))
        self.btnCerrar = BotonCerrarFormulario()
        layoutBotones.addWidget(self.btnCargar)
        layoutBotones.addWidget(self.btnGrabar)
        layoutBotones.addWidget(self.btnCerrar)
        layoutPpal.addLayout(layoutBotones)


