# coding=utf-8
from PyQt4.QtGui import QApplication, QMenu, QCursor

from controladores.Articulos import ArticulosController
from controladores.Clientes import ClientesController
from controladores.Configuracion import ConfiguracionController
from controladores.ConstatacionComprobantes import ConstatacionComprobantesController
from controladores.ConsultaCtaCte import ConsultaCtaCteController
from controladores.ConsultaPadronAfip import ConsultaPadronAfipController
from controladores.ControladorBase import ControladorBase
from controladores.EmiteRecibo import EmiteReciboController
from controladores.Facturas import FacturaController
from controladores.IVAVentas import IVAVentasController
from controladores.ReImprimeFactura import ReImprimeFacturaController
from modelos.ModeloBase import ModeloBase
from vistas.Main import MainView


class Main(ControladorBase):

    def __init__(self):
        super(Main, self).__init__()
        self.view = MainView()
        self.view.initUi()
        self.conectarWidgets()
        self.model = ModeloBase()
        self.model.getDb()

    def conectarWidgets(self):
        self.view.btnSalir.clicked.connect(self.SalirSistema)
        self.view.btnClientes.clicked.connect(self.onClickBtnCliente)
        self.view.btnArticulo.clicked.connect(self.onClickBtnArticulo)
        self.view.btnFactura.clicked.connect(self.onClickBtnFactura)
        self.view.btnSeteo.clicked.connect(self.onClickBtnSeteo)
        self.view.btnAFIP.clicked.connect(self.onClickBtnAFIP)

    def SalirSistema(self):
        QApplication.exit(1)

    def onClickBtnCliente(self):
        menu = QMenu(self.view)
        altaAction = menu.addAction(u"Alta, bajas y modificaciones")
        ctacteAction = menu.addAction(u"Cuenta corriente")
        menu.addAction(u"Volver")
        action = menu.exec_(QCursor.pos())

        if action == altaAction:
            clientes = ClientesController()
            clientes.view.exec_()
        elif action == ctacteAction:
            consulta = ConsultaCtaCteController()
            consulta.view.exec_()

    def onClickBtnArticulo(self):
        menu = QMenu(self.view)
        altaAction = menu.addAction(u"Alta, bajas y modificaciones")
        menu.addAction(u"Volver")
        action = menu.exec_(QCursor.pos())

        if action == altaAction:
            articulos = ArticulosController()
            articulos.view.exec_()

    def onClickBtnFactura(self):
        menu = QMenu(self.view)
        emisionAction = menu.addAction(u"Emision de Factura")
        reimprimeAction = menu.addAction(u"Re imprime factura")
        ivaventasAction = menu.addAction(u"IVA Ventas")
        reciboAction = menu.addAction(u"Emision de recibo")
        menu.addAction(u"Volver")
        action = menu.exec_(QCursor.pos())

        if action == emisionAction:
            factura = FacturaController()
            factura.view.exec_()
        elif action == reimprimeAction:
            ventana = ReImprimeFacturaController()
            ventana.view.exec_()
        elif action == ivaventasAction:
            ventana = IVAVentasController()
            ventana.view.exec_()
        elif action == reciboAction:
            ventana = EmiteReciboController()
            ventana.view.exec_()

    def onClickBtnSeteo(self):
        config = ConfiguracionController()
        config.view.exec_()


    def onClickBtnAFIP(self):
        menu = QMenu(self.view)
        consultaAction = menu.addAction(u"Consulta de CUIT")
        constatacionAction = menu.addAction(u"Constatacion de comprobantes")
        menu.addAction(u"Volver")
        action = menu.exec_(QCursor.pos())

        if action == consultaAction:
            ventana = ConsultaPadronAfipController()
            ventana.view.exec_()
        elif action == constatacionAction:
            ventana = ConstatacionComprobantesController()
            ventana.view.exec_()
