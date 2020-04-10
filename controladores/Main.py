# coding=utf-8
import os
from shutil import copyfile

import peewee
import pymysql
from PyQt5.QtCore import QPropertyAnimation, QRect
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QApplication, QMenu

from controladores.ABMCategoriasMonotributo import ABMCategoriaMonoController
from controladores.ABMGrupos import ABMGruposController
from controladores.ABMImpuestos import ABMImpuestoController
from controladores.ABMParametrosSistema import ABMParamSistController
from controladores.ABMTipoDocumentos import ABMTipoDocumentoController
from controladores.Articulos import ArticulosController
from controladores.CargaFacturasProveedor import CargaFacturaProveedorController
from controladores.CentroCostos import CentroCostoController
from controladores.Clientes import ClientesController
from controladores.Configuracion import ConfiguracionController
from controladores.ConstatacionComprobantes import ConstatacionComprobantesController
from controladores.ConsultaCAE import ConsultaCAEController
from controladores.ConsultaCtaCte import ConsultaCtaCteController
from controladores.ConsultaPadronAfip import ConsultaPadronAfipController
from controladores.ControladorBase import ControladorBase
from controladores.EmiteRecibo import EmiteReciboController
from controladores.Facturas import FacturaController
from controladores.FirmaCorreoElectronico import FirmaCorreoElectronicoController
from controladores.GeneraCertificados import GeneraCertificadosController
from controladores.IVACompras import IVAComprasController
from controladores.IVAVentas import IVAVentasController
from controladores.ImportacionAFIP import ImportaAFIPController
from controladores.InformeRecategorizacionMonotributo import InfRecMonotributoController
from controladores.InformeVentasPorGrupo import InformeVentasPorGrupoController
from controladores.Localidades import LocalidadesController
from controladores.MigracionBaseDatos import MigracionBaseDatos
from controladores.Proveedores import ProveedoresController
from controladores.RG3685Compras import RG3685ComprasController
from controladores.RG3685Ventas import RG3685VentasController
from controladores.ReImprimeFactura import ReImprimeFacturaController
from controladores.RindeCAEAIndividual import RindeCAEAIndividualController
from controladores.TipoComprobantes import TipoComprobantesController
from controladores.Resguardo import ResguardoController
from libs import Ventanas
from libs.Utiles import LeerIni, GrabarIni, FechaMysql, inicializar_y_capturar_excepciones, desencriptar
from modelos.ModeloBase import ModeloBase
from modelos.ParametrosSistema import ParamSist
from vistas.Main import MainView


class Main(ControladorBase):

    def __init__(self):
        super(Main, self).__init__()
        if LeerIni("base") == "sqlite":
            #pongo todo en un try para que en caso de que no exista aun la base de datos continue de todas formas
            try:
                copyfile("sistema.db", "sistema-res.db")
            except:
                pass
        self.view = MainView()
        self.view.initUi()
        self.conectarWidgets()
        self.model = ModeloBase()
        self.model.getDb()
        if not LeerIni("ultima_copia"):
            GrabarIni(clave='ultima_copia', key='param', valor='00000000')
        ult = LeerIni("ultima_copia")
        if LeerIni("base") == "sqlite":
            if ult < FechaMysql():
                resguardo = ResguardoController()
                resguardo.Cargar("sistema-res.db")
                resguardo.Cargar("sistema.ini")
                GrabarIni(clave='ultima_copia', key='param', valor=FechaMysql())
        self.CreaTablas()
        self.Migraciones()
        self.initUi()

    def initUi(self):
        # self.AnimacionEntrada()
        # self.EstableceTema()
        pass

    def conectarWidgets(self):
        self.view.btnSalir.clicked.connect(self.SalirSistema)
        self.view.btnClientes.clicked.connect(self.onClickBtnCliente)
        self.view.btnArticulo.clicked.connect(self.onClickBtnArticulo)
        self.view.btnFactura.clicked.connect(self.onClickBtnFactura)
        self.view.btnSeteo.clicked.connect(self.onClickBtnSeteo)
        self.view.btnAFIP.clicked.connect(self.onClickBtnAFIP)
        self.view.btnCompras.clicked.connect(self.onClickBtnCompras)

    def SalirSistema(self):
        QApplication.exit(1)

    def onClickBtnCliente(self):
        menu = QMenu(self.view)
        altaAction = menu.addAction(u"Alta, bajas y modificaciones")
        ctacteAction = menu.addAction(u"Cuenta corriente")
        localidadAction = menu.addAction(u"ABM Localidades")
        tipoCompAction = menu.addAction(u"ABM Tipo Comprobantes")
        tipoDocAction = menu.addAction(u"ABM Tipo de documentos")
        menu.addAction(u"Volver")
        action = menu.exec_(QCursor.pos())

        if action == altaAction:
            clientes = ClientesController()
            clientes.exec_()
        elif action == ctacteAction:
            consulta = ConsultaCtaCteController()
            consulta.exec_()
        elif action == localidadAction:
            localidad = LocalidadesController()
            localidad.exec_()
        elif action == tipoCompAction:
            tipocomp = TipoComprobantesController()
            tipocomp.view.exec_()
        elif action == tipoDocAction:
            tipodoc = ABMTipoDocumentoController()
            tipodoc.exec_()

    def onClickBtnArticulo(self):
        menu = QMenu(self.view)
        altaAction = menu.addAction(u"Alta, bajas y modificaciones")
        informeGrupoAction = menu.addAction(u"Informe de ventas por grupo")
        gruposAction  = menu.addAction(u"ABM Grupos de articulos")
        impuestoAction = menu.addAction(u"ABM de impuestos")
        menu.addAction(u"Volver")
        action = menu.exec_(QCursor.pos())

        if action == altaAction:
            articulos = ArticulosController()
            articulos.view.exec_()
        elif action == informeGrupoAction:
            controlador = InformeVentasPorGrupoController()
            controlador.view.exec_()
        elif action == gruposAction:
            controlador = ABMGruposController()
            controlador.exec_()
        elif action == impuestoAction:
            controlador = ABMImpuestoController()
            controlador.exec_()

    def onClickBtnFactura(self):
        menu = QMenu(self.view)
        emisionAction = menu.addAction(u"Emision de Factura")
        reimprimeAction = menu.addAction(u"Re imprime factura")
        ivaventasAction = menu.addAction(u"IVA Ventas")
        reciboAction = menu.addAction(u"Emision de recibo")
        citiAction = menu.addAction(u"RG 3685 AFIP")
        abmCategoria = menu.addAction(u"Categorias monotributo")
        infRecMono = menu.addAction(u"Informe de recategorizacion monotributo")
        menu.addAction(u"Volver")
        action = menu.exec_(QCursor.pos())

        if action == emisionAction:
            factura = FacturaController()
            factura.exec_()
        elif action == reimprimeAction:
            ventana = ReImprimeFacturaController()
            ventana.exec_()
        elif action == ivaventasAction:
            ventana = IVAVentasController()
            ventana.exec_()
        elif action == reciboAction:
            ventana = EmiteReciboController()
            ventana.exec_()
        elif action == citiAction:
            ventana = RG3685VentasController()
            ventana.exec_()
        elif action == infRecMono:
            ventana = InfRecMonotributoController()
            ventana.exec_()
        elif action == abmCategoria:
            ventana = ABMCategoriaMonoController()
            ventana.exec_()

    def onClickBtnSeteo(self):
        menu = QMenu(self.view)
        emisionConfig = menu.addAction(u"Configuracion de inicio")
        paramAction = menu.addAction(u"Parametros de sistema")
        firmaEmailAction = menu.addAction(u"Firma de correo electronico")
        generaAction = menu.addAction(u"Genera certificados digitales")
        menu.addAction(emisionConfig)
        menu.addAction(paramAction)
        menu.addAction(firmaEmailAction)
        menu.addAction(generaAction)
        menu.addAction(u"Volver")
        action = menu.exec_(QCursor.pos())
        if action == emisionConfig:
            config = ConfiguracionController()
            config.view.exec_()
        elif action == paramAction:
            _ventana = ABMParamSistController()
            _ventana.exec_()
        elif action == generaAction:
            _ventana_genera = GeneraCertificadosController()
            _ventana_genera.exec_()
        elif action == firmaEmailAction:
            _ventana_firma_email = FirmaCorreoElectronicoController()
            _ventana_firma_email.exec_()


    def onClickBtnAFIP(self):
        menu = QMenu(self.view)
        consultaAction = menu.addAction(u"Consulta de CUIT")
        constatacionAction = menu.addAction(u"Constatacion de comprobantes")
        consultaCAE = menu.addAction(u"Consulta de CAE")
        rindeCaeIndividual = menu.addAction(u"Rinde CAEA Individual")
        importa = menu.addAction(u"Importa comprobantes AFIP")
        menu.addAction(u"Volver")
        action = menu.exec_(QCursor.pos())

        if action == consultaAction:
            ventana = ConsultaPadronAfipController()
            ventana.view.exec_()
        elif action == constatacionAction:
            ventana = ConstatacionComprobantesController()
            ventana.view.exec_()
        elif action == consultaCAE:
            ventana = ConsultaCAEController()
            ventana.view.exec_()
        elif action == rindeCaeIndividual:
            ventana = RindeCAEAIndividualController()
            ventana.exec_()
        elif action == importa:
            ventana = ImportaAFIPController()
            ventana.exec_()

    def onClickBtnCompras(self):
        menu = QMenu(self.view)
        proveedoresAction = menu.addAction(u"Proveedores")
        centrocostosAction = menu.addAction(u"Centro de costos")
        facturasAction = menu.addAction(u"Carga facturas")
        ivaAction = menu.addAction(u"IVA Compras")
        rg3685 = menu.addAction(u"RG 3685 AFIP")
        menu.addAction(u"Volver")
        action = menu.exec_(QCursor.pos())

        if action == proveedoresAction:
            ventana = ProveedoresController()
            ventana.view.exec_()
        elif action == centrocostosAction:
            ventana = CentroCostoController()
            ventana.view.exec_()
        elif action == facturasAction:
            ventana = CargaFacturaProveedorController()
            ventana.view.exec_()
        elif action == ivaAction:
            ventana = IVAComprasController()
            ventana.view.exec_()
        elif action == rg3685:
            ventana = RG3685ComprasController()
            ventana.view.exec_()

    @inicializar_y_capturar_excepciones
    def CreaTablas(self, *args, **kwargs):
        if LeerIni("base") == "mysql": #en caso de que sea mysql y no este creada la base la crea
            basedatos = LeerIni("basedatos")
            user = LeerIni("usuario")
            password = desencriptar(LeerIni('password').encode(), LeerIni('key').encode())
            host = LeerIni("host")
            conn = pymysql.connect(host=host, user=user, password=password)
            conn.cursor().execute(f'CREATE DATABASE IF NOT EXISTS {basedatos}')
            conn.close()

        try:
            ParamSist.create_table(safe=True)
        except peewee.InternalError:
            Ventanas.showAlert("Sistema", "Verifique que la base de datos este creada en {}".format(
                LeerIni("host")
            ))

    def Migraciones(self):
        migracion = MigracionBaseDatos()
        migracion.Migrar()


    def AnimacionEntrada(self):
        animacion_caja = QPropertyAnimation(self.view.groupBoxBotones, b"geometry")
        animacion_caja.setDuration(1000)
        animacion_caja.setStartValue(QRect(0, self.view.lblTitulo.height(), self.view.lblTitulo.height(), 0))
        animacion_caja.setEndValue(QRect(5, 5, self.view.sizeHint().width()-5, self.view.sizeHint().height()-5))
        animacion_caja.start()
        # self.view.
        self.animacion_caja = animacion_caja

