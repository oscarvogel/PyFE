from controladores.ControladorBase import ControladorBase
from libs import Ventanas
from libs.Utiles import envia_correo, imagen
from modelos.Emailcliente import EmailCliente
from modelos.ParametrosSistema import ParamSist
from vistas.EnvioEmail import EnvioEmailView


class EnvioEmailController(ControladorBase):

    #parametros excluyentes no se puede setear ambos, porque toma de tablas distintas
    cliente = None #indica el cliente al cual se quiere enviar un correo
    proveedor = None #indica el proveedor al cual se quiere enviar un correo
    archivo_firma = '' #archivo con la firma del usuario

    def __init__(self):
        super().__init__()
        self.__adjuntos = []  # lista con los archivos adjuntos a enviar
        self.view = EnvioEmailView()
        self.conectarWidgets()
        self.cargaParametros()

    def conectarWidgets(self):
        # self.view.textPara.cargaDatos()
        self.view.btnCerrar.clicked.connect(self.view.Cerrar)
        self.view.btnEnviar.clicked.connect(self.onClickBtnEnviar)

    def onClickBtnEnviar(self):
        ok, err_msg = envia_correo(
            from_address=self.usuario, to_address=self.view.textPara.text(),
            message=self.view.textMensaje.toHtml(), subject=self.view.textAsunto.text(),
            password_email=self.clave, to_cc=self.view.textCC.text(),
            smtp_server=self.servidor, smtp_port=self.puerto, files=self.adjuntos,
            to_cco=self.view.textCCO.text()
        )
        if not ok:
            Ventanas.showAlert("Sistema", f"Se ha producido un error {err_msg}")
        else:
            Ventanas.showAlert("Sistema", "Correo enviado satisfactoriamente")
            self.view.Cerrar()

    def exec_(self):
        if self.archivo_firma:
            self.view.textMensaje.file_open(archivo=self.archivo_firma)
        if self.cliente:
            self.view.textPara.modelo = EmailCliente()
            self.view.textPara.cargaDatos()
        self.view.textAdjunto.setText(
            ','.join([x for x in self.adjuntos])
        )
        super().exec_()

    def cargaParametros(self):
        self.servidor = ParamSist.ObtenerParametro("SERVER_SMTP") #servidor email
        self.clave = ParamSist.ObtenerParametro("CLAVE_SMTP") #clave email
        self.usuario = ParamSist.ObtenerParametro("USUARIO_SMTP") #usuario email
        self.puerto = ParamSist.ObtenerParametro("PUERTO_SMTP") or 587 #puerto
        self.responder=ParamSist.ObtenerParametro("RESPONDER") #correo al cual responder

    @property
    def adjuntos(self):

        return self.__adjuntos

    @adjuntos.setter
    def adjuntos(self, valor):
        if not isinstance(valor, list):
            self.__adjuntos.append(valor)
            self.ActualizaListaAdjuntos()

    def ActualizaListaAdjuntos(self):
        self.view.listaAdjuntos.clear()
        icono = imagen('attach_file.png')
        for item in self.adjuntos:
            self.view.listaAdjuntos.AgregaItem(item, icon=icono)
