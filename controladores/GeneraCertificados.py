from controladores.ControladorBase import ControladorBase
from vistas.GenerarCertificados import GeneraCertificadoView


class GeneraCertificadosController(ControladorBase):

    def __init__(self):
        super().__init__()
        self.view = GeneraCertificadoView()
        self.conectarWidgets()

    def conectarWidgets(self):
        pass