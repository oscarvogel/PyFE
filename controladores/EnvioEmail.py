from PyQt5.QtCore import Qt

from controladores.ControladorBase import ControladorBase
from controladores.Emailcliente import EmailClienteController
from libs import Ventanas
from libs.Utiles import envia_correo, imagen, AbrirMultiplesArchivos
from modelos.Clientes import Cliente
from modelos.CorreosEnviados import CorreoEnviado
from modelos.Emailcliente import EmailCliente
from modelos.ParametrosSistema import ParamSist
from vistas.EnvioEmail import EnvioEmailView, ListaCorreosView


class EnvioEmailController(ControladorBase):

    #parametros excluyentes no se puede setear ambos, porque toma de tablas distintas
    cliente = None #indica el cliente al cual se quiere enviar un correo
    proveedor = None #indica el proveedor al cual se quiere enviar un correo
    archivo_firma = '' #archivo con la firma del usuario

    def __init__(self):
        super().__init__()
        self.__adjuntos = []  # lista con los archivos adjuntos a enviar
        self.view = EnvioEmailView()
        self.archivo_firma = ParamSist.ObtenerParametro("ARCHIVO_FIRMA_EMAIL")
        self.conectarWidgets()
        self.cargaParametros()

    def conectarWidgets(self):
        # self.view.textPara.cargaDatos()
        self.view.btnCerrar.clicked.connect(self.view.Cerrar)
        self.view.btnEnviar.clicked.connect(self.onClickBtnEnviar)
        self.view.listaAdjuntos.keyPressed.connect(self.onKeyListaAdjunto)
        self.view.listaAdjuntos.itemDropped.connect(self.onItemDroppedAdjunto)
        self.view.btnAdjunto.clicked.connect(self.onClickBtnAdjunto)
        self.view.btnPara.clicked.connect(lambda : self.onClicBtnPara(self.view.textPara))
        self.view.btnCC.clicked.connect(lambda: self.onClicBtnPara(self.view.textCC))
        self.view.btnCCO.clicked.connect(lambda: self.onClicBtnPara(self.view.textCCO))

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
            correo = CorreoEnviado()
            correo.de = self.usuario
            correo.para = self.view.textPara.text()
            correo.cc = self.view.textCC.text()
            correo.cco = self.view.textCCO.text()
            correo.asunto = self.view.textAsunto.text()
            correo.adjuntos = self.view.textAdjunto.text()
            correo.mensaje = self.view.textMensaje.toHtml()
            correo.save()
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
        if self.cliente:
            self.view.textPara.condicion = EmailCliente.idcliente == self.cliente
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
            # self.ActualizaListaAdjuntos()
        else:
            self.__adjuntos = valor

    def ActualizaListaAdjuntos(self):
        self.view.listaAdjuntos.clear()
        icono = imagen('attach_file.png')
        for item in self.adjuntos:
            self.view.listaAdjuntos.AgregaItem(item, icon=icono)

        self.view.textAdjunto.setText(
            ','.join(x for x in self.adjuntos)
        )

    def onKeyListaAdjunto(self, key):
        if key in [Qt.Key_Delete]:
            self.view.listaAdjuntos.BorrarItemSeleccionado()
            self.CargaAdjuntos()

    def CargaAdjuntos(self):
        self.adjuntos = []

        for row in range(self.view.listaAdjuntos.count() + 1):
            item = self.view.listaAdjuntos.ObtenerItem(row)
            if item:
                self.adjuntos = item

        self.view.textAdjunto.setText(
            ','.join(x for x in self.adjuntos)
        )

    def onItemDroppedAdjunto(self, lista):
        for l in lista:
            self.adjuntos = l

        self.view.textAdjunto.setText(
            ','.join(x for x in self.adjuntos)
        )

    def onClickBtnAdjunto(self):
        archivos = AbrirMultiplesArchivos(filter="Todos los archivos (*.*)")

        for a in archivos:
            self.adjuntos = a

        self.ActualizaListaAdjuntos()

    def onClicBtnPara(self, lineedit):
        controlador = ListaCorreosController()
        controlador.cliente = self.cliente
        controlador.CargaDatos()
        controlador.exec_()
        lineedit.setText(
            ','.join(x for x in controlador.correos_seleccionados)
        )

class ListaCorreosController(ControladorBase):

    cliente = None
    model = None
    correos_seleccionados = []

    def __init__(self):
        super().__init__()
        self.view = ListaCorreosView()
        self.conectarWidgets()

    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(self.view.Cerrar)
        self.view.btnSeleccionar.clicked.connect(self.onClickSeleccionar)
        self.view.checkTodos.clicked.connect(self.CargaDatos)
        self.view.textBusqueda.textChanged.connect(self.CargaDatos)
        self.view.btnAgregar.clicked.connect(self.onClickAgregar)

    def CargaDatos(self):
        self.view.gridCorreos.setRowCount(0)
        correos = None
        if self.cliente:
            correos = EmailCliente.select()
            if not self.view.checkTodos.isChecked():
                correos = correos.where(EmailCliente.idcliente == self.cliente)

            if self.view.textBusqueda.text():
                correos = correos.where(
                    EmailCliente.email.contains(self.view.textBusqueda.text()) |
                    Cliente.nombre.contains(self.view.textBusqueda.text())
                ).join(Cliente)

        for c in correos:
            if self.cliente:
                nombre = c.idcliente.nombre
                email = c.email
            else:
                nombre = ''
                email = ''
            item = [
                False, nombre, email
            ]
            self.view.gridCorreos.AgregaItem(item)

    def onClickSeleccionar(self):
        self.correos_seleccionados = []

        for row in range(self.view.gridCorreos.rowCount()):
            correo = self.view.gridCorreos.ObtenerItem(fila=row, col="Correo")
            self.correos_seleccionados.append(correo)

        self.view.Cerrar()

    def onClickAgregar(self):
        if self.cliente:
            controlador = EmailClienteController()
            controlador.idcliente = self.cliente
            controlador.CargaEmail()
            controlador.exec_()
