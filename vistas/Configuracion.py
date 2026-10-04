# coding=utf-8
from PyQt5.QtWidgets import QVBoxLayout, QLineEdit, QHBoxLayout

from libs.Botones import Boton, BotonCerrarFormulario, BotonArchivo
from libs.ComboBox import ComboSINO, ComboTipoBaseDatos, ComboTipoRespIVA, ComboCopiasFE
from libs.Etiquetas import EtiquetaTitulo
from libs.Formulario import Formulario
from libs.Utiles import imagen, icono


class ConfiguracionView(Formulario):

    def __init__(self, *args, **kwargs):
        Formulario.__init__(self, *args, **kwargs)
        self.setupUi(self)

    def setupUi(self, Form):
        self.setWindowTitle("Configuración de sistema")
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
        # El texto ya no dice '(1: Resp. Inscripto, 4 Exento, 6: Monotributo)'
        # porque el combo trae los diez codigos de ARCA, no tres.
        self.ArmaEntrada('cat_iva', texto='Categoria de IVA de la empresa',
                         boxlayout=self.layoutCopias, control=ComboTipoRespIVA())
        # Punto de venta e inicio de actividades los pide el asistente de
        # primer arranque, pero antes no se podian corregir desde aca: habia
        # que editar el .ini a mano.
        self.layoutEmision = self.ArmaEntrada('pto_vta', texto='Punto de venta')
        self.ArmaEntrada('inicio', texto='Inicio de actividades',
                         boxlayout=self.layoutEmision)

        self.lblTituloParametros = EtiquetaTitulo(texto='Parametros')
        self.verticalLayoutDatos.addWidget(self.lblTituloParametros)
        self.ArmaEntrada('nombre_sistema', texto='Nombre del sistema')
        # El selector de tema se saco. Ofrecia 7 archivos .css que nunca se
        # llegaban a aplicar (no habia codigo que los cargara), asi que un
        # usuario que elegia "dark" no pasaba nada y se pensaba que la app
        # estaba rota. Ahora hay un solo tema, pyfe.css, que se aplica solo al
        # arrancar. Ver libs/tema.py.

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
        self.btnGrabar = Boton(texto="Grabar", imagen=icono('guardar'), estilo='primario')
        self.btnCerrar = BotonCerrarFormulario()
        self.layoutBotones.addWidget(self.btnGrabar)
        self.layoutBotones.addWidget(self.btnCerrar)
        self.verticalLayoutDatos.addLayout(self.layoutBotones)
