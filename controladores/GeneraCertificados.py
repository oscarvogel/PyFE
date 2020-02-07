from controladores.ControladorBase import ControladorBase
from libs.Utiles import LeerIni
from vistas.GenerarCertificados import GeneraCertificadoView


class GeneraCertificadosController(ControladorBase):

    def __init__(self):
        super().__init__()
        self.view = GeneraCertificadoView()
        self.conectarWidgets()
        self.CargaDatos()

    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(self.view.Cerrar)

    def CargaDatos(self):
        self.view.controles['cuit'].setText(LeerIni(clave='cuit', key='WSFEv1'))
        self.view.controles['empresa'].setText(LeerIni(clave='empresa', key='FACTURA'))
        self.view.controles['nombre'].setText(LeerIni(clave='empresa', key='FACTURA'))