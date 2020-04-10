# coding=utf-8
from PyQt5.QtWidgets import QVBoxLayout, QLineEdit, QHBoxLayout

from libs.Botones import Boton, BotonCerrarFormulario, BotonArchivo
from libs.ComboBox import ComboSINO, ComboTipoBaseDatos, ComboTipoRespIVA, ComboCopiasFE, ComboTema
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
        self.layoutCopias = self.ArmaEntrada('num_copias', texto=u'Nº de copias de factura',
                                             control=ComboCopiasFE())
        self.ArmaEntrada('cat_iva', texto='Categoria IVA (1: Resp. Inscripto, 4 Exento, 6: Monotributo)',
                         boxlayout=self.layoutCopias, control=ComboTipoRespIVA())

        self.lblTituloParametros = EtiquetaTitulo(texto='Parametros')
        self.verticalLayoutDatos.addWidget(self.lblTituloParametros)
        layoutNombreSistema = self.ArmaEntrada('nombre_sistema', texto='Nombre del sistema')
        self.ArmaEntrada('tema', texto='Tema', boxlayout=layoutNombreSistema, control=ComboTema())

        layoutBaseDatos = self.ArmaEntrada('BaseDatos', texto='Base de datos')
        self.ArmaEntrada('Host', boxlayout=layoutBaseDatos)
        layoutUsuario = self.ArmaEntrada('Usuario', texto='Usuario de base de datos')
        self.ArmaEntrada('password', boxlayout=layoutUsuario)
        self.controles['password'].setEchoMode(QLineEdit.Password)

        self.layoutHOMO = self.ArmaEntrada('HOMO', texto='Homologacion (S) Produccion (N)', control=ComboSINO())
        self.ArmaEntrada('Base', boxlayout=self.layoutHOMO, texto='Tipo base (mysql/sqlite)',
                         control=ComboTipoBaseDatos())

        layoutFCE = self.ArmaEntrada('cbufce', texto="CBU FCE")
        self.ArmaEntrada('aliasfce', boxlayout=layoutFCE, texto="Alias FCE")

        layoutCertificadoCRT = self.ArmaEntrada('crt', texto="Certificado CRT")
        self.btnArchivoCRT = BotonArchivo(archivos="CRT (*.crt)")
        self.btnArchivoCRT.widgetArchivo = self.controles['crt']
        layoutCertificadoCRT.addWidget(self.btnArchivoCRT)

        layoutCertificadoKEY = self.ArmaEntrada('key', texto="Certificado KEY")
        self.btnArchivoKEY = BotonArchivo(archivos="KEY (*.key)")
        self.btnArchivoKEY.widgetArchivo = self.controles['key']
        layoutCertificadoKEY.addWidget(self.btnArchivoKEY)

        self.layoutBotones = QHBoxLayout()
        self.btnGrabar = Boton(texto="Grabar", imagen=imagen('save.png'))
        self.btnCerrar = BotonCerrarFormulario()
        self.layoutBotones.addWidget(self.btnGrabar)
        self.layoutBotones.addWidget(self.btnCerrar)
        self.verticalLayoutDatos.addLayout(self.layoutBotones)
