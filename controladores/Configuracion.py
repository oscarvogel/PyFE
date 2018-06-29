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
        self.view.controles['empresa'].setText(LeerIni(clave='empresa', key='FACTURA'))
        self.view.controles['membrete1'].setText(LeerIni(clave='membrete1', key='FACTURA'))
        self.view.controles['membrete2'].setText(LeerIni(clave='membrete2', key='FACTURA'))
        self.view.controles['cuit'].setText(LeerIni(clave='cuit', key='FACTURA'))
        self.view.controles['iibb'].setText(LeerIni(clave='iibb', key='FACTURA'))

        self.view.controles['nombre_sistema'].setText(LeerIni(clave='nombre_sistema', key='param'))
        self.view.controles['BaseDatos'].setText(LeerIni(clave='basedatos', key='param'))
        self.view.controles['Usuario'].setText(LeerIni(clave='usuario', key='param'))
        self.view.controles['Host'].setText(LeerIni(clave='host', key='param'))
        self.view.controles['HOMO'].setText(LeerIni(clave='homo', key='param'))
        self.view.controles['Base'].setText(LeerIni(clave='base', key='param'))
        self.view.controles['password'].setText(
            desencriptar(LeerIni(clave='password', key='param'), LeerIni(clave='key', key='param')))
        self.view.controles['num_copias'].setText(LeerIni(clave='num_copias', key='FACTURA'))
        self.view.controles['cat_iva'].setText(LeerIni(clave='cat_iva', key='WSFEv1'))

    def GrabaParametros(self):
        GrabarIni(clave='EMPRESA', key='FACTURA', valor=self.view.controles['empresa'].text())
        GrabarIni(clave='MEMBRETE1', key='FACTURA', valor=self.view.controles['membrete1'].text())
        GrabarIni(clave='MEMBRETE2', key='FACTURA', valor=self.view.controles['membrete2'].text())
        GrabarIni(clave='CUIT', key='FACTURA', valor=self.view.controles['cuit'].text())
        GrabarIni(clave='IIBB', key='FACTURA', valor=self.view.controles['iibb'].text())
        GrabarIni(clave='num_copias', key='FACTURA', valor=self.view.controles['num_copias'].text())

        GrabarIni(clave='nombre_sistema', key='param', valor=self.view.controles['nombre_sistema'].text())
        GrabarIni(clave='BaseDatos', key='param', valor=self.view.controles['BaseDatos'].text())
        GrabarIni(clave='Usuario', key='param', valor=self.view.controles['Usuario'].text())
        GrabarIni(clave='Host', key='param', valor=self.view.controles['Host'].text())
        GrabarIni(clave='HOMO', key='param', valor=self.view.controles['HOMO'].text())
        GrabarIni(clave='Base', key='param', valor=self.view.controles['Base'].text())
        password, key = encriptar(bytes(self.view.controles['password'].text()))
        GrabarIni(clave='password', key='param', valor=password)
        GrabarIni(clave='key', key='param', valor=key)
        GrabarIni(clave='cat_iva', key='WSFEv1', valor=self.view.controles['cat_iva'].text())
