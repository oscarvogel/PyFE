# coding=utf-8
from controladores.ControladorBase import ControladorBase
from libs import Ventanas
from libs.Utiles import LeerIni, GrabarIni, desencriptar, encriptar, inicializar_y_capturar_excepciones
from vistas.Configuracion import ConfiguracionView


class ConfiguracionController(ControladorBase):

    def __init__(self):
        super(ConfiguracionController, self).__init__()
        self.view = ConfiguracionView()
        self.conectarWidgets()
        self.CargaDatos()

    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(self.view.Cerrar)
        self.view.btnGrabar.clicked.connect(self.GrabaParametros)

    @inicializar_y_capturar_excepciones
    def CargaDatos(self, *args, **kwargs):
        self.view.controles['empresa'].setText(LeerIni(clave='empresa', key='FACTURA'))
        self.view.controles['membrete1'].setText(LeerIni(clave='membrete1', key='FACTURA'))
        self.view.controles['membrete2'].setText(LeerIni(clave='membrete2', key='FACTURA'))
        self.view.controles['cuit'].setText(LeerIni(clave='cuit', key='FACTURA'))
        self.view.controles['iibb'].setText(LeerIni(clave='iibb', key='FACTURA'))

        self.view.controles['nombre_sistema'].setText(LeerIni(clave='nombre_sistema', key='param'))
        self.view.controles['BaseDatos'].setText(LeerIni(clave='basedatos', key='param'))
        self.view.controles['Usuario'].setText(LeerIni(clave='usuario', key='param'))
        self.view.controles['Host'].setText(LeerIni(clave='host', key='param'))
        self.view.controles['HOMO'].setIndex(LeerIni(clave='homo', key='param'))
        self.view.controles['Base'].setText(LeerIni(clave='base', key='param'))
        #unicamente levanto la contraseña cuando tiene algo
        if LeerIni(clave='password', key='param'):
            self.view.controles['password'].setText(
                desencriptar(LeerIni(clave='password', key='param'), LeerIni(clave='key', key='param')))
        self.view.controles['num_copias'].setText(LeerIni(clave='num_copias', key='FACTURA'))
        self.view.controles['cat_iva'].setIndex(LeerIni(clave='cat_iva', key='WSFEv1'))
        self.view.controles['cbufce'].setText(LeerIni(clave='cbufce', key='FACTURA'))
        self.view.controles['aliasfce'].setText(LeerIni(clave='aliasfce', key='FACTURA'))
        if LeerIni('homo') == 'N':
            self.view.controles['crt'].setText(LeerIni(clave='cert_prod', key='WSAA'))
            self.view.controles['key'].setText(LeerIni(clave='privatekey_prod', key='WSAA'))
        else:
            self.view.controles['crt'].setText(LeerIni(clave='cert_homo', key='WSAA'))
            self.view.controles['key'].setText(LeerIni(clave='privatekey_homo', key='WSAA'))

    @inicializar_y_capturar_excepciones
    def GrabaParametros(self, *args, **kwargs):
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
        #si tiene una contraseña la guardo de lo contrario no
        if self.view.controles['password'].text():
            password, key = encriptar(bytes(self.view.controles['password'].text(), encoding='utf8'))
            GrabarIni(clave='password', key='param', valor=password.decode('utf-8'))
            GrabarIni(clave='key', key='param', valor=key.decode('utf-8'))
        GrabarIni(clave='cat_iva', key='WSFEv1', valor=self.view.controles['cat_iva'].text())
        GrabarIni(clave='cbufce', key='FACTURA', valor=self.view.controles['cbufce'].text())
        GrabarIni(clave='aliasfce', key='FACTURA', valor=self.view.controles['aliasfce'].text())
        if LeerIni('homo') == 'N':
            GrabarIni(clave='cert_prod', key='WSAA', valor=self.view.controles['crt'].text())
            GrabarIni(clave='privatekey_prod', key='WSAA', valor=self.view.controles['key'].text())
        else:
            GrabarIni(clave='cert_homo', key='WSAA', valor=self.view.controles['crt'].text())
            GrabarIni(clave='privatekey_homo', key='WSAA', valor=self.view.controles['key'].text())

        Ventanas.showAlert(LeerIni('nombre_sistema'), 'Configuracion guardada con exito')
