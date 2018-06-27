# coding=utf-8
from controladores.ControladorBase import ControladorBase
from libs import Ventanas
from libs.Utiles import LeerIni, GrabarIni, desencriptar, encriptar
from vistas.Configuracion import ConfiguracionView


class ConfiguracionController(ControladorBase):

    def __init__(self):
        super(ConfiguracionController, self).__init__()
        self.view = ConfiguracionView()
        self.conectarWidgets()
        self.CargaDatos()

    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(self.view.Cerrar)
        self.view.btnCerrar.clicked.connect(self.GrabaParametros)

    def CargaDatos(self):
        self.view.controles['empresa'].setText(LeerIni(clave='EMPRESA', key='FACTURA'))
        self.view.controles['membrete1'].setText(LeerIni(clave='MEMBRETE1', key='FACTURA'))
        self.view.controles['membrete2'].setText(LeerIni(clave='MEMBRETE2', key='FACTURA'))
        self.view.controles['cuit'].setText(LeerIni(clave='CUIT', key='FACTURA'))
        self.view.controles['iibb'].setText(LeerIni(clave='IIBB', key='FACTURA'))

        self.view.controles['nombre_sistema'].setText(LeerIni(clave='nombre_sistema', key='param'))
        self.view.controles['BaseDatos'].setText(LeerIni(clave='BaseDatos', key='param'))
        self.view.controles['Usuario'].setText(LeerIni(clave='Usuario', key='param'))
        self.view.controles['Host'].setText(LeerIni(clave='Host', key='param'))
        self.view.controles['HOMO'].setText(LeerIni(clave='HOMO', key='param'))
        self.view.controles['Base'].setText(LeerIni(clave='Base', key='param'))
        self.view.controles['password'].setText(
            desencriptar(LeerIni(clave='password', key='param'), LeerIni(clave='key', key='param')))

    def GrabaParametros(self):
        GrabarIni(clave='EMPRESA', key='FACTURA', valor=self.view.controles['empresa'].text())
        GrabarIni(clave='MEMBRETE1', key='FACTURA', valor=self.view.controles['membrete1'].text())
        GrabarIni(clave='MEMBRETE2', key='FACTURA', valor=self.view.controles['membrete2'].text())
        GrabarIni(clave='CUIT', key='FACTURA', valor=self.view.controles['cuit'].text())
        GrabarIni(clave='IIBB', key='FACTURA', valor=self.view.controles['iibb'].text())

        GrabarIni(clave='nombre_sistema', key='param', valor=self.view.controles['nombre_sistema'].text())
        GrabarIni(clave='BaseDatos', key='param', valor=self.view.controles['BaseDatos'].text())
        GrabarIni(clave='Usuario', key='param', valor=self.view.controles['Usuario'].text())
        GrabarIni(clave='Host', key='param', valor=self.view.controles['Host'].text())
        GrabarIni(clave='HOMO', key='param', valor=self.view.controles['HOMO'].text())
        GrabarIni(clave='Base', key='param', valor=self.view.controles['Base'].text())
        key, password = encriptar(bytes(self.view.controles['password'].text()))
        GrabarIni(clave='password', key='param', valor=password)
        GrabarIni(clave='key', key='param', valor=key)
