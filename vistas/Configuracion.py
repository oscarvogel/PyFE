# coding=utf-8
from PyQt4.QtGui import QVBoxLayout, QHBoxLayout, QLineEdit

from libs.Botones import Boton, BotonCerrarFormulario
from libs.Etiquetas import EtiquetaTitulo
from libs.Formulario import Formulario
from libs.Utiles import imagen


class ConfiguracionView(Formulario):

    def __init__(self, *args, **kwargs):
        Formulario.__init__(self, *args, **kwargs)
        self.setupUi(self)

    def setupUi(self, Form):
        self.setWindowTitle("Configuracion de sistema")
        self.verticalLayoutDatos = QVBoxLayout(Form)

        self.lblTituloEmpresa = EtiquetaTitulo(texto='Datos empresa')
        self.verticalLayoutDatos.addWidget(self.lblTituloEmpresa)
        self.ArmaEntrada('empresa')
        self.ArmaEntrada('membrete1')
        self.ArmaEntrada('membrete2')
        self.layoutCUIT = self.ArmaEntrada('cuit')
        self.ArmaEntrada('iibb', boxlayout=self.layoutCUIT)
        self.layoutCopias = self.ArmaEntrada('num_copias', texto=u'Nº de copias de factura')
        self.ArmaEntrada('cat_iva', texto='Categoria IVA (1: Resp. Inscripto, 4 Exento, 6: Monotributo)',
                         boxlayout=self.layoutCopias)

        self.lblTituloParametros = EtiquetaTitulo(texto='Parametros')
        self.verticalLayoutDatos.addWidget(self.lblTituloParametros)
        self.ArmaEntrada('nombre_sistema', texto='Nombre del sistema')
        self.ArmaEntrada('BaseDatos', texto='Base de datos')
        self.ArmaEntrada('Usuario', texto='Usuario de base de datos')
        self.ArmaEntrada('Host')
        self.layoutHOMO = self.ArmaEntrada('HOMO', texto='Homologacion (S) Produccion (N)')
        self.ArmaEntrada('Base', boxlayout=self.layoutHOMO, texto='Tipo base (mysql/sqlite)')
        self.ArmaEntrada('password')
        self.controles['password'].setEchoMode(QLineEdit.Password)

        self.layoutBotones = QHBoxLayout()
        self.btnGrabar = Boton(texto="Grabar", imagen=imagen('guardar.png'))
        self.btnCerrar = BotonCerrarFormulario()
        self.layoutBotones.addWidget(self.btnGrabar)
        self.layoutBotones.addWidget(self.btnCerrar)
        self.verticalLayoutDatos.addLayout(self.layoutBotones)
