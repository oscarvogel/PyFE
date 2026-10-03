from controladores.ControladorBase import ControladorBase
from libs.Utiles import (LeerIni, formato_cuit, inicializar_y_capturar_excepciones)
from libs.instalacion import cuit_emisor
from pyafipws.wsaa import WSAA
from vistas.GenerarCertificados import GeneraCertificadoView


class GeneraCertificadosController(ControladorBase):

    def __init__(self):
        super().__init__()
        self.view = GeneraCertificadoView()
        self.conectarWidgets()
        self.CargaDatos()

    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(self.view.Cerrar)
        self.view.btnGenera.clicked.connect(self.onClickBtnGenera)

    def CargaDatos(self):
        self.view.controles['cuit'].setText(formato_cuit(cuit_emisor()))
        self.view.controles['empresa'].setText(LeerIni(clave='empresa', key='FACTURA'))
        self.view.controles['nombre'].setText(LeerIni(clave='empresa', key='FACTURA'))

    @inicializar_y_capturar_excepciones
    def onClickBtnGenera(self):
        wsaa = WSAA()
        wsaa.CrearPedidoCertificado
